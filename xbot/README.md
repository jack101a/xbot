# XBot: Multi-Profile Autonomous Agent Automation System

XBot is an enterprise-grade autonomous social media agent platform. It manages multiple browser automation profiles, evaluates natural human-like schedules, performs LLM-driven planning and content generation, enforces safety limits with progressive backoffs and circuit breakers, tracks creator monetization progress, and exposes a beautiful glassmorphic Next.js admin dashboard.

---

## 🚀 Quick Start & Launch Runbook

Ensure you have Redis and Node.js/npm installed on your system.

### 1. Initialize the Environment
Copy the example environment file and configure variables:
```bash
cp .env.example .env
# Edit .env with your custom SQLite Database URL, Redis URL, LiteLLM base configuration, and optional Discord/Telegram Webhook URL.
```

### 2. Startup Backend Service (FastAPI)
Create a Python virtual environment and run the FastAPI server:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn xbot.main:app --host 0.0.0.0 --port 8200
```
Check health: `curl http://localhost:8200/api/health`

### 3. Launch Celery Worker & Beat Scheduler
In separate terminal windows/panes within the backend environment:
```bash
# Run Celery Worker for execution logs & analytics scrapes
celery -A xbot.tasks worker --loglevel=info

# Run Celery Beat for periodic schedule checker triggers
celery -A xbot.tasks beat --loglevel=info
```

### 4. Launch Next.js Dashboard UI
Compile and run the dashboard:
```bash
cd dashboard
npm install
npm run dev
```
Open `http://localhost:3000` to access the Control Center interface.

---

## 🛠 Project Structure

```
xbot/
├── backend/                   # FastAPI REST API & Task Workers
│   ├── xbot/
│   │   ├── ai/                # Context assembler, planning, generation pipeline
│   │   ├── api/               # Router endpoints (profiles, sessions, system limits)
│   │   ├── browser/           # Playwright automation (actions, delay pacing)
│   │   ├── safety/            # sliding window rate limiter, cooldowns, webhooks
│   │   ├── scheduling/        # Natural scheduling calculations
│   │   ├── celery_app.py      # Celery connection setup
│   │   └── tasks.py           # Worker loop execution tasks (run_session, check_schedules)
│   └── tests/                 # 22 passed unit and integration tests
├── dashboard/                 # Next.js 16 Client App (Control Center)
│   ├── src/
│   │   ├── app/               # App Router pages and custom styling
│   │   └── lib/               # Fetch API wrappers
├── data/
│   └── profiles/              # Stored YAML configurations and JSONL logs per profile
├── backup.sh                  # Daily hot-database & profiles state archiver
└── README.md                  # This runbook document
```

---

## 🛡 Safety Guard & Webhook Alerting

XBot coordinates several defensive systems to safeguard profiles from detection:
1. **Sliding-Window Rate Limiter**: Uses Redis sorted-sets to keep track of hourly/daily caps.
2. **Pacing Cooldowns**: Applies randomized delays (e.g. 5-15 min between likes) to ensure human-like cadence.
3. **Warm-Up Multipliers**: Limits are dynamically scaled based on account age (e.g. 25% cap for the first week).
4. **Progressive Backoffs & Circuit Breaker**: Activates a 50% limit reduction on 429 warnings and pauses schedules automatically on 3 consecutive failures.
5. **Webhook Alerts**: Dispatches Discord/Telegram alerts upon critical events (account locked, CAPTCHA detected, circuit breaker tripped) if `WEBHOOK_URL` is set in the environment.

---

## 💾 System Backups & Rotation Policy

A production-ready `backup.sh` is provided in the project root. It performs a hot-backup of the database and copies profile logs/memories/personals into compressed archives, automatically keeping only the last 7 daily files.

To schedule daily backups at 2:00 AM, add a cron job:
```bash
0 2 * * * /home/ubuntu/projects/xbot/backup.sh >> /home/ubuntu/projects/xbot/backups/backup.log 2>&1
```

---

## 🧪 Running Tests
To run unit and integration tests, run `pytest` inside the backend directory:
```bash
cd backend
.venv/bin/pytest
```
All 22 test flows will execute, validating the compiler state, browser managers, scheduling arrays, and REST controllers.
