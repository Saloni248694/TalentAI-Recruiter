from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.core.database import Base


class Debate(Base):
    __tablename__ = "debates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    recommendation = Column(String)          # shortlist | reject | borderline
    confidence = Column(Float)               # 0-100
    transcript = Column(Text)                # full JSON transcript
    is_mock = Column(Integer, default=0)     # 1 if generated in mock mode

    created_at = Column(DateTime(timezone=True), server_default=func.now())