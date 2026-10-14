# 🎯 JobRadar AI — Automated Job Aggregator & Resume Matcher

An intelligent, end-to-end job aggregation pipeline that monitors **Telegram channels** in real time and scrapes **LinkedIn** on a schedule. It filters out noise, parses unstructured job posts using AI, scores every listing against your personal resume, and delivers high-match opportunities directly to a **Telegram Bot** and a **React Dashboard**.

---

## ✨ Key Features

- **📡 Real-Time Telegram Listener:** Connects via Telegram MTProto (`Telethon`) to monitor public and private job channels instantaneously without requiring admin privileges.
- **🔍 Automated LinkedIn Scraper:** Scheduled cron workers using `JobSpy` to pull fresh local and worldwide remote roles.
- **🧠 AI Resume Scoring & Extraction:** Uses the **Gemini API** with structured JSON outputs to parse messy posts, compare requirements against your `resume.md`, calculate a `0–100%` match score, and highlight matching vs. missing skills.
- **🛡️ Smart Deduplication:** Prevents cross-posted jobs from spamming your feed using URL normalization, content hashing, and composite key matching (`company + title`).
- **📲 Instant Telegram Alerts:** Sends formatted push notifications via an `Aiogram` bot for high-scoring jobs (>= 75%) with one-click apply links.
- **💻 Web Dashboard:** A React + TypeScript interface to browse medium-match jobs, track application statuses (`Saved`, `Applied`, `Interviewing`), and generate tailored cover letters.

---

## 🏗️ System Architecture

```text
+-------------------+       +-------------------+
| Telegram Channels |       |   LinkedIn Jobs   |
| (Real-Time Stream)|       | (Scheduled Cron)  |
+---------+---------+       +---------+---------+
          |                           |
          v                           v
+-----------------------------------------------+
|        1. Ingestion & Pre-Filter Layer        |
|   (Regex keyword check & URL deduplication)   |
+-----------------------+-----------------------+
                        |
                        v
+-----------------------------------------------+
|         2. AI Matching Engine (Gemini)        |
|    Compares raw job post <---> resume.md      |
|  Outputs structured JSON + Match Score (0-100)|
+-----------------------+-----------------------+
                        |
                        v
+-----------------------------------------------+
|          3. PostgreSQL Database               |
|   Stores structured jobs & application state  |
+-----------+-----------------------+-----------+
            |                       |
   Score >= 75%                     | All Matches (Score >= 50%)
            v                       v
+-----------------------+   +-----------------------+
|  Aiogram Telegram Bot |   |    React Dashboard    |
| (Instant Push Alerts) |   | (Kanban & Analytics)  |
+-----------------------+   +-----------------------+
```

---

## 🛠️ Tech Stack

### Backend & Ingestion
- **Runtime & API:** Python 3.11+, FastAPI
- **Telegram Client (Scraper):** Telethon (MTProto API)
- **Telegram Bot (Notifier):** Aiogram 3.x
- **LinkedIn Scraper:** `python-jobspy` & APScheduler
- **AI / LLM:** Google Gemini API (`google-genai` SDK)
- **Database:** PostgreSQL + SQLAlchemy

### Frontend Dashboard
- **Framework:** React (Vite) + TypeScript
- **Styling:** Tailwind CSS

---

## 📂 Project Structure

```text
job-radar-ai/
├── backend/
│   ├── app/
│   │   ├── config.py                 # Environment variables & channel lists
│   │   ├── database.py               # PostgreSQL connection & session setup
│   │   ├── models.py                 # SQLAlchemy database schemas
│   │   ├── main.py                   # FastAPI entry point & scheduler startup
│   │   ├── scrapers/
│   │   │   ├── telegram_listener.py  # Telethon real-time channel listener
│   │   │   └── linkedin_scraper.py   # JobSpy scheduled cron worker
│   │   ├── services/
│   │   │   ├── ai_matcher.py         # Gemini prompt & structured JSON parser
│   │   │   ├── deduplicator.py       # Hash & composite-key duplicate checker
│   │   │   └── notifier.py           # Aiogram bot push notification sender
│   │   └── data/
│   │       └── resume.md             # Personal resume & target preferences
│   ├── requirements.txt
│   └── .env.example
├── frontend/                         # React + Vite + Tailwind UI
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── App.tsx
│   └── package.json
└── README.md
```

