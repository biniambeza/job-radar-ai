import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

def test_phase1_config():
    """Verify configuration loads properly."""
    from app.config import settings
    assert settings.APP_NAME == "JobRadar AI"
    assert settings.INSTANT_ALERT_THRESHOLD == 75
    assert settings.SAVE_TO_DB_THRESHOLD == 50
    assert isinstance(settings.TG_TARGET_CHANNELS, list)
    print(" [PASSED] Phase 1: Configuration loaded successfully.")

def test_phase2_resume_loader():
    """Verify resume loader reads resume.md."""
    from app.services.resume_loader import get_resume_content
    resume = get_resume_content()
    assert len(resume) > 50
    assert "Candidate Profile" in resume
    print(f" [PASSED] Phase 2: Resume loaded ({len(resume)} chars).")

def test_phase2_database_and_models():
    """Verify database initialization and CRUD operations."""
    from app.database import init_db, SessionLocal
    from app.models import Job, JobHash

    init_db()
    db = SessionLocal()
    try:
        # Create test job
        test_job = Job(
            external_id="test_msg_001",
            title="Senior Full-Stack Developer",
            company="TestTech Corp",
            location="Remote",
            location_type="Remote",
            source="Telegram (@test_channel)",
            source_url="https://t.me/test_channel/1",
            apply_link="https://t.me/recruiter",
            raw_text="We are hiring a Senior Full-Stack Developer proficient in Python and React.",
            summary="Looking for a Python/React engineer for remote full-stack role.",
            match_score=88,
            matching_skills=["Python", "React", "FastAPI"],
            missing_skills=["Kubernetes"],
            status="NEW"
        )
        db.add(test_job)

        # Create test hash
        test_hash = JobHash(
            content_hash="abc123sha256hashdummy",
            composite_key="testtech-corp:senior-full-stack-developer",
            url_normalized="https://t.me/test_channel/1"
        )
        db.add(test_hash)
        db.commit()

        # Query back
        queried_job = db.query(Job).filter(Job.external_id == "test_msg_001").first()
        assert queried_job is not None
        assert queried_job.match_score == 88
        assert queried_job.matching_skills == ["Python", "React", "FastAPI"]

        # Clean up test records
        db.delete(queried_job)
        db.delete(test_hash)
        db.commit()

        print(" [PASSED] Phase 2: Database tables created and CRUD operations verified.")
    finally:
        db.close()

if __name__ == "__main__":
    test_phase1_config()
    test_phase2_resume_loader()
    test_phase2_database_and_models()
    print("\n All Phase 1 and Phase 2 tests passed successfully!")
