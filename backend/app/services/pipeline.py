import re
import logging
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Job
from app.services.deduplicator import check_is_duplicate, record_job_hash
from app.services.ai_matcher import evaluate_job_post, JobMatchResult

logger = logging.getLogger(__name__)

# Fast pre-filtering regex for job post indicators
JOB_INDICATORS_REGEX = re.compile(
    r"\b(hiring|vacancy|job|position|developer|engineer|fullstack|full-stack|backend|frontend|"
    r"software|react|python|remote|onsite|hybrid|salary|apply|experience|requirements|responsibilities)\b",
    re.IGNORECASE
)

# Common spam / advertisement keywords to reject early
SPAM_INDICATORS_REGEX = re.compile(
    r"\b(crypto airdrop|free spins|casino|betting|forex signals|adult content|weight loss)\b",
    re.IGNORECASE
)

def fast_pre_filter(text: str) -> bool:
    """
    Fast boolean check before hitting Gemini API or Database.
    Returns True if the text resembles a potential job posting.
    """
    if not text or len(text.strip()) < 40:
        return False
    
    # Reject obvious spam
    if SPAM_INDICATORS_REGEX.search(text):
        return False
    
    # Must match at least 2 job keywords
    matches = JOB_INDICATORS_REGEX.findall(text)
    return len(matches) >= 2

def process_job_pipeline(
    db: Session,
    raw_text: str,
    source: str,
    source_url: str | None = None,
    external_id: str | None = None
) -> dict:
    """
    Unified ingestion pipeline:
    1. Pre-filter keyword check
    2. Content & URL deduplication
    3. Gemini AI structured matching & scoring against resume.md
    4. Composite company:title deduplication
    5. Save qualified listings (>= 50%) to Neon PostgreSQL
    6. Return decision (saved, alert, duplicate, discarded)
    """
    # 1. Fast regex pre-filter
    if not fast_pre_filter(raw_text):
        return {
            "status": "filtered",
            "reason": "failed_pre_filter_keywords",
            "job": None,
            "should_alert": False
        }

    # 2. Check for duplicate content hash or URL before spending AI tokens
    is_dup, dup_reason = check_is_duplicate(db, raw_text=raw_text, source_url=source_url)
    if is_dup:
        return {
            "status": "duplicate",
            "reason": dup_reason,
            "job": None,
            "should_alert": False
        }

    # 3. Evaluate with Gemini AI Matcher
    match_result: JobMatchResult = evaluate_job_post(
        raw_text=raw_text,
        source=source,
        source_url=source_url
    )

    # 4. Check if sector is completely irrelevant
    if not match_result.is_relevant_sector:
        return {
            "status": "discarded",
            "reason": "irrelevant_sector",
            "match_score": match_result.match_score,
            "job": None,
            "should_alert": False
        }

    # 5. Secondary deduplication check on extracted company + title
    is_composite_dup, comp_reason = check_is_duplicate(
        db,
        raw_text=raw_text,
        source_url=source_url,
        title=match_result.job_title,
        company=match_result.company
    )
    if is_composite_dup:
        return {
            "status": "duplicate",
            "reason": comp_reason,
            "job": None,
            "should_alert": False
        }

    # 6. Score Threshold Check
    # Discard if score is below the save threshold (default: 50)
    if match_result.match_score < settings.SAVE_TO_DB_THRESHOLD:
        return {
            "status": "discarded",
            "reason": f"score_below_threshold ({match_result.match_score} < {settings.SAVE_TO_DB_THRESHOLD})",
            "match_score": match_result.match_score,
            "job": None,
            "should_alert": False
        }

    # 7. Save qualified job to Neon PostgreSQL
    job = Job(
        external_id=external_id,
        title=match_result.job_title,
        company=match_result.company,
        location=match_result.location,
        location_type=match_result.location_type,
        source=source,
        source_url=source_url,
        apply_link=match_result.apply_link_or_contact or source_url,
        raw_text=raw_text,
        summary=match_result.summary,
        match_score=match_result.match_score,
        matching_skills=match_result.matching_skills,
        missing_skills=match_result.missing_skills,
        status="NEW"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Record hash in database to prevent future duplicates
    record_job_hash(
        db=db,
        raw_text=raw_text,
        source_url=source_url,
        title=match_result.job_title,
        company=match_result.company
    )

    # Determine if this warrants an instant push alert (>= 75%)
    should_alert = match_result.match_score >= settings.INSTANT_ALERT_THRESHOLD

    return {
        "status": "saved",
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "match_score": job.match_score,
        "should_alert": should_alert,
        "matching_skills": job.matching_skills,
        "missing_skills": job.missing_skills,
        "apply_link": job.apply_link,
        "summary": job.summary
    }
