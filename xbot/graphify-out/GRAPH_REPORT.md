# Graph Report - xbot  (2026-08-21)

## Corpus Check
- 160 files · ~236,901 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1933 nodes · 4114 edges · 122 communities (102 shown, 20 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 440 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `aac36c58`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- profiles.py
- Master Plan
- test_safety_and_scheduling.py
- Skill
- page.tsx
- Session Management
- test_trend_generator.py
- sleep_with_jitter
- Storage State
- x_actions.py
- tasks.py
- Running Code
- Test Generation
- test_poll_generator.py
- config.py
- fetch_rss_trends
- models/profile.py
- devDependencies
- test_sniper_task.py
- Persona
- test_poll_integration.py
- loader.py
- compilerOptions
- Tracing
- test_trend_task.py
- manager.py
- SyncProfileFromX
- CheckUserLatestTweet
- ReflectionResponse
- test_profile_auth.py
- test_profile_auth_api.py
- engagement.py
- get_all_rate_limits
- ai/__init__.py
- MemoryManager
- generate_ai_content
- e2e_authenticated_session_test.py
- Video Recording
- ContextAssembler
- inspect_profile_auth_status
- Technical Specification: XBot Autonomous AI Persona Platform & UI Modernization
- Profile
- .get_context
- Request Mocking
- DiaryManager
- ThreadedUvicorn
- Global Constraints
- poll_action.py
- get_session_actions
- e2e_full_user_experience.py
- Readme
- .assemble
- post_session.py
- Decisions
- get_free_analytics
- analyze_sentiment_rules
- Project Status
- RoutingClient
- Any
- Playwright Tests
- Tasks
- schemas/profile.py
- load_raw_card
- 2026 08 18 Kol Sniper Reply Design
- 2026 08 18 Viral Hook And Poll Design
- Task 1 Report
- Task 4 Report
- .generate_content
- Element Attributes
- 2026 08 18 Trend Radar Design
- 2026 08 18 Profile Auth And Metrics Sync Design
- Task 3 Report
- Task 1 Report
- do_run_migrations
- websocket_live_global_logs
- health_check
- 2026 08 18 Kol Sniper Reply Plan
- 2026 08 18 Viral Hook And Poll Plan
- Task 1 Report
- Task 2 Report
- Task 4 Report
- Task 2 Report
- Task 1 Report
- Task 2 Report
- Task 3 Report
- ScrapeProfileMetrics
- Readme
- layout.tsx
- Progress
- Task 3 Report
- Progress
- Task 2 Report
- Task 3 Report
- Progress
- .capture_failure
- 2026 08 18 Trend Radar Plan
- 2026 06 29
- 2026 06 30
- Progress
- Task 4 Report
- Graphify
- Graphify
- _extract_tweet_id_from_url
- backup.sh
- Agents
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- 2026 08 18 Profile Auth And Metrics Sync Plan
- ScrapeProfileTweets
- StrategyResponse
- Readme
- Litellm Config
- Claude
- Docker Compose
- xbot

## God Nodes (most connected - your core abstractions)
1. `Profile` - 116 edges
2. `Master Plan` - 106 edges
3. `Persona` - 71 edges
4. `Skill` - 56 edges
5. `ProfileStatus` - 53 edges
6. `Session Management` - 52 edges
7. `Storage State` - 47 edges
8. `Running Code` - 40 edges
9. `Test Generation` - 40 edges
10. `load_persona()` - 37 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_browser_auth.py → backend/xbot/browser/manager.py
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_follow_selectors.py → backend/xbot/browser/manager.py
- `main()` --uses--> `CheckUserLatestTweet`  [INFERRED]
  test-script/test_live_actions.py → backend/xbot/browser/actions/check_user_action.py
- `run_step_3_sync_from_x()` --uses--> `SyncProfileFromX`  [INFERRED]
  test-script/e2e_authenticated_session_test.py → backend/xbot/browser/actions/sync_profile_action.py
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_actions.py → backend/xbot/browser/manager.py

## Import Cycles
- None detected.

## Communities (122 total, 20 thin omitted)

### Community 0 - "profiles.py"
Cohesion: 0.08
Nodes (64): create_profile(), delete_profile(), get_profile(), get_profile_analytics_snapshots(), get_profile_auth_status(), get_profile_config(), get_profile_diary_logs(), get_profile_learned_state() (+56 more)

### Community 1 - "Master Plan"
Cohesion: 0.02
Nodes (107): 10.1 Data Collection, 10.2 Analytics Snapshot Process, 10.3 Performance Scoring, 10.4 Strategy Engine (Weekly Review), 10.5 Monetization Tracking, 10. Analytics & Strategy Engine, 11.1 Dashboard Pages, 11.2 Key Features (+99 more)

### Community 2 - "test_safety_and_scheduling.py"
Cohesion: 0.06
Nodes (39): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Path, setup_db(), test_cooldown_tracking() (+31 more)

### Community 3 - "Skill"
Cohesion: 0.04
Nodes (57): --submit presses Enter after filling the element, Browser Automation with playwright-cli, Browser Sessions, Close all browsers, close the browser, Commands, Connect to a running browser via CDP endpoint, Connect to a running Chrome or Edge by channel name (+49 more)

### Community 4 - "page.tsx"
Cohesion: 0.08
Nodes (29): API_PROVIDERS, CONTEXT_OPTIONS, Dashboard(), getAvatarUrl(), JobModelSelector(), ConnectAccountModal(), ConnectAccountModalProps, GrowthEngineTab() (+21 more)

### Community 5 - "Session Management"
Cohesion: 0.04
Nodes (53): 1. Name Browser Sessions Semantically, 2. Always Clean Up, 3. Delete Stale Browser Data, A/B Testing Sessions, Attach by channel name, Attach to Chrome, Attach to Chrome Canary, Attach to Edge Dev (+45 more)

### Community 6 - "test_trend_generator.py"
Cohesion: 0.09
Nodes (48): irrelevant_trend_item(), asyncio, fixture, Tests Pydantic validation and field constraints on TrendEvaluation., Tests removing markdown code fences from LLM responses., Tests parsing trend evaluation from various JSON formats., Tests successful structured parse and hook optimization on relevant trend item., Tests that irrelevant news items return is_relevant=False and do NOT call hook… (+40 more)

### Community 7 - "sleep_with_jitter"
Cohesion: 0.11
Nodes (35): Page, Executes poll creation on X: 1. Opens compose modal or navigates to…, human_scroll_to_tweet(), _navigate_home_if_needed(), _post_action_cooldown_browse(), Any, Page, _random_tab_detour() (+27 more)

### Community 8 - "Storage State"
Cohesion: 0.04
Nodes (48): ... later, in a new session ..., Advanced: Multiple Cookies or Custom Options, Advanced: Multiple Operations, Already logged in!, Authentication State Reuse, Basic cookie, Clear All Cookies, Clear All localStorage (+40 more)

### Community 9 - "x_actions.py"
Cohesion: 0.11
Nodes (35): asyncio, Path, Executes and validates the complete library of browser actions against the…, test_x_actions_integration(), BaseAction, Base action class providing failure recovery, logging, and screenshot tools., Browser action for checking a user's profile and extracting their latest tweet., Browser action for synchronizing X profile data and verifying session… (+27 more)

### Community 10 - "tasks.py"
Cohesion: 0.07
Nodes (47): BrowserManager, Releases the execution lock for a profile., Manages Playwright browser automation contexts and anti-detection settings.…, Stops the Playwright driver., Acquires a lock in Redis to prevent multiple workers from running the same…, broadcast_session_log(), check_schedules(), collect_analytics_snapshot() (+39 more)

### Community 11 - "Running Code"
Cohesion: 0.05
Nodes (41): Clear geolocation override, Clipboard, Complex Workflows, Running Code, Emulate dark color scheme, Emulate light color scheme, Emulate print media, Emulate reduced motion (+33 more)

### Community 12 - "Test Generation"
Cohesion: 0.05
Nodes (41): 0. How generation works, 1.1 Prerequisite: workspace, 1.2 Prerequisite: seed test, 1.3 Explore the app, 1.4 Write the spec file, 1. <Group Name>, 1. Planning, 2.1 Inputs (+33 more)

### Community 13 - "test_poll_generator.py"
Cohesion: 0.10
Nodes (37): asyncio, Tests removing markdown code fences., Tests parsing poll from various JSON structures., Tests successful structured parse via OpenAI beta endpoint., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests that options exceeding 25 characters are safely truncated to 25 chars., Tests that network or API exceptions return a high-quality default fallback…, Tests that unparseable JSON response returns a safe fallback poll. (+29 more)

### Community 14 - "config.py"
Cohesion: 0.12
Nodes (17): configure_db_override(), create_tables(), drop_tables(), override_get_db(), AsyncSession, fixture, Override database dependency to use test database., Configure dependency override for the duration of the test module. (+9 more)

### Community 15 - "fetch_rss_trends"
Cohesion: 0.19
Nodes (24): asyncio, test_fetch_atom_1_0_parsing(), test_fetch_rss_2_0_parsing(), test_fetch_rss_trends_default_client(), test_http_status_error_resilience(), test_keyword_filtering(), test_malformed_xml_resilience(), test_max_items_per_feed() (+16 more)

### Community 16 - "models/profile.py"
Cohesion: 0.16
Nodes (24): Run migrations in 'offline' mode., run_migrations_offline(), configure_db_override(), create_tables(), drop_tables(), override_get_db(), populate_profile_files(), asyncio (+16 more)

### Community 17 - "devDependencies"
Cohesion: 0.06
Nodes (34): dependencies, lucide-react, next, react, react-dom, devDependencies, eslint, eslint-config-next (+26 more)

### Community 18 - "test_sniper_task.py"
Cohesion: 0.13
Nodes (21): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Path, Verifies that the periodic schedule for sniper_check_targets is registered in…, Tests that active profile with target KOLs fetches latest tweet, generates… (+13 more)

### Community 19 - "Persona"
Cohesion: 0.13
Nodes (33): asyncio, fixture, Tests fallback to chat.completions.create with JSON parsing when structured…, Tests fallback when response is plain unformatted text (not JSON)., Tests that various angles (witty, data, contrarian, framework, insight) are…, Tests that when preferred_angle is None, prompt instructs auto-selection among…, Tests that complete LLM failure returns a safe fallback SniperReplyResult…, Tests that when client is None, get_ai_client() is invoked. (+25 more)

### Community 20 - "test_poll_integration.py"
Cohesion: 0.15
Nodes (30): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Verifies that ActionType and ContentType include POLL enum members., Verifies generate_tweet passes draft_tweet through optimize_post_hook and…, Verifies generate_tweet creates a draft tweet from LLM then runs hook… (+22 more)

### Community 21 - "loader.py"
Cohesion: 0.13
Nodes (44): test_persona_with_target_kols(), test_yaml_loader_and_saver(), AsyncSession, AsyncSession, datetime, Runs the weekly strategic analysis and updates strategy.yaml., AccountRelationship, Config (+36 more)

### Community 22 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 23 - "Tracing"
Cohesion: 0.07
Nodes (28): 1. Start Tracing Before the Problem, 2. Clean Up Old Traces, ... all steps leading to the issue ..., `resources/`, `trace-{timestamp}.network`, `trace-{timestamp}.trace`, Analyzing Performance, Basic Usage (+20 more)

### Community 24 - "test_trend_task.py"
Cohesion: 0.12
Nodes (41): sample_persona(), fixture, sample_persona(), fixture, sample_persona(), sample_persona(), sample_persona_no_kols(), sample_persona_with_kols() (+33 more)

### Community 25 - "manager.py"
Cohesion: 0.08
Nodes (20): asyncio, Verifies BrowserManager startup, Redis-based locking, context creation, and…, test_browser_manager_flow(), apply_stealth(), apply_stealth_to_context(), _build_stealth_script(), BrowserContext, Page (+12 more)

### Community 26 - "SyncProfileFromX"
Cohesion: 0.11
Nodes (26): asyncio, Path, Tests count parsing helper function across various formats., Tests avatar URL upgrade helper function to 400x400., Tests extracting profile metrics from an authenticated session., Tests extracting profile metrics from a logged-out guest session., Tests detecting access/login challenge screen., Tests that HTTP 404 or network errors return status='failed' and capture… (+18 more)

### Community 27 - "CheckUserLatestTweet"
Cohesion: 0.13
Nodes (22): asyncio, Path, Tests fallback to second tweet when the first tweet is pinned., Tests extracting the pinned tweet when no second tweet is available., Tests returning None when profile has no tweets., Tests returning None and capturing failure screenshot on navigation error., Tests extracting standard latest tweet from profile., test_check_user_latest_tweet_empty_profile() (+14 more)

### Community 29 - "test_profile_auth.py"
Cohesion: 0.11
Nodes (24): Test parsing raw JSON object format., Test parsing full Playwright storage_state JSON string., Test parsing multiline newline-separated cookie string., Test format_storage_state generates standard Playwright storage state structure., Test empty, whitespace, and malformed inputs., Test inspect_profile_auth_status with valid active storage_state.json., Test format_storage_state includes twid when provided., Test parsing standard HTTP Cookie header string. (+16 more)

### Community 30 - "test_profile_auth_api.py"
Cohesion: 0.17
Nodes (18): configure_db_override(), create_tables(), create_test_profile(), drop_tables(), override_get_db(), AsyncSession, fixture, Path (+10 more)

### Community 31 - "engagement.py"
Cohesion: 0.14
Nodes (16): EngagementDecision, EngagementEvaluator, EngagementResponse, FollowDecision, FollowEvaluator, FollowResponse, Any, AsyncSession (+8 more)

### Community 32 - "get_all_rate_limits"
Cohesion: 0.11
Nodes (21): get_all_rate_limits(), get_system_config(), get_system_health(), get_system_models(), pause_entire_system(), Any, AsyncSession, BaseModel (+13 more)

### Community 33 - "ai/__init__.py"
Cohesion: 0.07
Nodes (48): asyncio, Tests cleaning archetype prefixes and long strings., Tests body preservation and micro-spacing in format_optimized_post., Tests format_optimized_post with a single line draft., Tests successful structured parse with 4 archetypes and winning hook selection., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests JSON parsing when returned as a dict keyed by archetype name., Tests that LLM network or API exceptions return original content safely. (+40 more)

### Community 34 - "MemoryManager"
Cohesion: 0.17
Nodes (10): MemoryManager, Any, Path, Appends a persistent high-importance memory., Retrieves a compiled list of memories based on recency, importance, and query.…, Manages episodic, semantic, and high-importance memories for a persona. Saves…, Appends a single JSON record to the specified file., Reads all JSON records from a JSONL file. (+2 more)

### Community 35 - "generate_ai_content"
Cohesion: 0.18
Nodes (17): generate_ai_content(), GenerateContentRequest, get_content_detail(), list_profile_content(), Any, AsyncSession, BaseModel, get (+9 more)

### Community 36 - "e2e_authenticated_session_test.py"
Cohesion: 0.38
Nodes (11): main(), Profile, End-to-End Comprehensive Feature Test for Authenticated Profile (@jackds1234 /…, run_step_1_services_health(), run_step_2_auth_status(), run_step_3_sync_from_x(), run_step_4_kol_sniper(), run_step_5_viral_hook_optimizer() (+3 more)

### Community 37 - "Video Recording"
Cohesion: 0.12
Nodes (16): 1. Use Descriptive Filenames, 2. Record entire hero scripts., Add a chapter marker for section transitions, Add another chapter, Basic Recording, Best Practices, Video Recording, Include context in filename (+8 more)

### Community 38 - "ContextAssembler"
Cohesion: 0.13
Nodes (19): db_session(), asyncio, AsyncSession, fixture, Path, Creates and teardowns the test database structure., Yields a clean database session., setup_db() (+11 more)

### Community 39 - "inspect_profile_auth_status"
Cohesion: 0.19
Nodes (13): Path, Test inspect_profile_auth_status when storage_state.json does not exist., Test inspect_profile_auth_status with only auth_token present., Test inspect_profile_auth_status with expired cookies., Test inspect_profile_auth_status when storage_state.json is malformed., test_inspect_profile_auth_status_corrupt_file(), test_inspect_profile_auth_status_expired(), test_inspect_profile_auth_status_missing() (+5 more)

### Community 40 - "Technical Specification: XBot Autonomous AI Persona Platform & UI Modernization"
Cohesion: 0.20
Nodes (9): 1. Product Identity & Purpose, 2. Feature Inventory: Final Decisions, 3. System Architecture & Components, 4. Frontend Modularization (5-Tab Glassmorphic UI), 5. Implementation & Migration Steps, Central Tab Breakdown, Kept & Enhanced Features, Purged / Removed Features (+1 more)

### Community 41 - "Profile"
Cohesion: 0.14
Nodes (28): db_session(), populate_profile_files(), asyncio, AsyncSession, fixture, Path, setup_db(), test_content_generator_with_retries() (+20 more)

### Community 42 - ".get_context"
Cohesion: 0.40
Nodes (3): BrowserContext, Creates or retrieves a persistent browser context for the profile. Picks a…, Starts the Playwright driver.

### Community 43 - "Request Mocking"
Cohesion: 0.13
Nodes (15): Advanced Mocking with run-code, CLI Route Commands, Conditional Response Based on Request, Delayed Response, Request Mocking, List active routes, Mock with custom headers, Mock with custom status (+7 more)

### Community 44 - "DiaryManager"
Cohesion: 0.13
Nodes (11): Path, test_diary_manager(), test_memory_manager(), AsyncSession, UUID, Runs the post-session diary updates and memory extraction operations., DiaryManager, Path (+3 more)

### Community 45 - "ThreadedUvicorn"
Cohesion: 0.18
Nodes (9): home_feed(), profile_page(), get, Runs the mock FastAPI application inside a background thread., search_results(), ThreadedUvicorn, mock_x_server(), fixture (+1 more)

### Community 46 - "Global Constraints"
Cohesion: 0.25
Nodes (7): Global Constraints, Task 1: Repository Purge & Legacy Cleanup, Task 2: Backend API & WebSocket Hardening, Task 3: Dashboard API Client & Modular Sub-Components, Task 4: Streamline Dashboard Root Container (`page.tsx`), Task 5: End-to-End Verification & Knowledge Graph Update, XBot Architecture & UI Redesign Implementation Plan

### Community 47 - "poll_action.py"
Cohesion: 0.24
Nodes (14): asyncio, Path, Tests creating a standard 2-option poll., Tests creating a 4-option poll with multiple extra choices added., Tests creating a 3-option poll with 1 extra choice., Tests navigating to compose post URL if textarea is not already on page., Tests that execution errors gracefully return False and capture failure…, test_create_poll_2_options_success() (+6 more)

### Community 48 - "get_session_actions"
Cohesion: 0.26
Nodes (13): get_session_actions(), get_session_detail(), list_profile_sessions(), Any, AsyncSession, get, post, UUID (+5 more)

### Community 49 - "e2e_full_user_experience.py"
Cohesion: 0.40
Nodes (10): main(), Profile, End-to-End User Experience Verification Script for XBot. Simulates the complete…, verify_api_and_db_integration(), verify_kol_sniper_flow(), verify_poll_generator(), verify_profile_and_kol_setup(), verify_services_online() (+2 more)

### Community 50 - "Readme"
Cohesion: 0.15
Nodes (13): 1. Initialize the Environment, 2. Startup Backend Service (FastAPI), 3. Launch Celery Worker & Beat Scheduler, 4. Launch Next.js Dashboard UI, 🛠 Project Structure, 🚀 Quick Start & Launch Runbook, 🧪 Running Tests, 🛡 Safety Guard & Webhook Alerting (+5 more)

### Community 51 - ".assemble"
Cohesion: 0.18
Nodes (8): AssembledContext, AsyncSession, BaseModel, datetime, Helper to dump Strategy model to YAML string., Gathers files and database records to construct an AssembledContext for the…, Helper to format the Persona object into a markdown character sheet., Renders the user prompt context following the structure defined in…

### Community 52 - "post_session.py"
Cohesion: 0.23
Nodes (9): ExtractedMemoriesResponse, ExtractedMemory, GeneratedDiaryEntry, GeneratedDiaryResponse, PostSessionProcessor, BaseModel, Implements Phase 2.5 Post-Session Processing. Evaluates session execution…, Evaluates recent session logs, episodic memories, and content performance to… (+1 more)

### Community 53 - "Decisions"
Cohesion: 0.17
Nodes (12): 2026-06-18: Initial Architecture Mapping, DEC-001: Backend Framework Choice, DEC-002: Project Init using `uv`, DEC-003: Strict Linting and Type Checking Configuration, DEC-004: Rename Virtual Environment to `.venv`, DEC-005: Switch Database from PostgreSQL to SQLite, DEC-006: Utilize Host Native Redis and External LiteLLM, DEC-011: Local Mock X Server for Browser Automation (+4 more)

### Community 54 - "get_free_analytics"
Cohesion: 0.33
Nodes (6): AnalyticsRequest, get_free_analytics(), Any, BaseModel, post, Deprecated: Free analytics scraper sandbox has been removed.

### Community 55 - "analyze_sentiment_rules"
Cohesion: 0.50
Nodes (4): analyze_sentiment_llm(), analyze_sentiment_rules(), Performs offline, fast rule-based sentiment classification on input text., Performs sentiment analysis using the fast LiteLLM model.

### Community 56 - "Project Status"
Cohesion: 0.20
Nodes (10): Project Status, Overall Status, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening (+2 more)

### Community 57 - "RoutingClient"
Cohesion: 0.15
Nodes (8): AsyncOpenAI, Beta, BetaChat, Chat, Completions, Any, A smart facade for AsyncOpenAI that dynamically routes requests to the correct…, RoutingClient

### Community 58 - "Any"
Cohesion: 0.31
Nodes (4): Any, SafeContentStatus, SafeContentType, TypeDecorator

### Community 59 - "Playwright Tests"
Cohesion: 0.22
Nodes (9): ..., ... debugging instructions for "tw-abcdef" session ..., Attach to the test, Debugging Playwright Tests, Playwright Tests, Run all tests, Run all tests through a custom npm script, Run the test (+1 more)

### Community 60 - "Tasks"
Cohesion: 0.22
Nodes (9): Active Task, Tasks, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening (+1 more)

### Community 61 - "schemas/profile.py"
Cohesion: 0.62
Nodes (5): ProfileBase, ProfileCreate, ProfileResponse, ProfileUpdate, BaseModel

### Community 62 - "load_raw_card"
Cohesion: 0.40
Nodes (5): load_raw_card(), map_card_to_persona(), Any, Loads a character card from either an absolute file path on the server or raw…, Deterministically maps any structured character card (such as Kaya's JSON…

### Community 63 - "2026 08 18 Kol Sniper Reply Design"
Cohesion: 0.25
Nodes (8): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.3 Sniper Angle & Response Engine (`xbot/ai/sniper.py`), 3.5 Periodic Task Runner (`xbot/tasks.py`), 3. Detailed Component Specifications, 4. Error Handling & Edge Cases, 5. Verification & Testing Plan, 2026 08 18 Kol Sniper Reply Design

### Community 64 - "2026 08 18 Viral Hook And Poll Design"
Cohesion: 0.25
Nodes (8): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Hook Optimization Engine (`xbot/ai/hook_optimizer.py`), 3.2 Poll Generation Engine (`xbot/ai/poll_generator.py`), 3. Detailed Component Specifications, 4. Integration into Session Planner & Content Pipeline, 5. Testing & Verification, 2026 08 18 Viral Hook And Poll Design

### Community 65 - "Task 1 Report"
Cohesion: 0.25
Nodes (8): 1. Overview & Objectives, 2. Changes Made, 3. Verification & Test Results, Archetypes Implemented:, Task 1 Report, Files Created / Modified:, Status: COMPLETE, Task 1 Report: Viral Hook Multi-Generator & Evaluator

### Community 66 - "Task 4 Report"
Cohesion: 0.25
Nodes (8): 1. Overview & Objectives, 2. Files Modified & Created, 3. Verification & Test Results, 4. Git Commit, Task 4 Report, Full Unit & Integration Test Suite, Key Accomplishments, Targeted Integration Tests

### Community 67 - ".generate_content"
Cohesion: 0.29
Nodes (6): calculate_similarity(), clean_text_for_json(), AsyncSession, Calculates similarity ratio between two strings using difflib., Clean markdown json wrap., Generates content, validates it, and handles automatic regeneration on failure…

### Community 68 - "Element Attributes"
Cohesion: 0.29
Nodes (7): Element Attributes, Examples, get a computed style property, get a specific attribute, get all CSS classes, get the element's id, Inspecting Element Attributes

### Community 69 - "2026 08 18 Trend Radar Design"
Cohesion: 0.29
Nodes (7): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Feed & Trend Ingestion Layer (`xbot/ai/trend_radar.py`), 3.3 Celery Periodic Task & Queue Routing (`xbot/tasks.py`), 3. Detailed Component Specifications, 4. Verification & Testing, 2026 08 18 Trend Radar Design

### Community 70 - "2026 08 18 Profile Auth And Metrics Sync Design"
Cohesion: 0.33
Nodes (6): 1. Executive Summary, 2. Architecture & Data Flow, 3.3 REST Endpoints (`backend/xbot/api/profiles.py`), 3. Component Specifications, 4. Verification & Testing, 2026 08 18 Profile Auth And Metrics Sync Design

### Community 71 - "Task 3 Report"
Cohesion: 0.33
Nodes (6): Changes Made, Task 3 Report, Git Commit, Overview, Task 3 Report: Build AI Sniper Angle & Response Generator, Test Verification

### Community 72 - "Task 1 Report"
Cohesion: 0.33
Nodes (6): 1. Summary of Changes, 2. Test Verification, 3. Next Steps, Task 1 Report, Files Created/Modified, Task 1 Report: Cookie Converter & Auth State Engine

### Community 73 - "do_run_migrations"
Cohesion: 0.40
Nodes (5): do_run_migrations(), Any, Helper method to run migrations synchronously., Run migrations in 'online' mode using async engine., run_migrations_online()

### Community 74 - "websocket_live_global_logs"
Cohesion: 0.40
Nodes (5): Streams real-time updates for a single session execution., Streams live session updates system-wide., websocket_live_global_logs(), websocket_session_logs(), websocket

### Community 75 - "health_check"
Cohesion: 0.40
Nodes (5): health_check(), Any, get, Health check endpoint returning system status., root()

### Community 76 - "2026 08 18 Kol Sniper Reply Plan"
Cohesion: 0.40
Nodes (5): 2026 08 18 Kol Sniper Reply Plan, Global Constraints, Plan Verification & Self-Review Checklist, Task 1: Extend Persona Model and Schema with Target KOLs, Task 3: Build AI Sniper Angle & Response Generator

### Community 77 - "2026 08 18 Viral Hook And Poll Plan"
Cohesion: 0.40
Nodes (5): 2026 08 18 Viral Hook And Poll Plan, Global Constraints, Task 1: Build the Viral Hook Optimizer & Scorer, Task 2: Build the AI Poll Generator, Task 3: Implement `CreatePoll` Playwright Browser Action

### Community 78 - "Task 1 Report"
Cohesion: 0.40
Nodes (5): Changes Made, Task 1 Report, Git Commit, Overview, Test Verification

### Community 79 - "Task 2 Report"
Cohesion: 0.40
Nodes (5): Changes Made, Task 2 Report, Git Commit, Overview, Test Verification

### Community 80 - "Task 4 Report"
Cohesion: 0.40
Nodes (5): Changes Made, Task 4 Report, Git Commit, Overview, Test Verification

### Community 81 - "Task 2 Report"
Cohesion: 0.40
Nodes (5): 1. Summary of Changes, 2. Test Verification, 3. Git Commit, Created & Modified Files, Task 2 Report

### Community 82 - "Task 1 Report"
Cohesion: 0.40
Nodes (5): 1. Summary of Changes, 2. Test Execution Results, 3. Git Commit, Task 1 Report, Task 1 Report: Real-Time Trend Radar Ingestion Engine

### Community 83 - "Task 2 Report"
Cohesion: 0.40
Nodes (5): 1. Overview & Objectives, 2. Changes Made, 3. Verification & Test Results, Task 2 Report, Task 2 Report: AI Poll Generator Implementation

### Community 84 - "Task 3 Report"
Cohesion: 0.40
Nodes (5): Commit, Task 3 Report, Implementation Summary, Task 3 Report: CreatePoll Playwright Browser Action, Verification Evidence

### Community 86 - "Readme"
Cohesion: 0.50
Nodes (4): Deploy on Vercel, Readme, Getting Started, Learn More

### Community 88 - "Progress"
Cohesion: 0.50
Nodes (4): Progress, Pre-flight Conflict Scan, Task Status, Verification Status

### Community 89 - "Task 3 Report"
Cohesion: 0.50
Nodes (4): 1. Summary of Changes, 2. Test Coverage & Verification, Task 3 Report, Pytest Results

### Community 90 - "Progress"
Cohesion: 0.50
Nodes (4): Progress, Pre-flight Conflict Scan, Task Status, Verification Status

### Community 91 - "Task 2 Report"
Cohesion: 0.50
Nodes (4): 1. Overview & Key Deliverables, 2. Test Coverage & Verification, 3. Git Commit, Task 2 Report

### Community 92 - "Task 3 Report"
Cohesion: 0.50
Nodes (4): 1. Summary of Changes, 2. Verification Results, 3. Git Commit, Task 3 Report

### Community 93 - "Progress"
Cohesion: 0.50
Nodes (4): Progress, Pre-flight Conflict Scan, Task Status, Verification Status

### Community 98 - "2026 08 18 Trend Radar Plan"
Cohesion: 0.67
Nodes (3): 2026 08 18 Trend Radar Plan, Global Constraints, Task 1: Build the Trend Radar Ingestion Engine

### Community 99 - "2026 06 29"
Cohesion: 0.67
Nodes (3): 2026 06 29, Memory Log - June 29, 2026, Work Accomplished

### Community 100 - "2026 06 30"
Cohesion: 0.67
Nodes (3): 2026 06 30, Memory Log - June 30, 2026, Work Accomplished

### Community 101 - "Progress"
Cohesion: 0.67
Nodes (3): Progress, Pre-flight Conflict Scan, Task Status

### Community 102 - "Task 4 Report"
Cohesion: 0.67
Nodes (3): Changes Summary, Task 4 Report, Status: COMPLETE

## Knowledge Gaps
- **650 isolated node(s):** `xbot`, `backup.sh script`, `eslintConfig`, `nextConfig`, `name` (+645 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Profile` to `profiles.py`, `get_all_rate_limits`, `test_safety_and_scheduling.py`, `generate_ai_content`, `e2e_authenticated_session_test.py`, `ContextAssembler`, `x_actions.py`, `tasks.py`, `config.py`, `models/profile.py`, `e2e_full_user_experience.py`, `test_sniper_task.py`, `test_poll_integration.py`, `loader.py`, `post_session.py`, `test_trend_task.py`, `test_profile_auth_api.py`, `engagement.py`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `Persona` connect `Persona` to `ai/__init__.py`, `test_trend_generator.py`, `ContextAssembler`, `test_poll_generator.py`, `test_sniper_task.py`, `.assemble`, `test_poll_integration.py`, `loader.py`, `test_trend_task.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `get_ai_client()` connect `ai/__init__.py` to `profiles.py`, `.generate_content`, `ContextAssembler`, `test_trend_generator.py`, `Profile`, `tasks.py`, `DiaryManager`, `test_poll_generator.py`, `Persona`, `post_session.py`, `loader.py`, `analyze_sentiment_rules`, `RoutingClient`, `engagement.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 90 inferred relationships involving `Profile` (e.g. with `test_assembler_missing_directory()` and `test_assembler_success()`) actually correct?**
  _`Profile` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `Persona` (e.g. with `test_generate_sniper_reply_angles_and_prompts()` and `test_generate_sniper_reply_auto_angle_selection()`) actually correct?**
  _`Persona` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `ProfileStatus` (e.g. with `test_assembler_missing_directory()` and `test_assembler_success()`) actually correct?**
  _`ProfileStatus` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `xbot`, `backup.sh script`, `eslintConfig` to the rest of the system?**
  _650 weakly-connected nodes found - possible documentation gaps or missing edges._