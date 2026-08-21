# Graph Report - xbot  (2026-08-18)

## Corpus Check
- 173 files · ~120,362 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1804 nodes · 3989 edges · 152 communities (138 shown, 14 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 423 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3a512d3f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- x_actions.py
- Profile
- config.py
- tasks.py
- Cookies
- devDependencies
- loader.py
- page.tsx
- test_hook_optimizer.py
- test_trend_generator.py
- test_profile_auth.py
- compilerOptions
- CheckUserLatestTweet
- optimize_post_hook
- models/profile.py
- test_sniper_task.py
- Browser Automation with playwright-cli
- get_ai_client
- get_all_rate_limits
- Browser Session Management
- ScrapeProfileTweets
- .assemble
- Persona
- generate_ai_content
- DiaryManager
- MemoryManager
- 2026-06-18: Initial Architecture Mapping
- ThreadedUvicorn
- Session
- Running Custom Playwright Code
- 3. Heal
- Tracing
- engagement.py
- 3. Detailed Component Specifications
- SKILL.md
- XBot: Multi-Profile Autonomous Agent Automation System
- 3. Component Specifications
- Phase Breakdown
- sleep_with_jitter
- Video Recording
- Tasks: XBot
- test_trend_task.py
- ai/__init__.py
- Advanced Mocking with run-code
- Global Constraints
- XBot — Master Implementation Plan
- 4. Browser Automation Engine
- 6. Profile Persona & Diary System
- 16. Development Phases & Backlog
- 5. AI Decision System
- 9. Rate Limits & Safety
- 10. Analytics & Strategy Engine
- Task 1 Report: Extend Persona Model and Schema with Target KOLs
- test_profile_auth_api.py
- human_click
- stealth.py
- 12. Docker & Portainer Deployment
- 7. Database Design
- 8. Scheduling & Orchestration
- Task 2 Report: Implement CheckUserLatestTweet Playwright Browser Action
- dashboard/README.md
- layout.tsx
- 11. Admin Dashboard
- 13. Security & Secrets
- 15. Testing Strategy
- 1. Product Vision & Workflow
- 2. System Architecture
- 3. Technology Stack
- SDD ledger — plan: docs/superpowers/plans/2026-08-18-kol-sniper-reply-plan.md
- Memory Log - June 29, 2026
- Memory Log - June 30, 2026
- rules/graphify.md
- workflows/graphify.md
- backup.sh
- AGENTS.md
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- xbot
- Design Specification: Viral Hook Optimizer & Native X Poll Generator
- Global Constraints
- Task 3 Report: Build AI Sniper Angle & Response Generator
- Task 4 Report: Integrate Celery Periodic Task sniper_check_targets with Redis Deduplication & Safety
- Profile Authentication, Live Status & Metrics Sync Implementation Plan
- test_poll_integration.py
- SDD ledger — plan: docs/superpowers/plans/2026-08-18-profile-auth-and-metrics-sync-plan.md
- SDD ledger — plan: docs/superpowers/plans/2026-08-18-viral-hook-and-poll-plan.md
- fetch_rss_trends
- ProfileStatus
- CreatePoll
- inspect_profile_auth_status
- Design Specification: Real-Time Trend Radar & Breaking News Takes
- Task 4 Completion Report: Viral Hook & Native X Poll Pipeline Integration
- SyncProfileFromX
- do_run_migrations
- test_sniper_check_targets_executes_reply_and_records_db
- Task 1 Report: Viral Hook Multi-Generator & Evaluator
- test_poll_generator.py
- post_session.py
- Global Constraints
- Attaching to a Running Browser
- Task 2 Report: AI Poll Generator Implementation
- Task 3 Report: CreatePoll Playwright Browser Action
- SlidingWindowLimiter
- .is_action_safe
- 0. How generation works
- SDD ledger — plan: docs/superpowers/plans/2026-08-18-trend-radar-plan.md
- Any
- load_persona
- 2. Generate
- system.py
- Task 1 Report: Real-Time Trend Radar Ingestion Engine
- Task 2 Report: Trend Relevance Filter & Breaking Take Generator
- Task 3 Report: Integrate Celery Periodic Task `check_trend_radar` & Content Staging
- Completions
- Task 1 Report: Cookie Converter & Auth State Engine
- Task 2 Implementation Report: SyncProfileFromX Playwright Browser Action
- websocket_live_global_logs
- health_check
- ScrapeProfileMetrics
- .capture_failure
- persona/__init__.py
- _extract_tweet_id_from_url

## God Nodes (most connected - your core abstractions)
1. `Profile` - 116 edges
2. `Persona` - 71 edges
3. `ProfileStatus` - 52 edges
4. `_run_session_async()` - 36 edges
5. `load_persona()` - 33 edges
6. `get_ai_client()` - 32 edges
7. `TrendItem` - 32 edges
8. `sleep_with_jitter()` - 32 edges
9. `Base` - 28 edges
10. `BrowserManager` - 27 edges

## Surprising Connections (you probably didn't know these)
- `run_e2e_test()` --uses--> `ContentGenerator`  [INFERRED]
  test-script/test_ai_ghostwriter.py → backend/xbot/ai/generator.py
- `verify_profile_and_kol_setup()` --uses--> `ProfileStatus`  [INFERRED]
  test-script/e2e_full_user_experience.py → backend/xbot/models/profile.py
- `run_e2e_test()` --uses--> `ProfileStatus`  [INFERRED]
  test-script/e2e_session_test.py → backend/xbot/models/profile.py
- `verify_api_and_db_integration()` --uses--> `Profile`  [INFERRED]
  test-script/e2e_full_user_experience.py → backend/xbot/models/profile.py
- `verify_kol_sniper_flow()` --uses--> `Profile`  [INFERRED]
  test-script/e2e_full_user_experience.py → backend/xbot/models/profile.py

## Import Cycles
- None detected.

## Communities (152 total, 14 thin omitted)

### Community 0 - "x_actions.py"
Cohesion: 0.11
Nodes (30): asyncio, Path, Executes and validates the complete library of browser actions against the…, test_x_actions_integration(), BaseAction, Base action class providing failure recovery, logging, and screenshot tools., Browser action for checking a user's profile and extracting their latest tweet., Browser action for synchronizing X profile data and verifying session… (+22 more)

### Community 1 - "Profile"
Cohesion: 0.05
Nodes (106): create_campaign(), create_profile(), delete_campaign(), delete_profile(), get_campaigns(), get_follower_changelogs(), get_follower_snapshots(), get_profile() (+98 more)

### Community 2 - "config.py"
Cohesion: 0.12
Nodes (24): clean_redis(), db_session(), asyncio, AsyncSession, fixture, setup_db(), test_generate_daily_schedule(), test_safety_guard_failures_and_signal() (+16 more)

### Community 3 - "tasks.py"
Cohesion: 0.05
Nodes (60): asyncio, Verifies BrowserManager startup, Redis-based locking, context creation, and…, test_browser_manager_flow(), Replies to a tweet. Uses tweet_url when available (from AI planner). Falls back…, ReplyToTweet, BrowserManager, Releases the execution lock for a profile., Manages Playwright browser automation contexts and anti-detection settings.… (+52 more)

### Community 4 - "Cookies"
Cohesion: 0.06
Nodes (35): Advanced: Multiple Cookies or Custom Options, Advanced: Multiple Operations, Authentication State Reuse, Clear All Cookies, Clear All localStorage, Clear sessionStorage, Common Patterns, Cookies (+27 more)

### Community 5 - "devDependencies"
Cohesion: 0.06
Nodes (34): dependencies, lucide-react, next, react, react-dom, devDependencies, eslint, eslint-config-next (+26 more)

### Community 6 - "loader.py"
Cohesion: 0.16
Nodes (24): test_yaml_loader_and_saver(), AsyncSession, BaseModel, datetime, Implements Phase 2.6 Weekly Strategy Review Logic. Queries database performance…, Runs the weekly strategic analysis and updates strategy.yaml., StrategyResponse, StrategyReviewer (+16 more)

### Community 7 - "page.tsx"
Cohesion: 0.06
Nodes (36): API_PROVIDERS, CONTEXT_OPTIONS, Dashboard(), getAvatarUrl(), JobModelSelector(), AudienceNetworkTab(), Changelog, GraphLink (+28 more)

### Community 8 - "test_hook_optimizer.py"
Cohesion: 0.10
Nodes (25): asyncio, Tests cleaning archetype prefixes and long strings., Tests body preservation and micro-spacing in format_optimized_post., Tests format_optimized_post with a single line draft., Tests successful structured parse with 4 archetypes and winning hook selection., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests JSON parsing when returned as a dict keyed by archetype name., Tests that LLM network or API exceptions return original content safely. (+17 more)

### Community 9 - "test_trend_generator.py"
Cohesion: 0.09
Nodes (48): irrelevant_trend_item(), asyncio, fixture, Tests Pydantic validation and field constraints on TrendEvaluation., Tests removing markdown code fences from LLM responses., Tests parsing trend evaluation from various JSON formats., Tests successful structured parse and hook optimization on relevant trend item., Tests that irrelevant news items return is_relevant=False and do NOT call hook… (+40 more)

### Community 10 - "test_profile_auth.py"
Cohesion: 0.11
Nodes (24): Test parsing raw JSON object format., Test parsing full Playwright storage_state JSON string., Test parsing multiline newline-separated cookie string., Test format_storage_state generates standard Playwright storage state structure., Test empty, whitespace, and malformed inputs., Test inspect_profile_auth_status with valid active storage_state.json., Test format_storage_state includes twid when provided., Test parsing standard HTTP Cookie header string. (+16 more)

### Community 11 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 12 - "CheckUserLatestTweet"
Cohesion: 0.13
Nodes (22): asyncio, Path, Tests fallback to second tweet when the first tweet is pinned., Tests extracting the pinned tweet when no second tweet is available., Tests returning None when profile has no tweets., Tests returning None and capturing failure screenshot on navigation error., Tests extracting standard latest tweet from profile., test_check_user_latest_tweet_empty_profile() (+14 more)

### Community 13 - "optimize_post_hook"
Cohesion: 0.19
Nodes (18): _build_hook_optimizer_system_prompt(), _build_hook_optimizer_user_prompt(), clean_text_for_json(), _get_persona_field(), HookCandidate, _HookGenerationResponse, _normalize_candidate(), optimize_post_hook() (+10 more)

### Community 14 - "models/profile.py"
Cohesion: 0.13
Nodes (32): Run migrations in 'offline' mode., run_migrations_offline(), db_session(), asyncio, AsyncSession, fixture, Path, Creates and teardowns the test database structure. (+24 more)

### Community 15 - "test_sniper_task.py"
Cohesion: 0.21
Nodes (27): fixture, sample_persona(), sample_tweet(), fixture, sample_persona(), fixture, sample_persona(), sample_persona() (+19 more)

### Community 16 - "Browser Automation with playwright-cli"
Cohesion: 0.08
Nodes (24): Browser Automation with playwright-cli, Browser Sessions, Commands, Core, DevTools, Example: Debugging with DevTools, Example: Form submission, Example: Interactive session (+16 more)

### Community 17 - "get_ai_client"
Cohesion: 0.15
Nodes (10): Beta, BetaChat, Chat, get_ai_client(), A smart facade for AsyncOpenAI that dynamically routes requests to the correct…, RoutingClient, analyze_sentiment_llm(), analyze_sentiment_rules() (+2 more)

### Community 18 - "get_all_rate_limits"
Cohesion: 0.11
Nodes (21): get_all_rate_limits(), get_system_config(), get_system_health(), get_system_models(), pause_entire_system(), Any, AsyncSession, BaseModel (+13 more)

### Community 19 - "Browser Session Management"
Cohesion: 0.13
Nodes (15): 1. Name Browser Sessions Semantically, 2. Always Clean Up, 3. Delete Stale Browser Data, A/B Testing Sessions, Best Practices, Browser Session Commands, Browser Session Configuration, Browser Session Isolation Properties (+7 more)

### Community 20 - "ScrapeProfileTweets"
Cohesion: 0.24
Nodes (8): AnalyticsRequest, get_free_analytics(), Any, BaseModel, post, On-demand free analytics scraper that mirrors tools like…, Scrapes recent tweets of a profile to calculate engagement metrics., ScrapeProfileTweets

### Community 21 - ".assemble"
Cohesion: 0.14
Nodes (11): AssembledContext, AsyncSession, BaseModel, datetime, Helper to dump Strategy model to YAML string., Gathers files and database records to construct an AssembledContext for the…, Helper to format the Persona object into a markdown character sheet., Renders the user prompt context following the structure defined in… (+3 more)

### Community 22 - "Persona"
Cohesion: 0.13
Nodes (33): asyncio, Tests fallback to chat.completions.create with JSON parsing when structured…, Tests fallback when response is plain unformatted text (not JSON)., Tests that various angles (witty, data, contrarian, framework, insight) are…, Tests that when preferred_angle is None, prompt instructs auto-selection among…, Tests that complete LLM failure returns a safe fallback SniperReplyResult…, Tests that when client is None, get_ai_client() is invoked., Tests that excessively long replies (> 280 chars) are trimmed to 280 chars. (+25 more)

### Community 23 - "generate_ai_content"
Cohesion: 0.18
Nodes (17): generate_ai_content(), GenerateContentRequest, get_content_detail(), list_profile_content(), Any, AsyncSession, BaseModel, get (+9 more)

### Community 24 - "DiaryManager"
Cohesion: 0.16
Nodes (9): Path, test_diary_manager(), test_memory_manager(), test_persona_with_target_kols(), DiaryManager, Path, Manages daily diary entries ("inner monologue") for personas. Stores logs in…, Appends a structured session entry to the daily diary markdown file. Auto-… (+1 more)

### Community 25 - "MemoryManager"
Cohesion: 0.17
Nodes (10): MemoryManager, Any, Path, Appends a persistent high-importance memory., Retrieves a compiled list of memories based on recency, importance, and query.…, Manages episodic, semantic, and high-importance memories for a persona. Saves…, Appends a single JSON record to the specified file., Reads all JSON records from a JSONL file. (+2 more)

### Community 26 - "2026-06-18: Initial Architecture Mapping"
Cohesion: 0.12
Nodes (15): 2026-06-18: Initial Architecture Mapping, DEC-001: Backend Framework Choice, DEC-002: Project Init using `uv`, DEC-003: Strict Linting and Type Checking Configuration, DEC-004: Rename Virtual Environment to `.venv`, DEC-005: Switch Database from PostgreSQL to SQLite, DEC-006: Utilize Host Native Redis and External LiteLLM, DEC-007: Enable Modern Python Deferred Type Annotations in Database Models (+7 more)

### Community 27 - "ThreadedUvicorn"
Cohesion: 0.18
Nodes (9): home_feed(), profile_page(), get, Runs the mock FastAPI application inside a background thread., search_results(), ThreadedUvicorn, mock_x_server(), fixture (+1 more)

### Community 28 - "Session"
Cohesion: 0.27
Nodes (14): get_session_actions(), get_session_detail(), list_profile_sessions(), Any, AsyncSession, get, post, UUID (+6 more)

### Community 29 - "Running Custom Playwright Code"
Cohesion: 0.15
Nodes (13): Clipboard, Complex Workflows, Error Handling, File Downloads, Frames and Iframes, Geolocation, JavaScript Execution, Media Emulation (+5 more)

### Community 30 - "3. Heal"
Cohesion: 0.15
Nodes (13): 1.1 Prerequisite: workspace, 1.2 Prerequisite: seed test, 1.3 Explore the app, 1.4 Write the spec file, 1. Planning, 3.1 Find failing tests, 3.2 Debug one failure, 3.3 Apply the fix (+5 more)

### Community 31 - "Tracing"
Cohesion: 0.12
Nodes (16): 1. Start Tracing Before the Problem, 2. Clean Up Old Traces, Analyzing Performance, Basic Usage, Best Practices, Capturing Evidence, Debugging Failed Actions, Limitations (+8 more)

### Community 32 - "engagement.py"
Cohesion: 0.14
Nodes (16): EngagementDecision, EngagementEvaluator, EngagementResponse, FollowDecision, FollowEvaluator, FollowResponse, Any, AsyncSession (+8 more)

### Community 33 - "3. Detailed Component Specifications"
Cohesion: 0.17
Nodes (11): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Persona Configuration Extension (`persona.yaml` / `loader.py`), 3.2 Browser Extraction Action (`xbot/browser/actions/x_actions.py`), 3.3 Sniper Angle & Response Engine (`xbot/ai/sniper.py`), 3.4 Rate Limiting & Safety Integration (`xbot/safety/limiter.py`), 3.5 Periodic Task Runner (`xbot/tasks.py`), 3. Detailed Component Specifications (+3 more)

### Community 34 - "SKILL.md"
Cohesion: 0.24
Nodes (4): Examples, Inspecting Element Attributes, Debugging Playwright Tests, Running Playwright Tests

### Community 35 - "XBot: Multi-Profile Autonomous Agent Automation System"
Cohesion: 0.18
Nodes (10): 1. Initialize the Environment, 2. Startup Backend Service (FastAPI), 3. Launch Celery Worker & Beat Scheduler, 4. Launch Next.js Dashboard UI, 🛠 Project Structure, 🚀 Quick Start & Launch Runbook, 🧪 Running Tests, 🛡 Safety Guard & Webhook Alerting (+2 more)

### Community 36 - "3. Component Specifications"
Cohesion: 0.20
Nodes (9): 1. Executive Summary, 2. Architecture & Data Flow, 3.1 Backend Cookie Converter & Session Health (`xbot/browser/auth.py`), 3.2 Probe & Metrics Scraper Action (`xbot/browser/actions/sync_profile_action.py`), 3.3 REST Endpoints (`backend/xbot/api/profiles.py`), 3.4 Dashboard UI Components (`dashboard/src/app/page.tsx` & `dashboard/src/components/ConnectAccountModal.tsx`), 3. Component Specifications, 4. Verification & Testing (+1 more)

### Community 37 - "Phase Breakdown"
Cohesion: 0.20
Nodes (9): Overall Status, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening, Phase Breakdown (+1 more)

### Community 38 - "sleep_with_jitter"
Cohesion: 0.20
Nodes (16): human_scroll_to_tweet(), _navigate_home_if_needed(), _post_action_cooldown_browse(), Any, Page, _random_tab_detour(), Scroll a tweet into view and add a read pause., Navigate to the X home feed if not already there. (+8 more)

### Community 39 - "Video Recording"
Cohesion: 0.22
Nodes (8): 1. Use Descriptive Filenames, 2. Record entire hero scripts., Basic Recording, Best Practices, Limitations, Overlay API Summary, Tracing vs Video, Video Recording

### Community 40 - "Tasks: XBot"
Cohesion: 0.22
Nodes (8): Active Task, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening, Tasks: XBot

### Community 41 - "test_trend_task.py"
Cohesion: 0.14
Nodes (22): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Verifies that the periodic schedule for check_trend_radar is registered in…, Tests active profile fetches trends, evaluates relevance, stages Content…, Tests that previously seen trend items are skipped and not re-evaluated. (+14 more)

### Community 42 - "ai/__init__.py"
Cohesion: 0.12
Nodes (19): Verifies generate_tweet passes draft_tweet through optimize_post_hook and…, Verifies generate_tweet creates a draft tweet from LLM then runs hook…, test_content_generator_generate_tweet_with_existing_draft(), test_content_generator_generate_tweet_without_draft_generates_and_optimizes(), calculate_similarity(), clean_text_for_json(), ContentGenerationResponse, ContentGenerator (+11 more)

### Community 43 - "Advanced Mocking with run-code"
Cohesion: 0.25
Nodes (8): Advanced Mocking with run-code, CLI Route Commands, Conditional Response Based on Request, Delayed Response, Modify Real Response, Request Mocking, Simulate Network Failures, URL Patterns

### Community 44 - "Global Constraints"
Cohesion: 0.25
Nodes (7): Global Constraints, KOL Sniper Reply & Fast Engagement Subsystem Implementation Plan, Plan Verification & Self-Review Checklist, Task 1: Extend Persona Model and Schema with Target KOLs, Task 2: Implement `CheckUserLatestTweet` Playwright Browser Action, Task 3: Build AI Sniper Angle & Response Generator, Task 4: Integrate Celery Periodic Task `sniper_check_targets` with Redis Deduplication & Safety

### Community 45 - "XBot — Master Implementation Plan"
Cohesion: 0.25
Nodes (7): 14.1 Logging Architecture, 14.2 Log Categories & Levels, 14.3 Monitoring & Alerting, 14. Logging & Observability, Appendix: Target Project Structure, Table of Contents, XBot — Master Implementation Plan

### Community 46 - "4. Browser Automation Engine"
Cohesion: 0.25
Nodes (8): 4.1 Design Principles, 4.2 Browser Manager, 4.3 Stealth Configuration, 4.4 Action Library, 4.5 Timing Engine, 4.6 Error Handling & Recovery, 4.7 Session Lifecycle, 4. Browser Automation Engine

### Community 47 - "6. Profile Persona & Diary System"
Cohesion: 0.25
Nodes (8): 6.1 File Structure Per Profile, 6.2 Persona Definition Schema (`persona.yaml`), 6.3 Diary System, 6.4 Memory System, 6.5 Memory Retrieval Strategy, 6.6 Relationship Tracking (`known_accounts.yaml`), 6.7 Strategy Document (`strategy.yaml`), 6. Profile Persona & Diary System

### Community 48 - "16. Development Phases & Backlog"
Cohesion: 0.29
Nodes (7): 16.1 Phase 0: Foundation (Week 1-2), 16.2 Phase 1: Browser Engine + Persona (Week 3-5), 16.3 Phase 2: AI Brain (Week 6-8), 16.4 Phase 3: Scheduling & Safety (Week 9-10), 16.5 Phase 4: Analytics & Dashboard (Week 11-14), 16.6 Phase 5: Polish & Hardening (Week 15-16), 16. Development Phases & Backlog

### Community 49 - "5. AI Decision System"
Cohesion: 0.29
Nodes (7): 5.1 LiteLLM Integration, 5.2 AI Call Types, 5.3 Session Planning Prompt Structure, 5.4 Response Schema (Structured Output), 5.5 Content Generation Pipeline, 5.6 Engagement Decision Flow, 5. AI Decision System

### Community 50 - "9. Rate Limits & Safety"
Cohesion: 0.29
Nodes (7): 9.1 Three-Tier Rate Limit Architecture, 9.2 Hard Limits (Defaults — Established Accounts), 9.3 Soft Limits (Per-Profile Budget), 9.4 Redis Implementation, 9.5 Account Safety Measures, 9.6 Health Signal Detection, 9. Rate Limits & Safety

### Community 51 - "10. Analytics & Strategy Engine"
Cohesion: 0.33
Nodes (6): 10.1 Data Collection, 10.2 Analytics Snapshot Process, 10.3 Performance Scoring, 10.4 Strategy Engine (Weekly Review), 10.5 Monetization Tracking, 10. Analytics & Strategy Engine

### Community 52 - "Task 1 Report: Extend Persona Model and Schema with Target KOLs"
Cohesion: 0.33
Nodes (5): Changes Made, Git Commit, Overview, Task 1 Report: Extend Persona Model and Schema with Target KOLs, Test Verification

### Community 53 - "test_profile_auth_api.py"
Cohesion: 0.17
Nodes (18): configure_db_override(), create_tables(), create_test_profile(), drop_tables(), override_get_db(), AsyncSession, fixture, Path (+10 more)

### Community 54 - "human_click"
Cohesion: 0.16
Nodes (19): Page, Executes poll creation on X: 1. Opens compose modal or navigates to…, _bezier_curve_points(), human_click(), human_click_selector(), human_mouse_move(), human_scroll_to_element(), human_type() (+11 more)

### Community 55 - "stealth.py"
Cohesion: 0.15
Nodes (12): BrowserContext, Creates or retrieves a persistent browser context for the profile. Picks a…, Starts the Playwright driver., apply_stealth(), apply_stealth_to_context(), _build_stealth_script(), BrowserContext, Page (+4 more)

### Community 56 - "12. Docker & Portainer Deployment"
Cohesion: 0.40
Nodes (5): 12.1 Docker Compose, 12.2 Dockerfile Strategy, 12.3 Portainer Setup, 12.4 Volume Strategy, 12. Docker & Portainer Deployment

### Community 57 - "7. Database Design"
Cohesion: 0.40
Nodes (5): 7.1 Entity-Relationship Overview, 7.2 Table Definitions, 7.3 Key Indexes, 7.4 Migration Strategy, 7. Database Design

### Community 58 - "8. Scheduling & Orchestration"
Cohesion: 0.40
Nodes (5): 8.1 Schedule Architecture, 8.2 Profile Schedule Configuration, 8.3 Natural Schedule Algorithm, 8.4 Task Types, 8. Scheduling & Orchestration

### Community 59 - "Task 2 Report: Implement CheckUserLatestTweet Playwright Browser Action"
Cohesion: 0.33
Nodes (5): Changes Made, Git Commit, Overview, Task 2 Report: Implement CheckUserLatestTweet Playwright Browser Action, Test Verification

### Community 60 - "dashboard/README.md"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

### Community 62 - "11. Admin Dashboard"
Cohesion: 0.50
Nodes (4): 11.1 Dashboard Pages, 11.2 Key Features, 11.3 API Endpoints (FastAPI), 11. Admin Dashboard

### Community 63 - "13. Security & Secrets"
Cohesion: 0.50
Nodes (4): 13.1 Secret Management, 13.2 Credential Encryption, 13.3 Network Security, 13. Security & Secrets

### Community 64 - "15. Testing Strategy"
Cohesion: 0.50
Nodes (4): 15.1 The Testing Pyramid, 15.2 Test Categories & Tools, 15.3 Mock X Server, 15. Testing Strategy

### Community 65 - "1. Product Vision & Workflow"
Cohesion: 0.50
Nodes (4): 1.1 What the System Does, 1.2 Core Product Loop, 1.3 Monetization Path, 1. Product Vision & Workflow

### Community 66 - "2. System Architecture"
Cohesion: 0.50
Nodes (4): 2.1 High-Level Architecture, 2.2 Service Responsibilities, 2.3 Key Architecture Decisions, 2. System Architecture

### Community 67 - "3. Technology Stack"
Cohesion: 0.50
Nodes (4): 3.1 Backend, 3.2 Frontend (Dashboard), 3.3 Infrastructure, 3. Technology Stack

### Community 68 - "SDD ledger — plan: docs/superpowers/plans/2026-08-18-kol-sniper-reply-plan.md"
Cohesion: 0.40
Nodes (4): Pre-flight Conflict Scan, SDD ledger — plan: docs/superpowers/plans/2026-08-18-kol-sniper-reply-plan.md, Task Status, Verification Status

### Community 107 - "Design Specification: Viral Hook Optimizer & Native X Poll Generator"
Cohesion: 0.20
Nodes (9): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Hook Optimization Engine (`xbot/ai/hook_optimizer.py`), 3.2 Poll Generation Engine (`xbot/ai/poll_generator.py`), 3.3 Native X Poll Browser Action (`xbot/browser/actions/poll_action.py`), 3. Detailed Component Specifications, 4. Integration into Session Planner & Content Pipeline, 5. Testing & Verification (+1 more)

### Community 108 - "Global Constraints"
Cohesion: 0.29
Nodes (6): Global Constraints, Task 1: Build the Viral Hook Optimizer & Scorer, Task 2: Build the AI Poll Generator, Task 3: Implement `CreatePoll` Playwright Browser Action, Task 4: Integrate Hook Optimization & Polls into Content Pipeline & Tasks, Viral Hook Optimizer & Native X Poll Subsystem Implementation Plan

### Community 109 - "Task 3 Report: Build AI Sniper Angle & Response Generator"
Cohesion: 0.33
Nodes (5): Changes Made, Git Commit, Overview, Task 3 Report: Build AI Sniper Angle & Response Generator, Test Verification

### Community 110 - "Task 4 Report: Integrate Celery Periodic Task sniper_check_targets with Redis Deduplication & Safety"
Cohesion: 0.33
Nodes (5): Changes Made, Git Commit, Overview, Task 4 Report: Integrate Celery Periodic Task sniper_check_targets with Redis Deduplication & Safety, Test Verification

### Community 111 - "Profile Authentication, Live Status & Metrics Sync Implementation Plan"
Cohesion: 0.33
Nodes (5): Profile Authentication, Live Status & Metrics Sync Implementation Plan, Task 1: Build Cookie Converter & Auth State Engine, Task 2: Implement `SyncProfileFromX` Playwright Browser Action, Task 3: Expose REST Endpoints for Auth Status, Cookie Import & Metrics Sync, Task 4: Build Dashboard UI (Connect Modal, Live Avatar & Real-time Metrics)

### Community 112 - "test_poll_integration.py"
Cohesion: 0.14
Nodes (29): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Verifies that ActionType and ContentType include POLL enum members., Verifies that _run_session_async executes ActionType.POLL in mock mode and…, Verifies that _run_session_async in live mode executes CreatePoll browser… (+21 more)

### Community 113 - "SDD ledger — plan: docs/superpowers/plans/2026-08-18-profile-auth-and-metrics-sync-plan.md"
Cohesion: 0.50
Nodes (3): Pre-flight Conflict Scan, SDD ledger — plan: docs/superpowers/plans/2026-08-18-profile-auth-and-metrics-sync-plan.md, Task Status

### Community 114 - "SDD ledger — plan: docs/superpowers/plans/2026-08-18-viral-hook-and-poll-plan.md"
Cohesion: 0.40
Nodes (4): Pre-flight Conflict Scan, SDD ledger — plan: docs/superpowers/plans/2026-08-18-viral-hook-and-poll-plan.md, Task Status, Verification Status

### Community 115 - "fetch_rss_trends"
Cohesion: 0.19
Nodes (24): asyncio, test_fetch_atom_1_0_parsing(), test_fetch_rss_2_0_parsing(), test_fetch_rss_trends_default_client(), test_http_status_error_resilience(), test_keyword_filtering(), test_malformed_xml_resilience(), test_max_items_per_feed() (+16 more)

### Community 116 - "ProfileStatus"
Cohesion: 0.26
Nodes (17): db_session(), populate_profile_files(), asyncio, AsyncSession, fixture, Path, setup_db(), test_content_generator_with_retries() (+9 more)

### Community 117 - "CreatePoll"
Cohesion: 0.26
Nodes (14): asyncio, Path, Tests creating a standard 2-option poll., Tests creating a 4-option poll with multiple extra choices added., Tests creating a 3-option poll with 1 extra choice., Tests navigating to compose post URL if textarea is not already on page., Tests that execution errors gracefully return False and capture failure…, test_create_poll_2_options_success() (+6 more)

### Community 118 - "inspect_profile_auth_status"
Cohesion: 0.19
Nodes (13): Path, Test inspect_profile_auth_status when storage_state.json does not exist., Test inspect_profile_auth_status with only auth_token present., Test inspect_profile_auth_status with expired cookies., Test inspect_profile_auth_status when storage_state.json is malformed., test_inspect_profile_auth_status_corrupt_file(), test_inspect_profile_auth_status_expired(), test_inspect_profile_auth_status_missing() (+5 more)

### Community 119 - "Design Specification: Real-Time Trend Radar & Breaking News Takes"
Cohesion: 0.22
Nodes (8): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Feed & Trend Ingestion Layer (`xbot/ai/trend_radar.py`), 3.2 Relevance Filter & Take Synthesizer (`xbot/ai/trend_generator.py`), 3.3 Celery Periodic Task & Queue Routing (`xbot/tasks.py`), 3. Detailed Component Specifications, 4. Verification & Testing, Design Specification: Real-Time Trend Radar & Breaking News Takes

### Community 120 - "Task 4 Completion Report: Viral Hook & Native X Poll Pipeline Integration"
Cohesion: 0.22
Nodes (8): 1. Overview & Objectives, 2. Files Modified & Created, 3. Verification & Test Results, 4. Git Commit, Full Unit & Integration Test Suite, Key Accomplishments, Targeted Integration Tests, Task 4 Completion Report: Viral Hook & Native X Poll Pipeline Integration

### Community 121 - "SyncProfileFromX"
Cohesion: 0.11
Nodes (26): asyncio, Path, Tests count parsing helper function across various formats., Tests avatar URL upgrade helper function to 400x400., Tests extracting profile metrics from an authenticated session., Tests extracting profile metrics from a logged-out guest session., Tests detecting access/login challenge screen., Tests that HTTP 404 or network errors return status='failed' and capture… (+18 more)

### Community 122 - "do_run_migrations"
Cohesion: 0.40
Nodes (5): do_run_migrations(), Any, Helper method to run migrations synchronously., Run migrations in 'online' mode using async engine., run_migrations_online()

### Community 123 - "test_sniper_check_targets_executes_reply_and_records_db"
Cohesion: 0.21
Nodes (13): asyncio, AsyncSession, Path, Tests that active profile with target KOLs fetches latest tweet, generates…, Tests that already-seen tweets are skipped via Redis deduplication., Tests that when SafetyGuard indicates rate limit or cooldown, sniper reply is…, Tests that profiles with no configured target KOLs are skipped without…, Tests lock collision handling and guaranteed lock release when exceptions occur. (+5 more)

### Community 124 - "Task 1 Report: Viral Hook Multi-Generator & Evaluator"
Cohesion: 0.25
Nodes (7): 1. Overview & Objectives, 2. Changes Made, 3. Verification & Test Results, Archetypes Implemented:, Files Created / Modified:, Status: COMPLETE, Task 1 Report: Viral Hook Multi-Generator & Evaluator

### Community 125 - "test_poll_generator.py"
Cohesion: 0.10
Nodes (37): asyncio, Tests removing markdown code fences., Tests parsing poll from various JSON structures., Tests successful structured parse via OpenAI beta endpoint., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests that options exceeding 25 characters are safely truncated to 25 chars., Tests that network or API exceptions return a high-quality default fallback…, Tests that unparseable JSON response returns a safe fallback poll. (+29 more)

### Community 126 - "post_session.py"
Cohesion: 0.22
Nodes (10): ExtractedMemoriesResponse, ExtractedMemory, GeneratedDiaryEntry, GeneratedDiaryResponse, AsyncSession, BaseModel, UUID, Runs the post-session diary updates and memory extraction operations. (+2 more)

### Community 127 - "Global Constraints"
Cohesion: 0.33
Nodes (5): Global Constraints, Real-Time Trend Radar & Breaking News Subsystem Implementation Plan, Task 1: Build the Trend Radar Ingestion Engine, Task 2: Build the Trend Relevance Filter & Breaking Take Generator, Task 3: Integrate Celery Periodic Task `check_trend_radar` & Content Staging

### Community 128 - "Attaching to a Running Browser"
Cohesion: 0.40
Nodes (5): Attach by channel name, Attach via browser extension, Attach via CDP endpoint, Attaching to a Running Browser, Detach

### Community 129 - "Task 2 Report: AI Poll Generator Implementation"
Cohesion: 0.40
Nodes (4): 1. Overview & Objectives, 2. Changes Made, 3. Verification & Test Results, Task 2 Report: AI Poll Generator Implementation

### Community 130 - "Task 3 Report: CreatePoll Playwright Browser Action"
Cohesion: 0.40
Nodes (4): Commit, Implementation Summary, Task 3 Report: CreatePoll Playwright Browser Action, Verification Evidence

### Community 131 - "SlidingWindowLimiter"
Cohesion: 0.18
Nodes (9): test_cooldown_tracking(), test_sliding_window_rate_limiter(), datetime, Enforces a strict cooling period for this action type., Checks if a cooldown key exists in Redis and has not yet expired., Implements Phase 3.2 Redis-based Sliding Window Rate Limiter. Utilizes Redis…, Records a new execution event in Redis sorted sets and updates TTL., Evaluates hourly and daily rates. Returns True if limit exceeded in either… (+1 more)

### Community 132 - ".is_action_safe"
Cohesion: 0.16
Nodes (8): AsyncSession, datetime, Runs safety check pipeline: DB status, active cooldowns, and sliding window…, Records the action success in rate limits and applies cooldowns., Sends a synchronous JSON POST webhook payload to external alerts handler…, Processes failures. Checks for CAPTCHAs, account locking (health signals), 429…, Calculates account age and returns multiplier based on Section 9.5 Table., Calculates warm-up multiplier and applies progressive backoff (50% reduction)…

### Community 133 - "0. How generation works"
Cohesion: 0.40
Nodes (5): 0. How generation works, Add assertions manually, Building a test file, Explore before recording, Use semantic locators

### Community 134 - "SDD ledger — plan: docs/superpowers/plans/2026-08-18-trend-radar-plan.md"
Cohesion: 0.40
Nodes (4): Pre-flight Conflict Scan, SDD ledger — plan: docs/superpowers/plans/2026-08-18-trend-radar-plan.md, Task Status, Verification Status

### Community 135 - "Any"
Cohesion: 0.31
Nodes (4): Any, SafeContentStatus, SafeContentType, TypeDecorator

### Community 136 - "load_persona"
Cohesion: 0.36
Nodes (12): load_persona(), Loads persona.yaml from the given profile directory or direct file path., main(), Profile, End-to-End User Experience Verification Script for XBot. Simulates the complete…, verify_api_and_db_integration(), verify_kol_sniper_flow(), verify_poll_generator() (+4 more)

### Community 137 - "2. Generate"
Cohesion: 0.40
Nodes (5): 2.1 Inputs, 2.2 Generate one scenario, 2.3 Generate multiple scenarios, 2.4 Run generated tests, 2. Generate

### Community 138 - "system.py"
Cohesion: 0.11
Nodes (20): configure_db_override(), override_get_db(), AsyncSession, fixture, Configure dependency override for the duration of the test module., configure_db_override(), create_tables(), drop_tables() (+12 more)

### Community 139 - "Task 1 Report: Real-Time Trend Radar Ingestion Engine"
Cohesion: 0.40
Nodes (4): 1. Summary of Changes, 2. Test Execution Results, 3. Git Commit, Task 1 Report: Real-Time Trend Radar Ingestion Engine

### Community 141 - "Task 2 Report: Trend Relevance Filter & Breaking Take Generator"
Cohesion: 0.40
Nodes (4): 1. Overview & Key Deliverables, 2. Test Coverage & Verification, 3. Git Commit, Task 2 Report: Trend Relevance Filter & Breaking Take Generator

### Community 142 - "Task 3 Report: Integrate Celery Periodic Task `check_trend_radar` & Content Staging"
Cohesion: 0.40
Nodes (4): 1. Summary of Changes, 2. Verification Results, 3. Git Commit, Task 3 Report: Integrate Celery Periodic Task `check_trend_radar` & Content Staging

### Community 144 - "Completions"
Cohesion: 0.43
Nodes (3): AsyncOpenAI, Completions, Any

### Community 146 - "Task 1 Report: Cookie Converter & Auth State Engine"
Cohesion: 0.33
Nodes (5): 1. Summary of Changes, 2. Test Verification, 3. Next Steps, Files Created/Modified, Task 1 Report: Cookie Converter & Auth State Engine

### Community 147 - "Task 2 Implementation Report: SyncProfileFromX Playwright Browser Action"
Cohesion: 0.33
Nodes (5): 1. Summary of Changes, 2. Test Verification, 3. Git Commit, Created & Modified Files, Task 2 Implementation Report: SyncProfileFromX Playwright Browser Action

### Community 149 - "websocket_live_global_logs"
Cohesion: 0.40
Nodes (5): Streams real-time updates for a single session execution., Streams live session updates system-wide., websocket_live_global_logs(), websocket_session_logs(), websocket

### Community 150 - "health_check"
Cohesion: 0.40
Nodes (5): health_check(), Any, get, Health check endpoint returning system status., root()

### Community 154 - "persona/__init__.py"
Cohesion: 0.23
Nodes (18): AsyncSession, BaseModel, ReflectionResponse, CredentialsConfig, LearnedCharacteristics, LearnedDislikes, LearnedHabits, LearnedInterests (+10 more)

## Knowledge Gaps
- **408 isolated node(s):** `xbot`, `backup.sh script`, `eslintConfig`, `nextConfig`, `name` (+403 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Profile` to `config.py`, `tasks.py`, `loader.py`, `load_persona`, `system.py`, `models/profile.py`, `test_sniper_task.py`, `get_all_rate_limits`, `generate_ai_content`, `persona/__init__.py`, `Session`, `engagement.py`, `test_trend_task.py`, `ai/__init__.py`, `test_profile_auth_api.py`, `test_poll_integration.py`, `ProfileStatus`, `test_sniper_check_targets_executes_reply_and_records_db`, `post_session.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `Persona` connect `Persona` to `loader.py`, `test_hook_optimizer.py`, `test_trend_generator.py`, `ai/__init__.py`, `test_trend_task.py`, `load_persona`, `models/profile.py`, `test_sniper_task.py`, `test_poll_integration.py`, `.assemble`, `persona/__init__.py`, `test_sniper_check_targets_executes_reply_and_records_db`, `test_poll_generator.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `get_ai_client()` connect `get_ai_client` to `engagement.py`, `Profile`, `tasks.py`, `loader.py`, `test_trend_generator.py`, `ai/__init__.py`, `optimize_post_hook`, `models/profile.py`, `Completions`, `test_poll_integration.py`, `Persona`, `persona/__init__.py`, `test_poll_generator.py`, `post_session.py`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Profile` (e.g. with `test_assembler_missing_directory()` and `test_assembler_success()`) actually correct?**
  _`Profile` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `Persona` (e.g. with `test_generate_sniper_reply_angles_and_prompts()` and `test_generate_sniper_reply_auto_angle_selection()`) actually correct?**
  _`Persona` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 35 inferred relationships involving `ProfileStatus` (e.g. with `test_assembler_missing_directory()` and `test_assembler_success()`) actually correct?**
  _`ProfileStatus` has 35 INFERRED edges - model-reasoned connections that need verification._
- **What connects `xbot`, `backup.sh script`, `eslintConfig` to the rest of the system?**
  _408 weakly-connected nodes found - possible documentation gaps or missing edges._