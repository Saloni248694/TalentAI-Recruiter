from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)

    # Parsed Fields
    candidate_name = Column(String)
    email = Column(String)
    phone = Column(String)
    skills = Column(Text)        # stored as JSON string
    experience = Column(Text)    # stored as JSON string
    education = Column(Text)     # stored as JSON string
    summary = Column(Text)

    # ATS Fields
    ats_score = Column(Float, default=0.0)
    ats_feedback = Column(Text)  # stored as JSON string

    # Raw Text
    parsed_text = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())