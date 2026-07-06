import os
import json
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.services.parser import extract_text_from_pdf, parse_resume_with_claude
from app.services.ats import analyze_ats
from app.core.config import settings

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload")
async def upload_resumes(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload one or multiple resume PDFs"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    results = []

    for file in files:
        # Only allow PDF files
        if not file.filename.endswith(".pdf"):
            results.append({
                "filename": file.filename,
                "error": "Only PDF files are allowed"
            })
            continue

        try:
            # Step 1: Save file to disk
            safe_filename = f"{current_user.id}_{file.filename}"
            file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Step 2: Extract text from PDF
            text = extract_text_from_pdf(file_path)

            # Step 3: Parse resume with Gemini
            parsed = parse_resume_with_claude(text)


            # Step 4: ATS Analysis with Gemini
            ats_result = analyze_ats(text)

            # Step 5: Save to PostgreSQL
            resume = Resume(
                user_id=current_user.id,
                filename=file.filename,
                file_path=file_path,
                candidate_name=parsed.get("candidate_name", "Unknown"),
                email=parsed.get("email", ""),
                phone=parsed.get("phone", ""),
                summary=parsed.get("summary", ""),
                skills=json.dumps(parsed.get("skills", [])),
                experience=json.dumps(parsed.get("experience", [])),
                education=json.dumps(parsed.get("education", [])),
                ats_score=ats_result.get("ats_score", 0),
                ats_feedback=json.dumps(ats_result),
                parsed_text=text[:5000]
            )
            db.add(resume)
            db.commit()
            db.refresh(resume)

            results.append({
                "filename": file.filename,
                "resume_id": resume.id,
                "candidate_name": resume.candidate_name,
                "ats_score": resume.ats_score,
                "status": "success"
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e),
                "status": "failed"
            })

    return {
        "total_uploaded": len(results),
        "results": results
    }


@router.get("/")
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all resumes for logged-in recruiter"""
    resumes = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.created_at.desc()).all()

    result = []
    for r in resumes:
        result.append({
            "id": r.id,
            "filename": r.filename,
            "candidate_name": r.candidate_name,
            "email": r.email,
            "phone": r.phone,
            "ats_score": r.ats_score,
            "skills": json.loads(r.skills) if r.skills else [],
            "created_at": str(r.created_at)
        })
    return result


@router.get("/{resume_id}")
def get_resume_detail(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get full detail of a single resume"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    ats_feedback = json.loads(resume.ats_feedback) if resume.ats_feedback else {}

    return {
        "id": resume.id,
        "filename": resume.filename,
        "candidate_name": resume.candidate_name,
        "email": resume.email,
        "phone": resume.phone,
        "summary": resume.summary,
        "skills": json.loads(resume.skills) if resume.skills else [],
        "experience": json.loads(resume.experience) if resume.experience else [],
        "education": json.loads(resume.education) if resume.education else [],
        "ats_score": resume.ats_score,
        "ats_feedback": ats_feedback,
        "parsed_text": resume.parsed_text,
        "created_at": str(resume.created_at)
    }


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a resume"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Delete file from disk
    if os.path.exists(resume.file_path):
        os.remove(resume.file_path)

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted successfully"}

# ── Day 4: LangGraph Agent Pipeline ──────────────
from app.agents.workflow import run_pipeline

@router.post("/{resume_id}/reanalyze")
def reanalyze_with_agents(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Re-run a resume through the LangGraph multi-agent pipeline"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file missing from disk")

    # Run through agent pipeline: Parser → ATS → Report
    report = run_pipeline(resume.file_path)

    # Update DB with fresh results
    parsed = report["candidate"]
    ats = report["ats_analysis"]

    resume.candidate_name = parsed.get("candidate_name", resume.candidate_name)
    resume.email = parsed.get("email", resume.email)
    resume.phone = parsed.get("phone", resume.phone)
    resume.skills = json.dumps(parsed.get("skills", []))
    resume.ats_score = ats.get("ats_score", resume.ats_score)
    resume.ats_feedback = json.dumps(ats)
    db.commit()

    return {
        "message": "Re-analyzed with LangGraph agent pipeline",
        "pipeline": report["pipeline"],
        "candidate_name": resume.candidate_name,
        "ats_score": resume.ats_score
    }