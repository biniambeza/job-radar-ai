import re
import hashlib
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import datetime
import logging
from sqlalchemy.orm import Session
from app.models import JobHash, Job

logger = logging.getLogger(__name__)

# Query parameters to strip for clean URL normalization
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "referrer", "fbclid", "gclid", "igshid", "mc_cid", "mc_eid"
}

def normalize_url(url: str | None) -> str | None:
    """Normalize a URL by stripping tracking parameters, lowercase domain, and trailing slashes."""
    if not url:
        return None
    try:
        url = url.strip()
        parsed = urlparse(url)
        if not parsed.netloc:
            return url

        # Filter out tracking query parameters
        clean_queries = [
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
            if k.lower() not in TRACKING_PARAMS
        ]
        clean_query_str = urlencode(clean_queries)
        clean_path = parsed.path.rstrip("/")

        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            clean_path,
            parsed.params,
            clean_query_str,
            ""  # Strip fragment
        ))
        return normalized
    except Exception as e:
        logger.debug(f"Error normalizing URL {url}: {e}")
        return url.strip()

def compute_content_hash(text: str) -> str:
    """
    Generate SHA-256 hash of normalized text.
    Strips non-alphanumeric characters, converts to lowercase, and collapses whitespace.
    """
    if not text:
        return hashlib.sha256(b"").hexdigest()
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    collapsed = " ".join(cleaned.split())
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()

def make_composite_key(company: str | None, title: str | None) -> str:
    """Generate a slugified composite key: company_slug:title_slug."""
    comp_slug = re.sub(r"[^a-z0-9]+", "-", (company or "unknown").strip().lower()).strip("-")
    title_slug = re.sub(r"[^a-z0-9]+", "-", (title or "untitled").strip().lower()).strip("-")
    return f"{comp_slug}:{title_slug}"

def check_is_duplicate(
    db: Session,
    raw_text: str,
    source_url: str | None = None,
    title: str | None = None,
    company: str | None = None,
    lookback_days: int = 14
) -> tuple[bool, str]:
    """
    Check if a job posting is a duplicate using content hash, normalized URL,
    and composite company:title key within a lookback window.
    
    Returns:
        (is_dup, reason)
    """
    # 1. Content Hash Check (Direct duplicate text across channels)
    content_hash = compute_content_hash(raw_text)
    existing_hash = db.query(JobHash).filter(JobHash.content_hash == content_hash).first()
    if existing_hash:
        return True, "duplicate_content_hash"

    # 2. Normalized URL Check
    norm_url = normalize_url(source_url)
    if norm_url:
        existing_by_url = db.query(JobHash).filter(JobHash.url_normalized == norm_url).first()
        if existing_by_url:
            return True, "duplicate_url"

    # 3. Composite Key Check (Same company & title posted within sliding window)
    if title and company:
        composite_key = make_composite_key(company, title)
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=lookback_days)
        existing_composite = db.query(JobHash).filter(
            JobHash.composite_key == composite_key,
            JobHash.created_at >= cutoff_date
        ).first()
        if existing_composite:
            return True, "duplicate_composite_key"

    return False, "unique"

def record_job_hash(
    db: Session,
    raw_text: str,
    source_url: str | None = None,
    title: str | None = None,
    company: str | None = None
) -> JobHash:
    """Record a unique job hash and composite key to PostgreSQL."""
    content_hash = compute_content_hash(raw_text)
    norm_url = normalize_url(source_url)
    composite_key = make_composite_key(company, title)

    job_hash = JobHash(
        content_hash=content_hash,
        composite_key=composite_key,
        url_normalized=norm_url
    )
    db.add(job_hash)
    db.commit()
    db.refresh(job_hash)
    return job_hash
