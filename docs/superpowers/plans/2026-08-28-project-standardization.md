# XBot Codebase Standardization & Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize and modularize the entire XBot repository, eliminating all files >300 lines of code across Backend and Frontend, establishing clean domain packages, resolving all test failures, and ensuring 100% interconnected reliability.

**Architecture:** Domain-driven decomposition for backend tasks, actions, and API routers; Feature-slice modularization with hooks and component extraction for the Next.js dashboard.

**Tech Stack:** Python 3.11, FastAPI, Celery, SQLAlchemy, Playwright, Next.js 16 (Turbopack), TypeScript, Tailwind CSS.

**Spec:** `docs/superpowers/specs/2026-08-28-project-standardization-design.md`

## Global Constraints
- Every source file MUST stay ≤ 250–300 lines of code.
- Zero broken imports: package `__init__.py` files must re-export all public functions, classes, and Celery task definitions.
- 100% test pass rate across backend pytest suite (318/318 passing).
- Zero TypeScript/build errors on Next.js production build (`npm run build`).

---

### Task 1: Decompose Backend Tasks Layer (`tasks.py` -> `tasks/`)
- Create `backend/xbot/tasks/` subpackage.
- Create `common.py`, `sniper_tasks.py` (with explicit `import re`), `campaign_tasks.py`, `circadian_tasks.py`, `trend_tasks.py`, `growth_tasks.py`, `publish_tasks.py`, `maintenance_tasks.py`.
- Create `backend/xbot/tasks/__init__.py` re-exporting all tasks and helpers.
- Run `backend/.venv/bin/pytest backend/tests/test_sniper_task.py backend/tests/test_link_injection_and_pipeline.py` and verify all tests pass.

### Task 2: Decompose Backend Browser Actions (`x_actions.py` -> `actions/`)
- Create `backend/xbot/browser/actions/` modules: `post_action.py`, `thread_action.py`, `reply_action.py`, `engagement_action.py`, `follow_action.py`, `feed_navigation.py`.
- Update `backend/xbot/browser/actions/__init__.py` with re-export facade.
- Run `backend/.venv/bin/pytest backend/tests/test_x_actions.py` and verify all tests pass.

### Task 3: Decompose FastAPI Profiles Router & AI Monoliths
- Create `backend/xbot/api/profiles/` subpackage: `crud.py`, `campaigns.py`, `persona_memory.py`, `analytics.py`, `sessions.py`, `automation_state.py`.
- Create `backend/xbot/api/profiles/__init__.py` assembling the unified profile APIRouter.
- Modularize `hook_optimizer.py` and `sniper.py` into dedicated sub-packages.
- Run backend pytest suite to verify all API and AI tests pass.

### Task 4: Decompose Dashboard Frontend Feature Slices
- Modularize `GrowthEngineTab.tsx` (1,659 lines) into components, custom hooks, and types.
- Modularize `OverviewTab.tsx` (1,068 lines), `LiveActivityTab.tsx` (909 lines), `CampaignStudioTab.tsx` (695 lines), and `PersonaMemoryTab.tsx` (651 lines).
- Modularize `dashboard/src/lib/api.ts` (465 lines) into domain modules.
- Run `npm run build` in `dashboard/` to verify clean build.

### Task 5: Final Verification & Integration Audit
- Run full backend test suite: 318/318 passing.
- Run frontend build: successful static export.
- Verify file sizes: confirm no file exceeds 300 lines.
