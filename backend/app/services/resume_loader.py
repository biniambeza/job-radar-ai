from pathlib import Path
import logging
from app.config import settings

logger = logging.getLogger(__name__)

_cached_resume_content: str | None = None

def get_resume_content(force_reload: bool = False) -> str:
    """
    Read and return the candidate resume/profile from resume.md.
    Caches the content in memory for performance.
    """
    global _cached_resume_content
    if _cached_resume_content is not None and not force_reload:
        return _cached_resume_content

    resume_path = Path(settings.RESUME_PATH)
    if not resume_path.exists():
        logger.warning(f"Resume file not found at {resume_path}. Using fallback default.")
        return "# Candidate Profile\n\nSoftware Engineer proficient in Python, TypeScript, React, and FastAPI."

    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            _cached_resume_content = f.read().strip()
            logger.info(f"Loaded resume successfully ({len(_cached_resume_content)} characters).")
            return _cached_resume_content
    except Exception as e:
        logger.error(f"Error reading resume file at {resume_path}: {e}")
        return "# Candidate Profile\n\nFull-Stack Software Engineer."

def reload_resume() -> str:
    """Force reloads the resume from disk."""
    return get_resume_content(force_reload=True)
