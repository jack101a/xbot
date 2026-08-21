# Technical Specification: XBot Autonomous AI Persona Platform & UI Modernization

**Date:** 2026-08-21  
**Status:** Approved by User  
**Scope:** Architectural Overhaul & Repository Cleanliness  

---

## 1. Product Identity & Purpose

**XBot** is an enterprise-grade autonomous social media agent platform. It manages multiple autonomous AI personas on X (Twitter), creating organic, high-engagement content through:
1. **Intelligent KOL Sniping:** Identifying high-value posts from niche leaders and generating insightful, contrarian, witty, framework, or data-driven replies.
2. **Viral Hook Optimization:** Scoring and rewriting opening lines across 6 proven psychological archetypes.
3. **Interactive Viral Polls:** Creating native multi-choice polls on trending niche debates to drive viral impressions.
4. **Real-Time Trend Radar:** Ingesting RSS/Atom feeds, scoring relevance to the persona, and generating timely commentary.
5. **Cognitive Persona Memory & Reflection:** Maintaining persistent voice, opinions, long-term memory, daily journals, and performance-driven learning.
6. **Stealth Browser Automation & Sliding-Window Safety:** Playwright-based humanized execution with Redis-backed rate limiting, per-profile proxy support, and anti-fingerprinting.

---

## 2. Feature Inventory: Final Decisions

### Kept & Enhanced Features
- **Multi-Profile Management & Storage:** Profile creation, switching, settings, YAML configs, SQLite/PostgreSQL persistence.
- **Account Auth & Live Sync:** Fast cookie paste (`auth_token`, `ct0`, `twid`), storage state parser, live profile scraping (followers, following, avatar, bio).
- **Growth Engine (KOL Sniper, Hook Optimizer, Poll Generator, Trend Radar):** Standalone tools and autonomous generation pipelines.
- **Cognitive Persona System:** Persona loader, daily diary logs, long-term memory, performance-informed reflection loop.
- **Stealth Browser Automation:** Playwright with Redis distributed locks, anti-detection scripts, humanized typing/scrolling, error screenshot capture.
- **Safety Limiter & Circuit Breaker:** Hourly/daily sliding-window action caps via Redis sorted sets, warm-up multipliers, automatic backoffs.
- **Live Activity Streaming:** Real-time WebSocket event broadcaster and session history viewer with action logs.

### Purged / Removed Features
- **Outreach Campaigns (`CampaignsTab.tsx`, `campaign_manager.py`):** Deprecated mass-messaging/search workflows removed.
- **Social Graph Network Crawler (`AudienceNetworkTab.tsx`, `/social-graph`):** Ban-prone 2nd-degree follower crawling removed.
- **Free Tools Scraper (`tools.py`, `/tools/analytics`, `free-tools` tab):** Dedicated "scraper" profile sandbox removed.
- **Legacy Patch Files:** 16+ temporary Python patch scripts and test `.db` files deleted from root and backend.

---

## 3. System Architecture & Components

```
xbot/
├── backend/
│   ├── xbot/
│   │   ├── ai/               # Cognitive & Generation Pipeline
│   │   │   ├── assembler.py      # Prompt context assembler (persona, memory, history)
│   │   │   ├── client.py         # Multi-model client (LiteLLM, Gemini, Mistral, OpenAI)
│   │   │   ├── sniper.py         # KOL sniper angle & reply generator
│   │   │   ├── hook_optimizer.py # Viral hook scoring across 6 archetypes
│   │   │   ├── poll_generator.py # Poll question & choice generator
│   │   │   ├── trend_radar.py    # RSS/Atom ingestion & relevance evaluator
│   │   │   ├── trend_generator.py# Trend commentary tweet generator
│   │   │   ├── planner.py        # Dynamic growth session planner
│   │   │   ├── reflection.py     # Cognitive reinforcement learning & memory updates
│   │   │   └── sentiment.py      # Toxicity & sentiment validator
│   │   ├── api/              # FastAPI REST Endpoints & WebSockets
│   │   │   ├── profiles.py       # Profiles CRUD, cookies, persona, sync
│   │   │   ├── sessions.py       # Session execution, history, WebSockets
│   │   │   └── system.py         # Health, rate limits, global config, models
│   │   ├── browser/          # Playwright Automation Engine
│   │   │   ├── manager.py        # Lifecycle & Redis distributed locks
│   │   │   ├── auth.py           # Cookie & storage_state hydration
│   │   │   ├── stealth.py        # Anti-fingerprint overrides
│   │   │   ├── timing.py         # Human typing & organic cooldowns
│   │   │   └── actions/          # PostTweet, ReplyTweet, LikeTweet, CreatePoll, SyncProfile, CheckUser
│   │   ├── safety/           # Redis Sliding-Window Rate Limiter & Circuit Breakers
│   │   ├── persona/          # Persona YAML loader, diary, and cognitive memory
│   │   ├── models/           # SQLAlchemy 2.0 Async ORM models
│   │   ├── scheduling/       # Organic jitter-based cron scheduler
│   │   ├── celery_app.py     # Celery app configuration
│   │   └── tasks.py          # Celery background tasks
│   └── tests/                # Comprehensive unit & integration test suite
├── dashboard/                # Next.js 16 / React 19 Clean Glassmorphic UI
│   └── src/
│       ├── app/
│       │   ├── page.tsx          # Clean root container & tab router
│       │   └── layout.tsx        # Glassmorphic shell, fonts, meta
│       ├── components/
│       │   ├── Sidebar.tsx           # Profile selector, nav tabs, system health
│       │   ├── OverviewTab.tsx       # Profile hero, live stats, quick triggers
│       │   ├── GrowthEngineTab.tsx   # KOL Sniper, Hook Optimizer, Polls, Trend Radar
│       │   ├── LiveActivityTab.tsx   # Real-time WebSocket stream & session history
│       │   ├── PersonaMemoryTab.tsx  # Voice, topics, diary, cognitive memory
│       │   ├── LimitsSchedulerTab.tsx# Sliding-window limits, cooldowns, scheduling
│       │   ├── GlobalSettingsModal.tsx# AI providers, API keys, models
│       │   └── ConnectAccountModal.tsx# Cookie import & live profile sync
│       └── lib/
│           └── api.ts            # Central typed client & dynamic WebSocket/HTTP URLs
└── data/profiles/            # Per-profile YAML configurations, diaries, and logs
```

