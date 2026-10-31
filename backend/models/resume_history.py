from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from database import Base


class ResumeHistory(Base):
    __tablename__ = "resume_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    target_role = Column(String(200), nullable=False)
    match_score = Column(Integer, nullable=False)
    resume_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    skill_gaps = Column(Text, nullable=False, default="[]")
    action_roadmap = Column(Text, nullable=False, default="[]")
    ats_score = Column(Integer, nullable=False, default=0)
    keyword_heatmap = Column(Text, nullable=False, default="[]")
    ats_issues = Column(Text, nullable=False, default="[]")
    tailored_bullets = Column(Text, nullable=False, default="[]")
