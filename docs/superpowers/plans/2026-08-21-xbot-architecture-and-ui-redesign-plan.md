# XBot Architecture & UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up legacy bloat, harden the backend AI persona & stealth engine, and refactor the monolithic dashboard into a modern, modular 5-tab Glassmorphic UI.

**Architecture:** Purge deprecated campaign/crawler/scraper dead code; harden FastAPI and WebSocket streaming; decompose the 2,978-line `page.tsx` into modular components (`Sidebar`, `OverviewTab`, `GrowthEngineTab`, `LiveActivityTab`, `PersonaMemoryTab`, `LimitsSchedulerTab`, `GlobalSettingsModal`); ensure full type-safety and test coverage.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Playwright, Redis, Next.js 16, React 19, TypeScript, Tailwind CSS, Lucide React, Pytest.

**Spec:** `docs/superpowers/specs/2026-08-21-xbot-architecture-and-ui-redesign-design.md`

## Global Constraints
- Do NOT break existing core tests in `backend/tests/`.
- Ensure all frontend network calls use `api.ts` with dynamic base URLs (no hardcoded `localhost:18234` or `localhost:8200`).
- Use Glassmorphic styling with dark/light mode compatibility across all UI components.
- Maintain strict rate limiting and humanized timing safety invariants for Playwright automation.

---

### Task 1: Repository Purge & Legacy Cleanup

**Files:**
- Delete:
  - `add_profile_job_ui.py`
  - `fix_tab_location.py`
  - `patch_api_ts.py`
  - `patch_page.py`
  - `patch_page_tsx.py`
  - `backend/patch_api_profiles.py`
  - `backend/patch_client.py`
  - `backend/patch_engagement_learned.py`
  - `backend/patch_engagement.py`
  - `backend/patch_engagement_reply.py`
  - `backend/patch_generator_learned.py`
  - `backend/patch_generator.py`
  - `backend/patch_loader.py`
  - `backend/patch_post_session.py`
  - `backend/patch_system.py`
  - `backend/patch_tasks_reflection.py`
  - `backend/update_config_defaults.py`
  - `backend/update_env.py`
  - `backend/test_*.db`
  - `backend/xbot/campaign_manager.py`
  - `dashboard/src/components/AudienceNetworkTab.tsx`
  - `dashboard/src/components/CampaignsTab.tsx`
- Modify:
  - `backend/xbot/api/profiles.py` (remove campaign, social-graph, follower-snapshot/changelog/audit legacy endpoints)
  - `backend/xbot/api/tools.py` (clean up scraper profile dependency)
  - `backend/xbot/api/__init__.py`

- [ ] **Step 1: Delete all leftover patch scripts and temporary SQLite files**
```bash
rm -f add_profile_job_ui.py fix_tab_location.py patch_api_ts.py patch_page.py patch_page_tsx.py
rm -f backend/patch_*.py backend/update_*.py backend/test_*.db
rm -f backend/xbot/campaign_manager.py
rm -f dashboard/src/components/AudienceNetworkTab.tsx dashboard/src/components/CampaignsTab.tsx
```

- [ ] **Step 2: Clean up deprecated router endpoints in `backend/xbot/api/profiles.py`**
Remove endpoints for `/follower-snapshots`, `/follower-changelogs`, `/follower-audit`, `/campaigns`, `/campaigns/{id}/run`, `/reputation-history`, `/reputation-analysis`, `/social-graph`, `/social-graph/crawl`, and `/autoreply-mentions`.

- [ ] **Step 3: Run existing unit tests to verify nothing broke**
```bash
backend/.venv/bin/pytest backend/tests/test_ai_assembler.py backend/tests/test_ai_sniper.py backend/tests/test_hook_optimizer.py backend/tests/test_poll_generator.py backend/tests/test_trend_radar.py backend/tests/test_trend_generator.py backend/tests/test_profile_auth.py backend/tests/test_sync_profile_action.py backend/tests/test_persona.py
```

- [ ] **Step 4: Commit cleanup**
```bash
git add -A
git commit -m "refactor: purge deprecated legacy campaigns, crawlers, and temporary patch scripts"
```