---

## 4. Frontend Modularization (5-Tab Glassmorphic UI)

### Central Tab Breakdown
1. **Overview Tab (`OverviewTab.tsx`)**:
   - Profile avatar, handle, status badge (Active / Paused / Locked).
   - Follower count, following count, last sync timestamp, and "Sync Now" button.
   - Quick Action bar: "Run Autonomous Session Now", "Draft Tweet", "Pause Profile".
   - Recent activity summary and 24h action counts vs limits.

2. **Growth Engine Tab (`GrowthEngineTab.tsx`)**:
   - Sub-tabs:
     - **KOL Sniper:** Manage target KOL handles, priority (High/Med/Low), preferred angles (Witty, Contrarian, Analytical, Framework, Insight), and test live tweet replies.
     - **Hook Optimizer:** Interactive hook sandbox; input draft/topic, generate 6 archetype candidates with virality scores, pick winner.
     - **Poll Generator:** Interactive poll sandbox; input topic, generate question + 2-4 choices (<=25 chars) + duration, stage to queue or post immediately.
     - **Trend Radar:** Feed list, manual refresh, relevance scores, and instant trend tweet drafting.

3. **Live Activity Tab (`LiveActivityTab.tsx`)**:
   - Real-time WebSocket log stream with color-coded event badges (Session Started, Planning, Executing Action, Completed, Cooldown).
   - Expandable Session History cards with individual action breakdown, durations, target URLs, and error logs.
   - Fixed dynamic WebSocket URL (`ws://${window.location.hostname}:8200/api/ws/live`).

4. **Persona & Memory Tab (`PersonaMemoryTab.tsx`)**:
   - Persona Identity: Name, bio, tone description, voice attributes.
   - Topic Boundaries: Core topics, secondary topics, anti-topics (never talk about).
   - Daily Diary Viewer: Historical entries from `diary/YYYY-MM-DD.md`.
   - Cognitive Long-Term Memory: Key beliefs, learned preferences, audience feedback notes.

5. **Limits & Automation Tab (`LimitsSchedulerTab.tsx`)**:
   - Hourly and daily caps for Posts, Replies, Likes, Retweets, Follows.
   - Randomized cooldown sliders (min/max seconds between actions).
   - Active hours schedule (e.g. 08:00 - 22:00 with organic jitter).
   - Warm-up account age multiplier display and circuit breaker status.

---

## 5. Implementation & Migration Steps

1. **Step 1: Clean Up Dead Code & Artifacts**:
   - Remove 16+ leftover patch scripts in root and `backend/`.
   - Remove temporary SQLite test `.db` files.
   - Remove deprecated `CampaignsTab.tsx`, `AudienceNetworkTab.tsx`, `campaign_manager.py`, and free tools endpoints.
2. **Step 2: Backend API & WebSocket Hardening**:
   - Consolidate `/api/profiles`, `/api/sessions`, `/api/system` routes.
   - Ensure WebSocket connections use clean `/api/ws/live` and `/api/ws/sessions/{id}` endpoints.
   - Implement tweet performance metrics ingestion in reflection task.
3. **Step 3: Dashboard Modular Decomposition**:
   - Split `page.tsx` (2,978 lines) into clean modular components in `dashboard/src/components/`.
   - Update `api.ts` to derive dynamic HTTP and WebSocket URLs correctly.
   - Rebuild UI with modern glassmorphic styling, responsive layouts, and proper dark/light theme support.
4. **Step 4: End-to-End Verification**:
   - Run unit test suite (79+ tests).
   - Test Next.js build (`npm run build`).
   - Validate live API endpoints and WebSocket event streams.
