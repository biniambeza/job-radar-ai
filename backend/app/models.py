import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from app.database import Base

class Job(Base):
    """Stores structured, scored job opportunities."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    external_id = Column(String(255), index=True, nullable=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    location_type = Column(String(50), default="Remote")  # Remote, Hybrid, Onsite
    source = Column(String(100), nullable=False)          # e.g., 'Telegram (@channel)', 'LinkedIn'
    source_url = Column(String(1024), nullable=True)
    apply_link = Column(String(1024), nullable=True)
    raw_text = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    match_score = Column(Integer, default=0, index=True)
    matching_skills = Column(JSON, default=list)          # list of strings
    missing_skills = Column(JSON, default=list)           # list of strings
    status = Column(String(50), default="NEW", index=True)# NEW, SAVED, APPLIED, INTERVIEWING, REJECTED, ARCHIVED
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    def to_dict(self):
        """Serialize model to dictionary."""
        return {
            "id": self.id,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "location_type": self.location_type,
            "source": self.source,
            "source_url": self.source_url,
            "apply_link": self.apply_link,
            "raw_text": self.raw_text,
            "summary": self.summary,
            "match_score": self.match_score,
            "matching_skills": self.matching_skills or [],
            "missing_skills": self.missing_skills or [],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class JobHash(Base):
    """Deduplication tracker to avoid reprocessing cross-posted or duplicate jobs."""
    __tablename__ = "job_hashes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content_hash = Column(String(64), unique=True, index=True, nullable=False) # SHA-256
    composite_key = Column(String(255), index=True, nullable=False)            # company_slug + title_slug
    url_normalized = Column(String(1024), index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_composite_created", "composite_key", "created_at"),
    )
