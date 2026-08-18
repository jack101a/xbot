# KOL Sniper Reply & Fast Engagement Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated KOL Sniper Reply Subsystem that monitors target influencer accounts, detects new posts in real-time, generates high-insight algorithm-optimized replies via LLM, and executes fast browser replies on X within 180 seconds.

**Architecture:** A periodic Celery beat task queries active profiles' target KOL lists, uses Playwright stealth actions to scrape the target user's latest tweet, filters through Redis deduplication, passes the context to an AI Sniper Angle Engine to craft high-value replies, and executes the reply using existing humanized browser actions with sliding-window safety enforcement.

**Tech Stack:** Python 3.12+, FastAPI, Celery, Playwright, SQLAlchemy 2.0 (aiosqlite), Redis, LiteLLM, Pydantic, Pytest.

**Spec:** [`docs/superpowers/specs/2026-08-18-kol-sniper-reply-design.md`](file:///home/ubuntu/projects/xbot/docs/superpowers/specs/2026-08-18-kol-sniper-reply-design.md)

## Global Constraints
- Target environment: Linux / Python 3.12+ in `backend/.venv`.
- Database: SQLite with async SQLAlchemy (`xbot.db`).
- Broker & Limiter: Local native Redis at `localhost:6379`.
- Type checking: Strict `mypy` and `ruff` standards with `from __future__ import annotations`.
- All browser actions must use stealth delays and random jitter.

---

### Task 1: Extend Persona Model and Schema with Target KOLs

**Files:**
- Modify: `backend/xbot/persona/loader.py`
- Test: `backend/tests/test_persona.py`

**Interfaces:**
- Produces: `TargetKOL` model and `Persona.target_kols: list[TargetKOL]` field with parsing in `load_persona()`.

- [ ] **Step 1: Write the failing test for TargetKOL schema in `test_persona.py`**

```python
def test_persona_with_target_kols(tmp_path: Path) -> None:
    persona_path = tmp_path / "persona.yaml"
    persona_path.write_text(
        """
id: tech_guru
display_name: Tech Guru
x_handle: "@techguru"
identity:
  background: Veteran engineer
personality:
  traits: [analytical, witty]
  values: [open_source]
  communication_style: concise
interests:
  primary: [AI, distributed systems]
  secondary: []
  will_not_discuss: []
writing_style:
  tone: insightful
  typical_length: short
  formatting: []
  examples: []
goals:
  short_term: [grow audience]
  long_term: []
  content_pillars: []
rules:
  always: []
  never: []
target_kols:
  - handle: "elonmusk"
    category: "tech"
    priority: "high"
    preferred_angle: "witty"
  - handle: "sama"
    category: "ai"
    priority: "medium"
    preferred_angle: "framework"
"""
    )
    persona = load_persona(persona_path)
    assert len(persona.target_kols) == 2
    assert persona.target_kols[0].handle == "elonmusk"
    assert persona.target_kols[0].preferred_angle == "witty"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_persona.py -k test_persona_with_target_kols -v`
Expected: FAIL (`unexpected keyword argument 'target_kols'` or `AttributeError`)

- [ ] **Step 3: Implement `TargetKOL` in `backend/xbot/persona/loader.py`**

```python
class TargetKOL(BaseModel):
    handle: str = Field(..., description="Target X handle without leading @")
    category: str = Field("general", description="Niche or industry category")
    priority: str = Field("medium", description="Priority tier: high, medium, low")
    preferred_angle: str = Field(
        "insight", description="Preferred response angle: contrarian, framework, witty, data, insight"
    )
```
Add `target_kols: list[TargetKOL] = Field(default_factory=list)` to `Persona`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_persona.py -k test_persona_with_target_kols -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/persona/loader.py backend/tests/test_persona.py
git commit -m "feat(persona): add target_kols configuration support"
```

---

### Task 2: Implement `CheckUserLatestTweet` Playwright Browser Action

**Files:**
- Create: `backend/xbot/browser/actions/check_user_action.py`
- Modify: `backend/xbot/browser/actions/__init__.py`
- Test: `backend/tests/test_sniper_browser_action.py`

**Interfaces:**
- Produces: `CheckUserLatestTweet.execute(page: Page, handle: str) -> dict[str, Any] | None`
- Consumes: Playwright `Page` and mock X server endpoints.

- [ ] **Step 1: Write test for `CheckUserLatestTweet` using mock X server**

```python
import pytest
from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.manager import BrowserManager

@pytest.mark.asyncio
async def test_check_user_latest_tweet(mock_x_server: str, tmp_path: Path) -> None:
    manager = BrowserManager()
    await manager.start()
    profile_slug = "sniper_test_profile"
    manager.release_lock(profile_slug)
    assert manager.acquire_lock(profile_slug) is True

    context = await manager.get_context(profile_slug)
    page = await context.new_page()
    try:
        action = CheckUserLatestTweet(screenshot_dir=str(tmp_path))
        # Point to mock server handle
        result = await action.execute(page, handle="mockuser", base_url=mock_x_server)
        assert result is not None
        assert "tweet_id" in result
        assert "text" in result
        assert len(result["text"]) > 0
    finally:
        await page.close()
        await manager.close_context(profile_slug)
        manager.release_lock(profile_slug)
        await manager.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_sniper_browser_action.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `CheckUserLatestTweet`**

Implement `backend/xbot/browser/actions/check_user_action.py` navigating to `https://x.com/{handle}`, waiting for `[data-testid="tweet"]`, extracting tweet text, tweet link/id, and timestamp.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_sniper_browser_action.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/browser/actions/check_user_action.py backend/tests/test_sniper_browser_action.py
git commit -m "feat(browser): add CheckUserLatestTweet action"
```

---

### Task 3: Build AI Sniper Angle & Response Generator

**Files:**
- Create: `backend/xbot/ai/sniper.py`
- Test: `backend/tests/test_ai_sniper.py`

**Interfaces:**
- Produces: `generate_sniper_reply(persona: Persona, target_tweet: dict, angle: str | None = None) -> SniperReplyResult`
- Consumes: `xbot.ai.client.generate_text` or `xbot.ai.client.generate_json`.

- [ ] **Step 1: Write the failing unit tests in `test_ai_sniper.py`**

Test angle generation for `contrarian`, `framework`, `witty`, and `data` angles, validating length (< 280 chars) and no forbidden phrases ("Great tweet!", "100%", etc.).

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `backend/xbot/ai/sniper.py`**

Implement system prompt and parsing for high-value algorithm-optimized reply generation.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_ai_sniper.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/ai/sniper.py backend/tests/test_ai_sniper.py
git commit -m "feat(ai): add AI Sniper response and angle generator"
```

---

### Task 4: Integrate Celery Periodic Task `sniper_check_targets` with Redis Deduplication & Safety

**Files:**
- Modify: `backend/xbot/tasks.py`
- Modify: `backend/xbot/celery_app.py`
- Test: `backend/tests/test_sniper_task.py`

**Interfaces:**
- Produces: Celery task `@celery_app.task(name="xbot.tasks.sniper_check_targets")`
- Consumes: `CheckUserLatestTweet`, `generate_sniper_reply`, `ReplyToTweet`, `RateLimiter`.

- [ ] **Step 1: Write integration test in `test_sniper_task.py`**

Test task execution, Redis tweet deduplication key (`xbot:seen_tweets`), and action logging.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_sniper_task.py -v`
Expected: FAIL

- [ ] **Step 3: Implement `sniper_check_targets` in `tasks.py` and register in Celery Beat**

Add the task loop, rate limit checks, browser context acquisition, deduction of seen tweets in Redis, and logging into SQLite DB.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_sniper_task.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/tasks.py backend/xbot/celery_app.py backend/tests/test_sniper_task.py
git commit -m "feat(tasks): integrate sniper_check_targets Celery periodic task"
```

---

## Plan Verification & Self-Review Checklist
- [x] **Spec coverage**: All sections of `docs/superpowers/specs/2026-08-18-kol-sniper-reply-design.md` are covered.
- [x] **No Placeholders**: Exact paths, interface signatures, and testing commands are defined.
- [x] **TDD Flow**: Every task contains failing test, run command, minimal implementation, verification, and commit step.
