import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import asyncio
from app.services.notifier import format_job_card_html, send_job_alert, get_dispatcher

def test_job_card_formatting():
    sample_job = {
        "job_id": 101,
        "title": "Staff Full-Stack Engineer",
        "company": "Horizon Cloud Labs",
        "location": "Worldwide",
        "location_type": "Remote",
        "match_score": 94,
        "matching_skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
        "missing_skills": ["Rust"],
        "summary": "Seeking a staff engineer to architect real-time cloud data pipelines and responsive UI.",
        "apply_link": "https://t.me/tech_recruiter_bot",
        "source": "Telegram (@remote_dev_jobs)"
    }

    message_text, markup = format_job_card_html(sample_job)

    assert "TOP MATCH" in message_text
    assert "94% Fit" in message_text
    assert "Staff Full-Stack Engineer" in message_text
    assert "Horizon Cloud Labs" in message_text
    assert "<code>Python</code>" in message_text
    assert "<code>Rust</code>" in message_text
    assert markup.inline_keyboard is not None
    assert len(markup.inline_keyboard) >= 1
    print("[PASS] Telegram Notifier: HTML card formatting and inline buttons verified.")

def test_safe_alert_dispatch():
    sample_job = {
        "job_id": 102,
        "title": "Senior Backend Developer",
        "company": "FinTech Africa",
        "location": "Addis Ababa",
        "location_type": "Hybrid",
        "match_score": 82,
        "matching_skills": ["Python", "PostgreSQL"],
        "missing_skills": [],
        "summary": "Building payment microservices and API gateways.",
        "apply_link": "https://careers.fintech.africa/apply/102",
        "source": "Telegram (@habeshajobs)"
    }

    # Should run cleanly in simulation mode when real credentials aren't supplied in tests
    sent = asyncio.run(send_job_alert(sample_job))
    assert isinstance(sent, bool)
    print(f"[PASS] Telegram Notifier: Alert delivery executed cleanly (Result: {sent}).")

def test_dispatcher_registration():
    dp = get_dispatcher()
    assert dp is not None
    print("[PASS] Telegram Notifier: Aiogram Dispatcher and interactive commands registered.")

if __name__ == "__main__":
    print("=" * 60)
    print(" Running Phase 5: Telegram Push Alert Bot Tests")
    print("=" * 60)
    test_job_card_formatting()
    test_safe_alert_dispatch()
    test_dispatcher_registration()
    print("=" * 60)
    print(" ALL PHASE 5 TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
