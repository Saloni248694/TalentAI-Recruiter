import os
import json
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.debate import Debate
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.services.parser import extract_text_from_pdf, parse_resume_with_claude
from app.services.ats import analyze_ats
from app.core.config import settings
from app.services.llm import ask_claude_json, llm_available
from app.services.auditor import audit_resume

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
            parsed = parse_resume_with_claude(text, filename=file.filename)


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
    search: str = None,
    min_score: float = None,
    max_score: float = None,
    skill: str = None,
    sort_by: str = "newest",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all resumes with optional search, filters, and sorting"""
    query = db.query(Resume).filter(Resume.user_id == current_user.id)

    # Search across name, email, and skills
    if search:
        term = f"%{search.lower()}%"
        query = query.filter(
            (Resume.candidate_name.ilike(term)) |
            (Resume.email.ilike(term)) |
            (Resume.skills.ilike(term))
        )

    # ATS score range filter
    if min_score is not None:
        query = query.filter(Resume.ats_score >= min_score)
    if max_score is not None:
        query = query.filter(Resume.ats_score <= max_score)

    # Skill filter (checks JSON string)
    if skill:
        query = query.filter(Resume.skills.ilike(f"%{skill}%"))

    # Sorting
    if sort_by == "score_high":
        query = query.order_by(Resume.ats_score.desc())
    elif sort_by == "score_low":
        query = query.order_by(Resume.ats_score.asc())
    elif sort_by == "name":
        query = query.order_by(Resume.candidate_name.asc())
    else:  # newest (default)
        query = query.order_by(Resume.created_at.desc())

    resumes = query.all()

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
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Remove dependent debate rows first (foreign-key constraint)
    db.query(Debate).filter(Debate.resume_id == resume_id).delete()

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted"}


# ── Day 4: LangGraph 4-Agent Pipeline ────────────
from app.agents.workflow import run_pipeline
from app.models.job import Job

@router.post("/{resume_id}/reanalyze")
def reanalyze_with_agents(
    resume_id: int,
    job_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Re-run a resume through the 4-agent LangGraph pipeline.
    Optionally pass ?job_id=N to include the Matching Agent's job comparison."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file missing from disk")

    # Optional: fetch job description for the Matching Agent
    job_description = None
    job_title = None
    if job_id:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.user_id == current_user.id
        ).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job_description = job.description
        job_title = job.title

    # Run through 4-agent pipeline: Parser → ATS → Matching → Report
    report = run_pipeline(resume.file_path, job_description)

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
        "message": "Re-analyzed with LangGraph 4-agent pipeline",
        "pipeline": report["pipeline"],
        "candidate_name": resume.candidate_name,
        "ats_score": resume.ats_score,
        "matching": report["matching"],
        "matched_against_job": job_title
    }

# ── Phase 2: AI Resume Optimizer ─────────────────
@router.post("/{resume_id}/optimize")
def optimize_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """AI-rewritten bullet points and tailored summary for a resume"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not llm_available:
        raise HTTPException(
            status_code=503,
            detail="Optimizer requires Claude API — set CLAUDE_API_KEY in .env"
        )

    try:
        system = (
            "You are an expert resume coach. Respond with ONLY valid JSON, "
            "no markdown, no code fences."
        )
        prompt = f"""Improve this resume. Return ONLY JSON in this exact schema:
{{
  "optimized_summary": "a compelling 3-sentence professional summary",
  "improved_bullets": [
    {{"original": "weak line from resume", "improved": "stronger rewritten version with action verb and impact"}}
  ],
  "missing_keywords": ["important industry keywords the resume should add"],
  "overall_advice": "2-3 sentences of the most important improvement advice"
}}

Rules: improved_bullets max 5 items, missing_keywords max 8.

RESUME TEXT:
{(resume.parsed_text or "")[:5000]}"""

        result = ask_claude_json(prompt, system=system, max_tokens=1800)
        return {
            "resume_id": resume_id,
            "candidate_name": resume.candidate_name,
            "optimization": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")
    
    # ── Phase 2: Consistency Auditor ─────────────────
@router.post("/{resume_id}/audit")
def audit_resume_endpoint(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fraud/inflation audit: timeline analysis, claim verification, consistency score"""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.parsed_text:
        raise HTTPException(status_code=400, detail="No parsed text available for this resume")

    skills = json.loads(resume.skills) if resume.skills else []
    result = audit_resume(resume.parsed_text, skills)

    return {
        "resume_id": resume_id,
        "candidate_name": resume.candidate_name,
        **result
    }