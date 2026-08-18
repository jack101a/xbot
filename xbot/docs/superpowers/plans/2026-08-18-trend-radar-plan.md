# Real-Time Trend Radar & Breaking News Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Real-Time Trend Radar & Breaking News Subsystem that ingests RSS and trending feeds, filters news against persona interests, generates high-insight 3-bullet takes + hot takes with optimized hooks, and schedules or posts them autonomously.

**Architecture:** A Trend Radar Ingestion module (`xbot.ai.trend_radar`) fetches and parses RSS/news feeds, a Trend Take Synthesizer (`xbot.ai.trend_generator`) evaluates relevance and writes persona-aligned takes with hook optimization, and a Celery periodic task (`xbot.tasks.check_trend_radar`) executes the pipeline on a 30-minute interval with Redis deduplication.

**Tech Stack:** Python 3.12+, FastAPI, Celery, httpx, xml.etree, Redis, SQLAlchemy 2.0, Pydantic, LiteLLM, Pytest.

**Spec:** [`docs/superpowers/specs/2026-08-18-trend-radar-design.md`](file:///home/ubuntu/projects/xbot/docs/superpowers/specs/2026-08-18-trend-radar-design.md)

## Global Constraints
- Target environment: Linux / Python 3.12+ in `backend/.venv`.
- Deduplication: Redis key `xbot:seen_trends:{profile_id}:{trend_id}` with TTL (7 days).
- HTTP requests: Async `httpx.AsyncClient` with timeout (10s) and error handling.
- Type checking: Strict `mypy` and `ruff` standards with `from __future__ import annotations`.

---

### Task 1: Build the Trend Radar Ingestion Engine

**Files:**
- Create: `backend/xbot/ai/trend_radar.py`
- Modify: `backend/xbot/ai/__init__.py`
- Test: `backend/tests/test_trend_radar.py`

**Interfaces:**
- Produces: `TrendItem`, `fetch_rss_trends(feed_urls: list[str], keywords: list[str] | None = None) -> list[TrendItem]`

- [ ] **Step 1: Write unit tests in `backend/tests/test_trend_radar.py`**

Test RSS/Atom XML parsing, item extraction (title, summary, link, guid, date), keyword filtering, and HTTP network error handling.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_radar.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `backend/xbot/ai/trend_radar.py`**

Implement `TrendItem` model, `_parse_rss_xml` using `xml.etree.ElementTree`, and async `fetch_rss_trends`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_radar.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/ai/trend_radar.py backend/xbot/ai/__init__.py backend/tests/test_trend_radar.py
git commit -m "feat(ai): add trend radar RSS ingestion engine"
```

---

### Task 2: Build the Trend Relevance Filter & Breaking Take Generator

**Files:**
- Create: `backend/xbot/ai/trend_generator.py`
- Modify: `backend/xbot/ai/__init__.py`
- Test: `backend/tests/test_trend_generator.py`

**Interfaces:**
- Produces: `TrendEvaluation`, `generate_trend_take(persona: Persona, trend_item: TrendItem, client: Any | None = None) -> TrendEvaluation`

- [ ] **Step 1: Write unit tests in `backend/tests/test_trend_generator.py`**

Test persona relevance evaluation, 3-bullet breakdown formulation, hot take generation, winning hook integration, and API exception fallback.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_generator.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `backend/xbot/ai/trend_generator.py`**

Implement `TrendEvaluation` model, persona prompt, structured take synthesis, and integration with `optimize_post_hook`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/ai/trend_generator.py backend/xbot/ai/__init__.py backend/tests/test_trend_generator.py
git commit -m "feat(ai): add trend relevance filter and breaking take generator"
```

---

### Task 3: Integrate Celery Periodic Task `check_trend_radar` & Content Staging

**Files:**
- Modify: `backend/xbot/tasks.py`
- Modify: `backend/xbot/celery_app.py`
- Test: `backend/tests/test_trend_task.py`

**Interfaces:**
- Produces: `@celery_app.task(name="xbot.tasks.check_trend_radar")`
- Consumes: `fetch_rss_trends`, `generate_trend_take`, `Content`, `SafetyGuard`.

- [ ] **Step 1: Write integration tests in `backend/tests/test_trend_task.py`**

Test task registration, Redis deduplication preventing duplicate posts, active profile scanning, and `Content` queue insertion.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_task.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `check_trend_radar` in `backend/xbot/tasks.py` and register in `backend/xbot/celery_app.py`**

Implement async pipeline checking feeds, deduplicating via Redis, evaluating takes, and queuing/posting content.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_trend_task.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/tasks.py backend/xbot/celery_app.py backend/tests/test_trend_task.py
git commit -m "feat(tasks): integrate check_trend_radar Celery periodic task"
```
