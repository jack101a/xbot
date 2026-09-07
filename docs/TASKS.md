# Tasks: XBot

## Active Task
- **Task:** Phase 3.1: Implement natural schedule algorithm (Celery Beat) in `backend/xbot/scheduling/` directory.

## Phase 0: Foundation
- [x] Phase 0.1: Initialize Python project in `backend/` with `uv`, configuration for `ruff` & `mypy`, and basic FastAPI server.
- [x] Phase 0.2: Set up infrastructure (SQLite database, native Redis broker, VPS LiteLLM).
- [x] Phase 0.3: Design and implement SQLAlchemy models (`profiles`, `sessions`, `actions`, `action_results`, `analytics_snapshots`, `content`, `rate_limits`) and Alembic migrations.
- [x] Phase 0.4: Build basic FastAPI profile CRUD endpoints (`GET /profiles`, `POST /profiles`, etc.).
- [x] Phase 0.5: Set up Celery worker and beat infrastructure.
- [x] Phase 0.6: Configure Portainer stack template. (Skipped: no Docker/Portainer)

## Phase 1: Browser Engine + Persona
- [x] Build BrowserManager with Playwright and stealth config
- [x] Build action library (browse, like, post, reply, follow)
- [x] Implement timing engine with human-like delays
- [x] Build persona YAML loader and memory/diary system (JSONL)
- [x] Implement mock X server for browser testing
- [x] Build session lifecycle management and error handling

## Phase 2: AI Brain
- [x] Build context assembler (persona + diary + memories) — *Completed 2026-06-18*
- [x] Implement session planning prompt and JSON parsing — *Completed 2026-06-18*
- [x] Build content generation pipeline with validation — *Completed 2026-06-18*
- [x] Implement fast engagement decision flow — *Completed 2026-06-18*
- [x] Build post-session processing (update diary/memories) — *Completed 2026-06-18*
- [x] Implement weekly strategy review logic — *Completed 2026-06-18*

## Phase 3: Scheduling & Safety
- [ ] Implement natural schedule algorithm (Celery Beat)
- [ ] Build Redis-based sliding window rate limiter
- [ ] Implement cooldowns, warm-ups, and session variance
- [ ] Build circuit breaker and progressive backoff
- [ ] Add health signal detection (CAPTCHA, lock out)

## Phase 4: Analytics & Dashboard
- [ ] Build analytics snapshot collection process
- [ ] Implement content performance scoring
- [ ] Build monetization progress tracker
- [ ] Initialize Next.js dashboard project
- [ ] Build Overview, Profile Detail, and Session Log pages
- [ ] Build Analytics and Rate Limits dashboards
- [ ] Implement WebSocket live session monitoring
- [ ] Build Persona Editor UI

## Phase 5: Polish & Hardening
- [ ] End-to-end system load testing
- [ ] Finalize backup strategy for volumes
- [ ] Write system documentation and runbooks
- [ ] Add webhook alerting for critical events
- [ ] Log rotation and cleanup tasks
- [ ] Performance optimizations (browser memory management)
