# 24/7 Autonomous Growth Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete 24/7 Autonomous Organic Growth Engine for XBot Pro, implementing the Opportunity Radar, JIT 5-10 comment thread scraping, 4 sniper conversion archetypes, anti-hallucination topic guardrails, circadian episodic scheduling, and 1-click human approval workflows.

**Architecture:** A multi-stage pipeline combining an asynchronous Opportunity Radar (KOL & Trend scanning), JIT Playwright thread perception, LiteLLM synthesis with strict Voice vs. Topic decoupling, Redis sliding-window rate limiters, and an episodic circadian session scheduler.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy (Async), Redis Sorted Sets, LiteLLM, Playwright Stealth, Next.js 14, Tailwind CSS.

---

## Global Constraints

- Never post mundane diary filler or repetitive beverage cliches (chai, coffee, lukewarm tea, terrace vibes, peace is underrated).
- Persona governs strictly Voice/Tone/Slang; the Live Thread/Trend governs 100% of the Topic.
- Standard replies are text-only by default (80%); GIFs are attached only for punchline/shock value.
- Standalone posts and polls must be staged as `draft` items when `require_post_approval: true` is enabled.
- All core tests in `backend/tests/` must pass with 100% pass rate.

---

### Task 1: Opportunity Radar & Arbitrage Scorer

**Files:**
- Create: `backend/xbot/ai/opportunity_radar.py`
- Modify: `backend/xbot/ai/trend_radar.py`
- Test: `backend/tests/test_opportunity_radar.py`

**Interfaces:**
- Consumes: Target KOL handles from `Persona.target_kols`, RSS feeds from `TrendRadar`.
- Produces: `CandidateOpportunity` list with computed Arbitrage Score $S \ge 65.0$.

- [ ] **Step 1: Write the failing unit tests in `backend/tests/test_opportunity_radar.py`**
- [ ] **Step 2: Implement `OpportunityRadar` with Arbitrage Scoring formula ($V, R, A, C$)**
- [ ] **Step 3: Run pytest on `test_opportunity_radar.py` and verify 100% pass**
- [ ] **Step 4: Commit changes**

---

### Task 2: Sniper 4-Archetype Engine & JIT Thread Perception

**Files:**
- Modify: `backend/xbot/ai/sniper.py`
- Modify: `backend/xbot/browser/actions/x_actions.py`
- Test: `backend/tests/test_ai_sniper.py`

**Interfaces:**
- Consumes: Scraped tweet context + top 5-10 comments from `x_actions.py:ReplyToTweet`.
- Produces: `SniperReplyGeneration` adhering to 4 archetypes (Contrarian, Framework, Question, Witty) and passing the 5-Stage Verification Gatekeeper.

- [ ] **Step 1: Update `backend/tests/test_ai_sniper.py` with tests for the 4 archetypes and anti-slop filters**
- [ ] **Step 2: Implement archetype routing and 5-stage deterministic validation in `backend/xbot/ai/sniper.py`**
- [ ] **Step 3: Update `ReplyToTweet` in `backend/xbot/browser/actions/x_actions.py` with smooth-scroll comment extractor**
- [ ] **Step 4: Run pytest on `test_ai_sniper.py` and verify all tests pass**
- [ ] **Step 5: Commit changes**

---

### Task 3: Episodic Circadian Scheduler & Safety Sliding-Window Limiter

**Files:**
- Create: `backend/xbot/scheduler/circadian.py`
- Modify: `backend/xbot/safety/limiter.py`
- Modify: `backend/xbot/tasks.py`
- Test: `backend/tests/test_circadian_scheduler.py`

**Interfaces:**
- Consumes: Profile timezone and active hours (`08:00 - 23:00`).
- Produces: Randomized session slots ($D \sim \mathcal{U}(15, 45)\,\text{min}$) with 10% natural skips and atomic Redis sliding windows.

- [ ] **Step 1: Write failing tests in `backend/tests/test_circadian_scheduler.py`**
- [ ] **Step 2: Implement `CircadianScheduler` in `backend/xbot/scheduler/circadian.py`**
- [ ] **Step 3: Integrate circadian loop into `backend/xbot/tasks.py`**
- [ ] **Step 4: Run pytest on `test_circadian_scheduler.py` and `test_rate_limiter.py`**
- [ ] **Step 5: Commit changes**

---

### Task 4: Human-in-the-Loop Staging & 1-Click Action Verification

**Files:**
- Modify: `backend/xbot/api/profiles.py`
- Modify: `backend/xbot/tasks.py`
- Modify: `dashboard/src/components/OverviewTab.tsx`
- Test: `backend/tests/test_draft_staging.py`

**Interfaces:**
- Consumes: Staged drafts from `GET /api/profiles/{id}/drafts`.
- Produces: 1-click execution via `POST /api/profiles/{id}/drafts/{id}/approve` and dismissal via `DELETE /api/profiles/{id}/drafts/{id}`.

- [ ] **Step 1: Write integration tests in `backend/tests/test_draft_staging.py`**
- [ ] **Step 2: Validate approval and dismissal endpoints in `backend/xbot/api/profiles.py`**
- [ ] **Step 3: Rebuild dashboard static assets (`npm run build`)**
- [ ] **Step 4: Run pytest across the entire test suite**
- [ ] **Step 5: Commit changes**

---

### Task 5: End-to-End Autonomous Simulation & Live Verification

**Files:**
- Create: `test-script/verify_24_7_growth_engine.py`

- [ ] **Step 1: Run comprehensive end-to-end verification script testing radar, sniper generation, draft staging, and circadian planner**
- [ ] **Step 2: Verify zero chai/coffee regressions and 100% topic adherence**
- [ ] **Step 3: Restart live backend and frontend services**
- [ ] **Step 4: Commit and finalize walkthrough report**
