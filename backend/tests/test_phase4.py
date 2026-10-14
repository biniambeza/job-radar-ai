import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.database import SessionLocal, init_db
from app.models import Job, JobHash
from app.services.deduplicator import normalize_url, compute_content_hash, make_composite_key
from app.services.pipeline import fast_pre_filter, process_job_pipeline

def test_deduplication_helpers():
    # URL normalization
    dirty_url = "https://example.com/jobs/123/?utm_source=telegram&utm_campaign=winter#apply"
    clean_url = normalize_url(dirty_url)
    assert clean_url == "https://example.com/jobs/123"
    print("[PASS] Deduplication: URL normalization verified.")

    # Content hashing
    text_1 = "We are hiring a Senior Python Developer! Remote work available. Apply now."
    text_2 = "   we are hiring a senior python developer!   remote work available. apply now.   "
    hash_1 = compute_content_hash(text_1)
    hash_2 = compute_content_hash(text_2)
    assert hash_1 == hash_2
    print("[PASS] Deduplication: Normalized content hashing verified.")

    # Composite key
    comp_key = make_composite_key("Acme Corp Inc.", "Senior Backend Engineer (Python)")
    assert comp_key == "acme-corp-inc:senior-backend-engineer-python"
    print("[PASS] Deduplication: Composite slug key verified.")

def test_fast_pre_filter():
    job_post = "We have an open vacancy for a Full-Stack Software Developer. Requirements: React, Python, Remote. Salary negotiable."
    assert fast_pre_filter(job_post) is True

    spam_post = "Crypto airdrop! Claim your free spins now at casino online!"
    assert fast_pre_filter(spam_post) is False

    short_chat = "Hey, what time is the meeting tomorrow?"
    assert fast_pre_filter(short_chat) is False
    print("[PASS] Pipeline: Fast regex pre-filter verified.")

def test_full_pipeline_ingestion_and_deduplication():
    init_db()
    db = SessionLocal()

    test_external_id = "test_phase4_tg_999"
    high_match_post = """
    🚀 HIRING: Senior Full-Stack Engineer (Remote / East Africa or Worldwide)
    Company: NexaTech Labs
    Stack: Python, FastAPI, React, TypeScript, PostgreSQL, Redis
    Requirements:
    - 3+ years experience with modern web applications and REST APIs
    - Strong database skills with PostgreSQL / SQLAlchemy
    - Hands-on experience integrating AI / LLM APIs is a major plus!
    Location: 100% Remote
    Compensation: $60,000 - $90,000 / year + equity
    How to apply: Send your resume to careers@nexatech.io or message @nexa_talent
    """

    try:
        # Step 1: Ingest fresh job
        result = process_job_pipeline(
            db=db,
            raw_text=high_match_post,
            source="Telegram (@freelance_ethiopia)",
            source_url="https://t.me/freelance_ethiopia/999",
            external_id=test_external_id
        )

        assert result["status"] == "saved"
        assert result["match_score"] >= 50
        print(f"[PASS] Ingestion: Fresh high-match job processed successfully! (Score: {result['match_score']}, Alert: {result['should_alert']})")

        # Step 2: Ingest the exact same post again (must trigger duplicate detection)
        duplicate_result = process_job_pipeline(
            db=db,
            raw_text=high_match_post,
            source="Telegram (@another_channel)",
            source_url="https://t.me/another_channel/123",
            external_id="test_phase4_tg_1000"
        )
        assert duplicate_result["status"] == "duplicate"
        assert duplicate_result["reason"] == "duplicate_content_hash"
        print(f"[PASS] Ingestion: Duplicate detection caught identical cross-post ({duplicate_result['reason']}).")

        # Step 3: Ingest non-job post (should be filtered or discarded)
        irrelevant_post = "House for rent in Bole, Addis Ababa. 3 bedrooms, 2 bathrooms, modern finish. Call 0911223344 for pricing."
        filtered_result = process_job_pipeline(
            db=db,
            raw_text=irrelevant_post,
            source="Telegram (@random_channel)"
        )
        assert filtered_result["status"] in ("filtered", "discarded")
        print(f"[PASS] Ingestion: Non-job post properly discarded ({filtered_result['status']}: {filtered_result.get('reason')}).")

    finally:
        # Cleanup test records
        cleanup_job = db.query(Job).filter(Job.external_id == test_external_id).first()
        if cleanup_job:
            db.delete(cleanup_job)
        
        test_hash = compute_content_hash(high_match_post)
        cleanup_hash = db.query(JobHash).filter(JobHash.content_hash == test_hash).first()
        if cleanup_hash:
            db.delete(cleanup_hash)
        
        db.commit()
        db.close()
        print("[PASS] Database cleanup complete.")

if __name__ == "__main__":
    print("=" * 60)
    print(" Running Phase 4: Gemini AI Matcher & Deduplication Tests")
    print("=" * 60)
    test_deduplication_helpers()
    test_fast_pre_filter()
    test_full_pipeline_ingestion_and_deduplication()
    print("=" * 60)
    print(" ALL PHASE 4 TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
