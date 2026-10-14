import logging
import asyncio
from typing import Optional, List
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.config import settings
from app.database import SessionLocal
from app.models import Job

logger = logging.getLogger(__name__)

# Global bot instance
_bot: Optional[Bot] = None
_dp: Optional[Dispatcher] = None

def get_bot() -> Optional[Bot]:
    """Get or initialize the Aiogram Bot instance."""
    global _bot
    if _bot is not None:
        return _bot

    if not settings.TG_BOT_TOKEN or settings.TG_BOT_TOKEN.startswith("123456:"):
        logger.warning("TG_BOT_TOKEN not configured. Alerts will run in simulation mode.")
        return None

    try:
        _bot = Bot(
            token=settings.TG_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        return _bot
    except Exception as e:
        logger.error(f"Failed to initialize Aiogram Bot: {e}")
        return None

def get_dispatcher() -> Dispatcher:
    """Get or initialize the Aiogram Dispatcher with command handlers."""
    global _dp
    if _dp is not None:
        return _dp

    _dp = Dispatcher()
    _register_bot_handlers(_dp)
    return _dp

def format_job_card_html(job_data: dict) -> tuple[str, types.InlineKeyboardMarkup]:
    """Build a rich HTML notification message and inline keyboard buttons."""
    score = job_data.get("match_score", 0)
    title = job_data.get("title", "Software Developer")
    company = job_data.get("company") or "Direct Opportunity"
    location_type = job_data.get("location_type", "Remote")
    location = job_data.get("location") or "Flexible"
    summary = job_data.get("summary", "New opportunity matching your technical profile.")
    matching_skills: List[str] = job_data.get("matching_skills") or []
    missing_skills: List[str] = job_data.get("missing_skills") or []
    source = job_data.get("source", "JobRadar AI")
    apply_link = job_data.get("apply_link")
    job_id = job_data.get("job_id") or job_data.get("id")

    # Score indicator
    if score >= 90:
        badge = "🔥 <b>TOP MATCH</b>"
    elif score >= 75:
        badge = "🎯 <b>HIGH MATCH</b>"
    else:
        badge = "✨ <b>POTENTIAL MATCH</b>"

    matched_str = ", ".join(f"<code>{s}</code>" for s in matching_skills[:6]) if matching_skills else "General Profile"
    missing_str = ", ".join(f"<code>{s}</code>" for s in missing_skills[:4]) if missing_skills else "None noted"

    message_text = (
        f"{badge} — <b>{score}% Fit</b>\n\n"
        f"💼 <b>{title}</b>\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📍 <b>Arrangement:</b> {location_type} ({location})\n\n"
        f"📝 <b>Summary:</b>\n{summary}\n\n"
        f"✅ <b>Matching Skills:</b> {matched_str}\n"
        f"⚠️ <b>Missing / Target:</b> {missing_str}\n\n"
        f"📡 <i>Source: {source}</i>"
    )

    # Inline Keyboard Buttons
    builder = InlineKeyboardBuilder()

    # Apply button (URL or search link)
    if apply_link and (apply_link.startswith("http://") or apply_link.startswith("https://") or apply_link.startswith("t.me/")):
        target_url = f"https://{apply_link}" if apply_link.startswith("t.me/") else apply_link
        builder.button(text="🚀 Direct Apply", url=target_url)

    # Action buttons
    if job_id:
        builder.button(text="💾 Save Job", callback_data=f"job_save:{job_id}")
        builder.button(text="❌ Dismiss", callback_data=f"job_dismiss:{job_id}")

    builder.adjust(1, 2)
    return message_text, builder.as_markup()

async def send_job_alert(job_data: dict) -> bool:
    """Send an instant push alert for a high-match job to Telegram."""
    bot = get_bot()
    chat_id = settings.TG_USER_CHAT_ID

    if not bot or not chat_id:
        logger.info(f"[SIMULATED ALERT] Would send alert for Job: '{job_data.get('title')}' ({job_data.get('match_score')}%).")
        return False

    message_text, keyboard = format_job_card_html(job_data)

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
        logger.info(f"Successfully pushed Telegram alert to user {chat_id} for Job ID {job_data.get('job_id')}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert to {chat_id}: {e}")
        return False

def _register_bot_handlers(dp: Dispatcher):
    """Register interactive commands and callbacks for the Telegram notification bot."""

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            f"👋 <b>Welcome to JobRadar AI!</b>\n\n"
            f"I monitor Telegram channels in real time, score jobs against your <code>resume.md</code>, "
            f"and deliver instant push alerts when a listing matches your skills (>= {settings.INSTANT_ALERT_THRESHOLD}%).\n\n"
            f"Commands:\n"
            f"• /status — Check database & system health\n"
            f"• /recent — View top matched opportunities\n"
            f"• /help — Overview of features"
        )

    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        db = SessionLocal()
        try:
            total_jobs = db.query(Job).count()
            saved_jobs = db.query(Job).filter(Job.status == "SAVED").count()
            applied_jobs = db.query(Job).filter(Job.status == "APPLIED").count()
            high_matches = db.query(Job).filter(Job.match_score >= settings.INSTANT_ALERT_THRESHOLD).count()
            await message.answer(
                f"📊 <b>JobRadar AI System Status</b>\n\n"
                f"• <b>Total Parsed:</b> {total_jobs}\n"
                f"• <b>High Matches (>= {settings.INSTANT_ALERT_THRESHOLD}%):</b> {high_matches}\n"
                f"• <b>Saved to Dashboard:</b> {saved_jobs}\n"
                f"• <b>Applied:</b> {applied_jobs}\n"
                f"• <b>Database:</b> Neon Serverless PostgreSQL (Online ✅)"
            )
        finally:
            db.close()

    @dp.message(Command("recent"))
    async def cmd_recent(message: types.Message):
        db = SessionLocal()
        try:
            top_jobs = db.query(Job).order_by(Job.match_score.desc()).limit(3).all()
            if not top_jobs:
                await message.answer("ℹ️ No jobs recorded yet. Ingestion pipeline is running.")
                return

            for job in top_jobs:
                msg, kb = format_job_card_html(job.to_dict())
                await message.answer(msg, reply_markup=kb)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("job_save:"))
    async def callback_save_job(query: types.CallbackQuery):
        job_id = int(query.data.split(":")[1])
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "SAVED"
                db.commit()
                await query.answer("💾 Job saved to your dashboard!", show_alert=False)
                await query.message.edit_reply_markup(reply_markup=None)
            else:
                await query.answer("Job not found.", show_alert=True)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("job_dismiss:"))
    async def callback_dismiss_job(query: types.CallbackQuery):
        job_id = int(query.data.split(":")[1])
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "ARCHIVED"
                db.commit()
                await query.answer("❌ Job dismissed.", show_alert=False)
                await query.message.edit_reply_markup(reply_markup=None)
            else:
                await query.answer("Job not found.", show_alert=True)
        finally:
            db.close()
