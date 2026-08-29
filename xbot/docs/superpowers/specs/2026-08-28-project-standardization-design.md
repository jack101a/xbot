# Architecture & Codebase Standardization Design Document

**Project:** XBot Twitter Automation Platform  
**Target:** Standardize entire codebase into clean, decoupled, production-grade modules (≤250–300 lines/file), eliminating all monoliths, fixing test issues, and establishing robust type and interface contracts.

---

## 1. Executive Summary & Goals
- **Modularity:** Deconstruct all monolithic files (>500 to ~2,900 lines) across both Backend and Dashboard frontend into single-responsibility modules strictly under 300 lines.
- **Reliability:** Fix the undeclared `re` module in sniper loops and guarantee 100% test pass rate across the 318 backend unit/integration tests.
- **Interconnectedness:** Establish airtight interfaces across FastAPI routers, Celery tasks, Redis locks, Playwright browser actions, AI engines, and the Next.js React UI.
- **Orchestration:** Coordinate autonomous coding workers with the best available model, enforcing continuous verification.

---

## 2. Backend Domain Decomposition

### 2.1 Tasks & Pipelines Layer (`backend/xbot/tasks/`)
Decomposing `tasks.py` (2,879 lines) into a domain-driven package with re-export facade in `__init__.py`:
- **`common.py`**: Shared async DB session context managers, Redis lock acquisition, retry decorators, and `sleep_with_jitter`.
- **`sniper_tasks.py`**: KOL target monitoring, latest tweet polling, and sniper reply generation (with explicit `import re`).
- **`campaign_tasks.py`**: Scheduled and on-demand campaign dispatching, thread orchestration, and media attachment.
- **`circadian_tasks.py`**: Circadian rhythm session scheduling, wake/sleep window validation, and variance calculation.
- **`trend_tasks.py`**: Trend radar scanner, dynamic topic drafting, and real-time research.
- **`growth_tasks.py`**: Follow/unfollow execution, F4F reciprocity evaluation, and realgraph updates.
- **`publish_tasks.py`**: Auto-publishing approved drafts and creator studio analytics sync.
- **`maintenance_tasks.py`**: Cookie refresh, browser health telemetry, session lock cleanup, and log rotation.

### 2.2 Browser Automation Actions (`backend/xbot/browser/actions/`)
Decomposing `x_actions.py` (2,004 lines) into atomic action files:
- **`post_action.py`**: Single tweet composer, link injection, media attachment.
- **`thread_action.py`**: Multi-post thread publishing with delay pacing.
- **`reply_action.py`**: Target tweet reply, quote tweet composer.
- **`engagement_action.py`**: Like, bookmark, and poll voting actions.
- **`follow_action.py`**: Follow user, unfollow user, profile relationship inspection.
- **`feed_navigation.py`**: Feed scrolling, keyword search, timeline tweet parsing.

### 2.3 FastAPI Routers (`backend/xbot/api/profiles/`)
Decomposing `api/profiles.py` (2,296 lines) into sub-routers:
- **`crud.py`**: Profile CRUD and slug resolution.
- **`campaigns.py`**: Profile campaign configuration, queue inspection, instant trigger.
- **`persona_memory.py`**: Persona YAML card parser, diary entries, memory updates.
- **`analytics.py`**: Analytics snapshots, growth graphs, creator metrics.
- **`sessions.py`**: Session execution logs, manual browser actions, real-time status.
- **`automation_state.py`**: Rate limit status, schedule toggle, circuit breaker override.

### 2.4 AI Brain Engines
- Decompose `hook_optimizer.py` (870 lines) into `hook_optimizer/` (templates, heuristics, generator).
- Decompose `sniper.py` (797 lines) into `sniper/` (evaluator, prompt builder, reply synthesizer).
- Modularize `pipelines/reply_pipeline.py` (514 lines) and `on_demand_campaign_pipeline.py` (509 lines).

---

## 3. Dashboard Frontend Decomposition

### 3.1 Feature Slices Pattern
Decompose giant tab components into bounded sub-components and custom hooks:
- **`features/growth-engine/`** (1,659 lines) -> `components/`, `hooks/useGrowthEngine.ts`, `types.ts`, `GrowthEngineTab.tsx` (<150 lines).
- **`features/overview/`** (1,068 lines) -> `components/`, `hooks/useOverviewStats.ts`, `OverviewTab.tsx` (<150 lines).
- **`features/live-activity/`** (909 lines) -> `components/`, `hooks/useLiveActivity.ts`, `LiveActivityTab.tsx` (<150 lines).
- **`features/campaign-studio/`** (695 lines) -> `components/`, `hooks/useCampaignStudio.ts`, `CampaignStudioTab.tsx` (<150 lines).
- **`features/persona/`** (651 lines) -> `components/`, `hooks/usePersonaMemory.ts`, `PersonaMemoryTab.tsx` (<150 lines).
- **`lib/api/`** (465 lines) -> Domain client modules (`profiles.ts`, `campaigns.ts`, `activity.ts`, `system.ts`).

---

## 4. Verification & Testing Standards
1. **Pytest Suite:** Run `backend/.venv/bin/pytest backend/tests/ -q` to guarantee 318/318 passing tests.
2. **Dashboard Build:** Run `npm run build` in `dashboard/` to verify Turbopack bundling, TypeScript types, and zero build errors.
3. **Celery Autodiscovery:** Verify `celery_app.autodiscover_tasks` resolves all task signatures cleanly.