---

### Task 2: Backend API & WebSocket Hardening

**Files:**
- Modify: `backend/xbot/api/sessions.py`
- Modify: `backend/xbot/api/system.py`
- Modify: `backend/xbot/ai/reflection.py`
- Test: `backend/tests/test_reflection_learning.py`

**Interfaces:**
- Consumes: Redis pub/sub and WebSocket streaming in `sessions.py`
- Produces: Clean WebSocket endpoints `/api/ws/live` and `/api/ws/sessions/{session_id}` broadcasting normalized `LiveEvent` payloads.

- [ ] **Step 1: Write test for performance-driven cognitive reflection**
Create `backend/tests/test_reflection_learning.py` testing that post performance metrics (top tweets with high engagement) are correctly formatted and fed into `reflect_and_update`.

- [ ] **Step 2: Run test to verify it fails**
```bash
backend/.venv/bin/pytest backend/tests/test_reflection_learning.py
```

- [ ] **Step 3: Implement performance metric reflection ingestion**
Enhance `reflect_and_update()` in `backend/xbot/ai/reflection.py` to accept recent `top_tweets` and follower changes, and synthesize actionable learned insights.

- [ ] **Step 4: Verify WebSocket endpoints in `backend/xbot/api/sessions.py`**
Ensure message formats sent to `ws_live` and `ws_sessions` contain standardized event keys (`event`, `timestamp`, `session_id`, `action_type`, `status`, `content`, `error`).

- [ ] **Step 5: Run tests and ensure all pass**
```bash
backend/.venv/bin/pytest backend/tests/test_reflection_learning.py
```

- [ ] **Step 6: Commit backend improvements**
```bash
git add backend/xbot/api/sessions.py backend/xbot/ai/reflection.py backend/tests/test_reflection_learning.py
git commit -m "feat(ai): add tweet performance feedback to cognitive reflection loop"
```

---

### Task 3: Dashboard API Client & Modular Sub-Components

**Files:**
- Modify: `dashboard/src/lib/api.ts`
- Create: `dashboard/src/components/Sidebar.tsx`
- Create: `dashboard/src/components/OverviewTab.tsx`
- Create: `dashboard/src/components/PersonaMemoryTab.tsx`
- Create: `dashboard/src/components/LimitsSchedulerTab.tsx`
- Create: `dashboard/src/components/GlobalSettingsModal.tsx`
- Modify: `dashboard/src/components/GrowthEngineTab.tsx`
- Modify: `dashboard/src/components/LiveActivityTab.tsx`
- Modify: `dashboard/src/components/ConnectAccountModal.tsx`

**Interfaces:**
- `api.ts`: Central typed API client with dynamic HTTP (`/api/...`) and dynamic WebSocket (`/api/ws/live` and `/api/ws/sessions/{id}`).

- [ ] **Step 1: Refactor `dashboard/src/lib/api.ts`**
Remove deprecated endpoints (campaigns, social graph, free tools); standardize `API_BASE_URL` and `WS_BASE_URL` to derive dynamically from `window.location` or `process.env.NEXT_PUBLIC_API_BASE_URL`.

- [ ] **Step 2: Build `dashboard/src/components/Sidebar.tsx`**
Create modern glassmorphic sidebar featuring:
- Profile Switcher Dropdown (with Avatar, Handle, Status indicator).
- Add Profile button.
- Primary navigation tabs: Overview, Growth Engine, Live Activity, Persona & Memory, Limits & Automation.
- Bottom footer: System Health status indicator (Healthy/Unhealthy, Redis status), Global Settings button, Dark/Light Theme toggle.

- [ ] **Step 3: Build `dashboard/src/components/OverviewTab.tsx`**
Create Overview tab displaying:
- Profile Hero card (Avatar, Handle, Bio, Follower/Following counts, Account Age/Status).
- "Run Session Now" quick trigger with active progress indicator.
- "Sync with X" button.
- 24-Hour Limits Progress bars (Posts, Replies, Likes vs daily limits).
- Recent Sessions quick list with status badges.

