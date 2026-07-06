from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ResumeOut(BaseModel):
    id: int
    filename: str
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    summary: Optional[str] = None
    ats_score: Optional[float] = None
    ats_feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True