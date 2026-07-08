import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.debate import Debate
from app.agents.debate import run_debate
from app.services.llm import llm_available

router = APIRouter(prefix="/debate", tags=["Debate"])


@router.post("/{resume_id}/{job_id}")
def run_debate_endpoint(
    resume_id: int,
    job_id: int,
    mock: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run an Advocate vs. Skeptic vs. Judge debate on a candidate for a job.
    Pass ?mock=true for a canned transcript (UI testing without API credits)."""

    resume = db.query(Resume).filter(
        Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = db.query(Job).filter(
        Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        result = run_debate(
            resume_text=resume.parsed_text or "",
            job_description=job.description or "",
            candidate_name=resume.candidate_name or "Candidate",
            force_mock=mock
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debate failed: {str(e)}")

    # Persist the debate
    debate_row = Debate(
        user_id=current_user.id,
        resume_id=resume_id,
        job_id=job_id,
        recommendation=result["verdict"].get("recommendation", "unknown"),
        confidence=float(result["verdict"].get("confidence", 0)),
        transcript=json.dumps(result),
        is_mock=1 if result.get("is_mock") else 0
    )
    db.add(debate_row)
    db.commit()
    db.refresh(debate_row)

    return {
        "debate_id": debate_row.id,
        "candidate_name": resume.candidate_name,
        "job_title": job.title,
        "llm_available": llm_available,
        **result
    }


@router.get("/history")
def debate_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List past debates for this recruiter"""
    debates = db.query(Debate).filter(
        Debate.user_id == current_user.id
    ).order_by(Debate.created_at.desc()).limit(30).all()

    out = []
    for d in debates:
        resume = db.query(Resume).filter(Resume.id == d.resume_id).first()
        job = db.query(Job).filter(Job.id == d.job_id).first()
        out.append({
            "debate_id": d.id,
            "candidate_name": resume.candidate_name if resume else "Deleted",
            "job_title": job.title if job else "Deleted",
            "recommendation": d.recommendation,
            "confidence": d.confidence,
            "is_mock": bool(d.is_mock),
            "created_at": str(d.created_at)
        })
    return out


@router.get("/{debate_id}")
def get_debate(
    debate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Load a full debate transcript"""
    d = db.query(Debate).filter(
        Debate.id == debate_id, Debate.user_id == current_user.id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Debate not found")
    return json.loads(d.transcript)