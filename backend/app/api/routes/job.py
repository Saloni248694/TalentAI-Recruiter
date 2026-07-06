import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.job import JobCreate
from app.services.matcher import build_index, search_candidates

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/")
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_job = Job(
        user_id=current_user.id,
        title=job.title,
        description=job.description
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@router.get("/")
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    jobs = db.query(Job).filter(
        Job.user_id == current_user.id
    ).order_by(Job.created_at.desc()).all()
    return jobs


@router.post("/reindex")
def reindex_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rebuild FAISS index from all resumes"""
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).all()

    if not resumes:
        raise HTTPException(status_code=400, detail="No resumes to index. Upload resumes first.")

    texts = []
    ids = []
    for r in resumes:
        # Combine parsed text + skills for better matching
        text = (r.parsed_text or "") + " " + (r.skills or "")
        texts.append(text)
        ids.append(r.id)

    build_index(texts, ids)
    return {"message": f"Indexed {len(ids)} resumes successfully"}


@router.post("/{job_id}/match")
def match_candidates(
    job_id: int,
    top_k: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Find top matching candidates for a job"""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Auto-rebuild index before matching (keeps it fresh)
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    if not resumes:
        raise HTTPException(status_code=400, detail="No resumes uploaded yet")

    texts = [(r.parsed_text or "") + " " + (r.skills or "") for r in resumes]
    ids = [r.id for r in resumes]
    build_index(texts, ids)

    # Search
    matches = search_candidates(job.description, top_k)

    # Enrich with resume details
    results = []
    for m in matches:
        resume = db.query(Resume).filter(Resume.id == m["resume_id"]).first()
        if resume:
            results.append({
                "resume_id": resume.id,
                "candidate_name": resume.candidate_name,
                "email": resume.email,
                "phone": resume.phone,
                "skills": json.loads(resume.skills) if resume.skills else [],
                "ats_score": resume.ats_score,
                "match_score": m["match_score"]
            })

    return {
        "job_id": job.id,
        "job_title": job.title,
        "total_matches": len(results),
        "candidates": results
    }


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"message": "Deleted"}