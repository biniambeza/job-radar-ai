import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for backend
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Info
    APP_NAME: str = "JobRadar AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Telegram MTProto Client (Scraper)
    TG_API_ID: int = 0
    TG_API_HASH: str = ""
    TG_PHONE_NUMBER: str = ""
    TG_TARGET_CHANNELS: Union[List[str], str] = ["freelance_ethiopia", "habeshajobs", "remote_dev_jobs"]

    # Telegram Bot (Instant Push Alerts)
    TG_BOT_TOKEN: str = ""
    TG_USER_CHAT_ID: int = 0

    # AI / LLM (Gemini API)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Database
    DATABASE_URL: str = "sqlite:///./jobradar.db"

    # Matching & Alert Thresholds
    INSTANT_ALERT_THRESHOLD: int = 75
    SAVE_TO_DB_THRESHOLD: int = 50

    # LinkedIn Scraper Settings
    LINKEDIN_SCRAPE_INTERVAL_HOURS: int = 6
    LINKEDIN_SEARCH_TERMS: Union[List[str], str] = ["Software Engineer", "Full Stack Developer", "Backend Developer"]
    LINKEDIN_LOCATION: str = "Remote"

    # Resume File Path
    RESUME_PATH: str = str(Path(__file__).resolve().parent / "data" / "resume.md")

    @field_validator("TG_TARGET_CHANNELS", "LINKEDIN_SEARCH_TERMS", mode="before")
    @classmethod
    def parse_comma_separated_list(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

# Cached global settings instance
settings = Settings()