---

## ⚙️ Prerequisites & API Keys

Before running the project, gather the following credentials:

1. **Telegram Client API (`API_ID` & `API_HASH`):**
   - Go to [my.telegram.org](https://my.telegram.org), log in with your phone number, and create an app under **API development tools**.
2. **Telegram Bot Token (`BOT_TOKEN` & `CHAT_ID`):**
   - Message [@BotFather](https://t.me/BotFather) on Telegram to create a notification bot and copy its token.
   - Message [@userinfobot](https://t.me/userinfobot) to get your personal numeric `CHAT_ID`.
3. **Gemini API Key (`GEMINI_API_KEY`):**
   - Generate an API key from [Google AI Studio](https://aistudio.google.com/).
4. **PostgreSQL Database (`DATABASE_URL`):**
   - Local PostgreSQL instance or a cloud provider (e.g., Supabase, Neon, Render).

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/biniambeza/job-radar-ai.git
cd job-radar-ai/backend
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:

```env
# Telegram MTProto Client (For reading public channels)
TG_API_ID=12345678
TG_API_HASH=your_telegram_api_hash
TG_PHONE_NUMBER=+251900000000
TG_TARGET_CHANNELS=freelance_ethiopia,habeshajobs,remote_dev_jobs

# Telegram Bot (For sending alerts to you)
TG_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TG_USER_CHAT_ID=987654321

# AI & Database
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=postgresql://postgres:password@localhost:5432/jobradar

# Matching Thresholds
INSTANT_ALERT_THRESHOLD=75
SAVE_TO_DB_THRESHOLD=50
```

### 4. Add Your Resume
Edit `backend/app/data/resume.md` and paste your full resume in Markdown format (skills, tech stack, experience level, education, and preferred job roles).

### 5. Run the Backend Pipeline
```bash
uvicorn app.main:app --reload
```
> **Note:** On the first run, Telethon will prompt you in the terminal to enter the one-time login code sent to your Telegram account to generate a local `.session` file.

---

## 🧠 How the AI Matching Works

Every incoming job post that passes the initial keyword filter is evaluated against `resume.md` using a strict schema:

```json
{
  "is_relevant_sector": true,
  "job_title": "Full-Stack Developer (React / Node.js)",
  "company": "TechSolutions Inc.",
  "source": "Telegram (@freelance_ethiopia)",
  "location_type": "Remote",
  "match_score": 91,
  "matching_skills": ["React", "TypeScript", "Node.js", "PostgreSQL"],
  "missing_skills": ["AWS Lambda"],
  "summary": "Seeking a full-stack engineer to build real-time logistics dashboards and REST APIs.",
  "apply_link_or_contact": "https://t.me/recruiter_handle"
}
```

### Routing Rules
- **Score >= 75%:** Saved to PostgreSQL + Instant Telegram push alert with summary and apply button.
- **Score 50% - 74%:** Saved quietly to PostgreSQL for review on the web dashboard.
- **Score < 50%:** Discarded automatically.

---

## 🗺️ Roadmap

- [x] Phase 1: Project architecture & configuration
- [ ] Phase 2: Database models & Resume parser (`resume.md`)
- [ ] Phase 3: Telethon real-time channel listener + Regex pre-filter
- [ ] Phase 4: Gemini API structured matcher & deduplication logic
- [ ] Phase 5: Aiogram notification bot integration
- [ ] Phase 6: LinkedIn scheduled scraper (`JobSpy`)
- [ ] Phase 7: React + Tailwind web dashboard & one-click AI cover letter integration

---

## 📄 License

This project is for personal productivity and educational use. Respect platform terms of service and rate limits when configuring scraping intervals.
