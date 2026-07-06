import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.job import Job
from app.models.resume import Resume
from app.services.report import generate_pdf_report
from app.services.matcher import build_index, search_candidates
from app.services.cache import cache_get, cache_set

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{job_id}/pdf")
def download_pdf_report(
    job_id: int,
    top_k: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate and download a PDF report of top candidates for a job"""

    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == current_user.id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # ── Try Redis cache first ──
    cache_key = f"match:{current_user.id}:{job_id}:{top_k}"
    candidates = cache_get(cache_key)

    if not candidates:
        resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
        if not resumes:
            raise HTTPException(status_code=400, detail="No resumes uploaded")

        texts = [(r.parsed_text or "") + " " + (r.skills or "") for r in resumes]
        ids = [r.id for r in resumes]
        build_index(texts, ids)

        matches = search_candidates(job.description, top_k)

        candidates = []
        for m in matches:
            resume = db.query(Resume).filter(Resume.id == m["resume_id"]).first()
            if resume:
                candidates.append({
                    "candidate_name": resume.candidate_name,
                    "email": resume.email,
                    "skills": json.loads(resume.skills) if resume.skills else [],
                    "ats_score": resume.ats_score or 0,
                    "match_score": m["match_score"]
                })

        # Cache for 30 minutes
        cache_set(cache_key, candidates, ttl=1800)

    if not candidates:
        raise HTTPException(status_code=400, detail="No matching candidates found")

    # ── Generate PDF ──
    os.makedirs("reports", exist_ok=True)
    safe_title = "".join(c if c.isalnum() else "_" for c in job.title)[:30]
    output_path = f"reports/TalentAI_Report_{safe_title}_{job_id}.pdf"

    generate_pdf_report(candidates, job.title, output_path)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"TalentAI_Report_{safe_title}.pdf"
    )