- [ ] **Step 4: Refactor `dashboard/src/components/GrowthEngineTab.tsx`**
Modularize sub-tools:
- **KOL Sniper:** Target list table (handle, category, priority, preferred angle), Add KOL modal/inline form, Test Reply simulator.
- **Hook Optimizer:** Interactive draft tester, 6-archetype score bars, winning hook selector.
- **Poll Generator:** Topic prompt, generated choices (truncated to 25 chars), duration selector, post/draft buttons.
- **Trend Radar:** Active RSS feeds, relevance scoring list, one-click trend tweet generator.

- [ ] **Step 5: Refactor `dashboard/src/components/LiveActivityTab.tsx`**
- Fix WebSocket URL to use `api.getWebSocketUrl()`.
- Real-time streaming log with colored event pills.
- Expandable session history cards showing planned vs completed actions, reasoning, durations, and errors.

- [ ] **Step 6: Build `dashboard/src/components/PersonaMemoryTab.tsx`**
- Identity & Voice editor: Persona name, style, voice tone sliders/tags.
- Target Topics & Anti-Topics (tags/chips input).
- Daily Diary browser (dates list, markdown viewer for `YYYY-MM-DD.md`).
- Cognitive Long-Term Memories viewer with manual add/delete and "Trigger Reflection Now" button.

- [ ] **Step 7: Build `dashboard/src/components/LimitsSchedulerTab.tsx`**
- Action rate limits: Max posts/day, max replies/hour, max likes/day, max follows/day.
- Randomized delay sliders: Cooldown between actions (min/max seconds).
- Active hours scheduler: Daily start and end time with organic jitter.
- Warm-up account multiplier info.

- [ ] **Step 8: Build `dashboard/src/components/GlobalSettingsModal.tsx`**
- Modal for AI Providers: LiteLLM, Google Gemini, Mistral, OpenRouter, DeepSeek.
- API Key inputs with show/hide toggle.
- Primary & Fast model selectors.

- [ ] **Step 9: Commit modular components**
```bash
git add dashboard/src/lib/api.ts dashboard/src/components/
git commit -m "feat(dashboard): create modular 5-tab Glassmorphic component architecture"
```

---

### Task 4: Streamline Dashboard Root Container (`page.tsx`)

**Files:**
- Modify: `dashboard/src/app/page.tsx`
- Modify: `dashboard/src/app/layout.tsx`

- [ ] **Step 1: Refactor `dashboard/src/app/page.tsx`**
Replace the 2,978-line monolithic file with a clean ~200-line root layout:
- State management for `selectedProfileId`, `activeTab`, `profiles`, `systemHealth`, `showSettingsModal`, `showConnectModal`.
- Tab router rendering `OverviewTab`, `GrowthEngineTab`, `LiveActivityTab`, `PersonaMemoryTab`, or `LimitsSchedulerTab`.
- Responsive layout container with `Sidebar` and modal mounts.

- [ ] **Step 2: Verify and build Next.js application**
```bash
cd dashboard && npm run build
```
Verify build exits cleanly with 0 TypeScript/ESLint errors.

- [ ] **Step 3: Commit streamlined page**
```bash
git add dashboard/src/app/page.tsx dashboard/src/app/layout.tsx
git commit -m "refactor(dashboard): streamline page.tsx into clean root container"
```

---

### Task 5: End-to-End Verification & Knowledge Graph Update

**Files:**
- Execute: `backend/.venv/bin/pytest backend/tests/`
- Execute: `graphify update .`

- [ ] **Step 1: Run complete backend test suite**
```bash
backend/.venv/bin/pytest backend/tests/
```
Verify all tests pass.

- [ ] **Step 2: Test backend startup health check**
Verify FastAPI server initializes cleanly and responds on `/health` and `/api/health`.

- [ ] **Step 3: Update knowledge graph with clean architecture**
```bash
python3 -m graphify update .
```

- [ ] **Step 4: Final commit & walkthrough documentation**
```bash
git add -A
git commit -m "chore: complete XBot architectural overhaul, cleanup, and UI modernization"
```
