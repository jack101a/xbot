# Viral Hook Optimizer & Native X Poll Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Viral Hook Optimizer & Native X Poll Subsystem that crafts 4 high-retention hook archetypes, uses an AI judge to pick the best scroll-stopping opening, generates interactive polls, and automates poll creation via stealth Playwright browser actions.

**Architecture:** An AI Hook Optimizer (`xbot.ai.hook_optimizer`) scores and injects winning hooks into posts, an AI Poll Generator (`xbot.ai.poll_generator`) creates 2-4 option debate polls, and a Playwright `CreatePoll` action (`xbot.browser.actions.poll_action`) interacts with X's native poll modal to execute interactive posts.

**Tech Stack:** Python 3.12+, FastAPI, Celery, Playwright, SQLAlchemy 2.0, Pydantic, LiteLLM, Pytest.

**Spec:** [`docs/superpowers/specs/2026-08-18-viral-hook-and-poll-design.md`](file:///home/ubuntu/projects/xbot/docs/superpowers/specs/2026-08-18-viral-hook-and-poll-design.md)

## Global Constraints
- Target environment: Linux / Python 3.12+ in `backend/.venv`.
- X Poll constraints: 2 to 4 options, each option text maximum 25 characters.
- Hook constraints: Under 140 characters before line break, zero generic AI phrases ("In this thread...", "Let's dive in").
- Type checking: Strict `mypy` and `ruff` standards with `from __future__ import annotations`.

---

### Task 1: Build the Viral Hook Optimizer & Scorer

**Files:**
- Create: `backend/xbot/ai/hook_optimizer.py`
- Modify: `backend/xbot/ai/__init__.py`
- Test: `backend/tests/test_hook_optimizer.py`

**Interfaces:**
- Produces: `optimize_post_hook(persona: Persona, draft_content: str, topic: str, client: Any | None = None) -> HookOptimizationResult`
- Produces models: `HookCandidate`, `HookOptimizationResult`.

- [ ] **Step 1: Write unit tests in `backend/tests/test_hook_optimizer.py`**

Test generation of 4 hook archetypes (`curiosity_gap`, `contrarian`, `framework_breakdown`, `story_relatable`), AI scoring logic, winning hook selection, and fallback when LLM call fails.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_hook_optimizer.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `backend/xbot/ai/hook_optimizer.py`**

Implement `HookCandidate`, `HookOptimizationResult`, multi-hook generation prompt, judge prompt, and `optimize_post_hook`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_hook_optimizer.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/ai/hook_optimizer.py backend/xbot/ai/__init__.py backend/tests/test_hook_optimizer.py
git commit -m "feat(ai): add viral hook multi-generator and evaluator"
```

---

### Task 2: Build the AI Poll Generator

**Files:**
- Create: `backend/xbot/ai/poll_generator.py`
- Modify: `backend/xbot/ai/__init__.py`
- Test: `backend/tests/test_poll_generator.py`

**Interfaces:**
- Produces: `generate_poll(persona: Persona, topic: str | None = None, client: Any | None = None) -> GeneratedPoll`
- Produces model: `GeneratedPoll` with `question: str`, `options: list[str]` (2-4 items, each <= 25 chars), `duration_days: int`.

- [ ] **Step 1: Write unit tests in `backend/tests/test_poll_generator.py`**

Test validation rules (2-4 choices, choice length <= 25 chars), prompt structure, structured parsing, and exception safe fallback.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_poll_generator.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `backend/xbot/ai/poll_generator.py`**

Implement `GeneratedPoll` model, system prompt emphasizing engaging niche debates, option length truncator/validator, and `generate_poll()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_poll_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/ai/poll_generator.py backend/xbot/ai/__init__.py backend/tests/test_poll_generator.py
git commit -m "feat(ai): add AI poll generator with option length validation"
```

---

### Task 3: Implement `CreatePoll` Playwright Browser Action

**Files:**
- Create: `backend/xbot/browser/actions/poll_action.py`
- Modify: `backend/xbot/browser/actions/__init__.py`
- Modify: `backend/xbot/browser/actions/x_actions.py`
- Test: `backend/tests/test_poll_browser_action.py`

**Interfaces:**
- Produces: `CreatePoll.execute(page: Page, question: str, options: list[str], duration_days: int = 1) -> bool`
- Consumes: Playwright `Page` and selectors.

- [ ] **Step 1: Write tests in `backend/tests/test_poll_browser_action.py`**

Test 2-option poll creation, 4-option poll creation with add choice clicks, and failure screenshot capture.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_poll_browser_action.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement `backend/xbot/browser/actions/poll_action.py`**

Implement `CreatePoll(BaseAction)` with humanized delays, typing jitter, option field locators, and submission.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_poll_browser_action.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/browser/actions/poll_action.py backend/xbot/browser/actions/__init__.py backend/xbot/browser/actions/x_actions.py backend/tests/test_poll_browser_action.py
git commit -m "feat(browser): add CreatePoll Playwright browser action"
```

---

### Task 4: Integrate Hook Optimization & Polls into Content Pipeline & Tasks

**Files:**
- Modify: `backend/xbot/ai/generator.py`
- Modify: `backend/xbot/models/session.py` (add `ActionType.POLL`)
- Modify: `backend/xbot/tasks.py` (execute poll actions in session loop)
- Test: `backend/tests/test_poll_integration.py`

**Interfaces:**
- Produces: Seamless hook optimization in `ContentGenerator.generate_tweet()` and execution of `ActionType.POLL` in `tasks.py`.

- [ ] **Step 1: Write integration tests in `backend/tests/test_poll_integration.py`**

Verify that `ContentGenerator` enhances tweets with hook optimization and that `_run_session_async` handles poll actions.

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/pytest backend/tests/test_poll_integration.py -v`
Expected: FAIL

- [ ] **Step 3: Implement integration changes**

Integrate `optimize_post_hook` in `generator.py`, add `ActionType.POLL` in `session.py`, and add poll execution handler in `tasks.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `backend/.venv/bin/pytest backend/tests/test_poll_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

```bash
git add backend/xbot/ai/generator.py backend/xbot/models/session.py backend/xbot/tasks.py backend/tests/test_poll_integration.py
git commit -m "feat(integration): wire viral hook optimization and polls into content generator and tasks"
```
