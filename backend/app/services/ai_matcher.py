import json
import logging
import re
from typing import Optional, List
from pydantic import BaseModel, Field
from app.config import settings
from app.services.resume_loader import get_resume_content

logger = logging.getLogger(__name__)

class JobMatchResult(BaseModel):
    """Structured extraction and resume match assessment for a job post."""
    is_relevant_sector: bool = Field(
        description="True if the post is a legitimate software engineering, web development, data, or AI/tech job opening."
    )
    job_title: str = Field(
        description="Extracted standard job title (e.g., Full-Stack Engineer, Backend Developer)."
    )
    company: Optional[str] = Field(
        default=None,
        description="Hiring company name, or null/None if unmentioned."
    )
    location: Optional[str] = Field(
        default=None,
        description="Location mentioned in post (e.g. Worldwide, Addis Ababa, US, Remote)."
    )
    location_type: str = Field(
        default="Remote",
        description="One of: 'Remote', 'Hybrid', 'Onsite'."
    )
    match_score: int = Field(
        ge=0,
        le=100,
        description="Match score from 0 to 100 evaluated strictly against the candidate's resume."
    )
    matching_skills: List[str] = Field(
        default_factory=list,
        description="Technical skills and tools demanded by the job that the candidate possesses."
    )
    missing_skills: List[str] = Field(
        default_factory=list,
        description="Required or preferred skills mentioned in the job that are absent from the candidate's resume."
    )
    summary: str = Field(
        description="A 1-2 sentence executive summary of the job responsibilities and expectations."
    )
    apply_link_or_contact: Optional[str] = Field(
        default=None,
        description="Link to apply, email address, recruiter username, or Telegram handle/bot."
    )

def _get_gemini_client():
    """Initialize Google GenAI client if GEMINI_API_KEY is configured."""
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY.startswith("your_"):
        return None
    try:
        from google import genai
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Google GenAI Client: {e}")
        return None

def _fallback_heuristic_matcher(raw_text: str, resume_text: str) -> JobMatchResult:
    """
    Intelligent heuristic fallback when GEMINI_API_KEY is not configured.
    Ensures pipeline continuity and offline testing.
    """
    lower_text = raw_text.lower()
    
    # Common tech skills dictionary for keyword scanning
    tech_keywords = [
        "python", "react", "typescript", "javascript", "fastapi", "django",
        "nodejs", "node.js", "postgres", "postgresql", "sql", "docker",
        "aws", "mongodb", "redis", "next.js", "tailwind", "rest api", "graphql", "ai", "llm"
    ]
    
    matched = [tech for tech in tech_keywords if tech in lower_text]
    
    # Basic title detection
    title = "Software Engineer"
    if "full stack" in lower_text or "fullstack" in lower_text:
        title = "Full-Stack Developer"
    elif "backend" in lower_text:
        title = "Backend Developer"
    elif "frontend" in lower_text:
        title = "Frontend Developer"
    elif "ai" in lower_text or "machine learning" in lower_text:
        title = "AI / ML Engineer"

    # Location type detection
    location_type = "Remote"
    if "onsite" in lower_text or "on-site" in lower_text:
        location_type = "Onsite"
    elif "hybrid" in lower_text:
        location_type = "Hybrid"

    # Contact / apply link extraction regex
    link_match = re.search(r"(https?://\S+|@\w+|[\w\.-]+@[\w\.-]+\.\w+)", raw_text)
    apply_link = link_match.group(0) if link_match else None

    # Calculate heuristic score based on skill overlap
    score = min(95, max(20, len(matched) * 18))
    is_relevant = len(matched) >= 1 or any(k in lower_text for k in ["hiring", "developer", "engineer", "job", "vacancy"])

    return JobMatchResult(
        is_relevant_sector=is_relevant,
        job_title=title,
        company="Extracted from post",
        location="Remote / Unspecified",
        location_type=location_type,
        match_score=score if is_relevant else 15,
        matching_skills=[s.title() for s in matched],
        missing_skills=["Cloud Architecture"] if len(matched) < 3 else [],
        summary="Heuristically analyzed job posting (configure GEMINI_API_KEY for deep AI scoring).",
        apply_link_or_contact=apply_link
    )

def evaluate_job_post(raw_text: str, source: str = "Telegram", source_url: str | None = None) -> JobMatchResult:
    """
    Score and extract structured parameters from raw job post using Gemini API.
    Compares requirements against candidate profile in resume.md.
    """
    client = _get_gemini_client()
    resume_text = get_resume_content()

    if not client:
        logger.warning("GEMINI_API_KEY not configured. Using heuristic matcher fallback.")
        return _fallback_heuristic_matcher(raw_text, resume_text)

    prompt = f"""You are JobRadar AI's expert technical recruiter and resume matching engine.
Your task is to analyze an incoming unformatted job posting and evaluate it strictly against the candidate's resume and target preferences.

### CANDIDATE RESUME & PREFERENCES:
{resume_text}

### INCOMING JOB POSTING (Source: {source}):
{raw_text}

### SCORING CALIBRATION RUBRIC (0–100):
- 90–100: Top tier match. Candidate's core skills (Python, FastAPI, TypeScript, React, AI/LLM, PostgreSQL) and target seniority match closely.
- 75–89: Strong match. Candidate meets 70%+ of requirements with only minor, non-critical missing skills.
- 50–74: Moderate/partial match. Adjacent technologies, or candidate would need to learn key frameworks on the job.
- < 50: Poor match, non-technical role, deal-breaker violated (e.g. legacy stack, unpaid internship), or misaligned seniority.

### EXTRACTION RULES:
1. is_relevant_sector: Set to true ONLY if this is a genuine software engineering, AI, web development, or tech role.
2. job_title: Specific standard title (e.g., 'Full-Stack Developer', 'Python Backend Engineer').
3. location_type: Must be 'Remote', 'Hybrid', or 'Onsite'.
4. matching_skills: List specific technologies from candidate resume that match this job.
5. missing_skills: List required/desired skills in the post that candidate lacks.
6. apply_link_or_contact: Extract apply URL, recruiter email, or Telegram username/link.
7. summary: 1-2 concise sentences summarizing the role and main responsibilities.
"""

    try:
        from google.genai import types

        # Use GEMINI_MODEL setting, falling back to gemini-2.5-flash or gemini-3.8-flash
        model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=JobMatchResult.model_json_schema(),
                temperature=0.1,  # Low temperature for deterministic scoring
            )
        )

        data = json.loads(response.text)
        return JobMatchResult.model_validate(data)

    except Exception as e:
        logger.error(f"Error calling Gemini API for job evaluation: {e}")
        # Return fallback heuristic on API error/rate-limit
        return _fallback_heuristic_matcher(raw_text, resume_text)
