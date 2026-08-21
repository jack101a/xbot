# Graph Report - xbot  (2026-08-21)

## Corpus Check
- 206 files · ~245,432 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1980 nodes · 4234 edges · 140 communities (123 shown, 17 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 455 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Browser Auth & Profile Sync
- Browser Session & Lock Manager
- Viral Hook Optimization
- Playwright CLI Reference (playwright-cli)
- KOL Sniper & Reply Engine
- Playwright CLI Reference (references)
- Trend Radar & Generation
- Playwright CLI Reference (actions)
- Playwright CLI Reference (references)
- Viral Poll Creation & Actions
- Trend Radar & Generation
- Playwright CLI Reference (references)
- Playwright CLI Reference (references)
- Viral Poll Creation & Actions
- Database Schema & ORM Models
- Trend Radar & Generation
- Database Schema & ORM Models
- Dashboard UI (dashboard)
- KOL Sniper & Reply Engine
- KOL Sniper & Reply Engine
- Viral Poll Creation & Actions
- KOL Sniper & Reply Engine
- Dashboard UI (dashboard)
- Playwright CLI Reference (references)
- Trend Radar & Generation
- KOL Sniper & Reply Engine
- Browser Auth & Profile Sync
- KOL Sniper & Reply Engine
- Persona & Cognitive Memory Engine
- Browser Auth & Profile Sync
- Browser Auth & Profile Sync
- Persona & Cognitive Memory Engine
- Database Schema & ORM Models
- Viral Hook Optimization
- Persona & Cognitive Memory Engine
- FastAPI REST Endpoints
- Viral Hook Optimization
- Playwright CLI Reference (references)
- Persona & Cognitive Memory Engine
- Browser Auth & Profile Sync
- Trend Radar & Generation
- Database Schema & ORM Models
- Browser Session & Lock Manager
- Playwright CLI Reference (references)
- Persona & Cognitive Memory Engine
- Twitter / X Browser Automation
- Viral Hook Optimization
- Viral Poll Creation & Actions
- Superpowers Specs & Plans
- Trend Radar & Generation
- Viral Hook Optimization
- Persona & Cognitive Memory Engine
- Persona & Cognitive Memory Engine
- Database Schema & ORM Models
- Twitter / X Browser Automation
- Viral Poll Creation & Actions
- Persona & Cognitive Memory Engine
- Client Engine
- Database Schema & ORM Models
- Playwright CLI Reference (references)
- Persona & Cognitive Memory Engine
- Client Engine
- Database Schema & ORM Models
- KOL Sniper & Reply Engine
- Viral Poll Creation & Actions
- Viral Poll Creation & Actions
- Viral Poll Creation & Actions
- Generator Engine
- Playwright CLI Reference (references)
- Trend Radar & Generation
- Superpowers Specs & Plans
- KOL Sniper & Reply Engine
- Superpowers Specs & Plans
- Env Engine
- FastAPI REST Endpoints
- Main Engine
- KOL Sniper & Reply Engine
- Viral Poll Creation & Actions
- KOL Sniper & Reply Engine
- KOL Sniper & Reply Engine
- KOL Sniper & Reply Engine
- Superpowers Specs & Plans
- Trend Radar & Generation
- Viral Poll Creation & Actions
- Viral Poll Creation & Actions
- Twitter / X Browser Automation
- Dashboard UI (dashboard)
- Dashboard UI (app)
- KOL Sniper & Reply Engine
- Superpowers Specs & Plans
- Trend Radar & Generation
- Trend Radar & Generation
- Trend Radar & Generation
- Viral Poll Creation & Actions
- Twitter / X Browser Automation
- Trend Radar & Generation
- 2026-06-29 Engine
- 2026-06-30 Engine
- Superpowers Specs & Plans
- Superpowers Specs & Plans
- Graphify Engine
- Graphify Engine
- Twitter / X Browser Automation
- Backup Engine
- Dashboard UI (dashboard)
- Dashboard UI (dashboard)
- Dashboard UI (dashboard)
- Dashboard UI (dashboard)
- Superpowers Specs & Plans
- Readme Engine
- Litellm Config Engine
- Dashboard UI (dashboard)
- Docker-Compose Engine
- Pyproject Engine

## God Nodes (most connected - your core abstractions)
1. `Profile` - 125 edges
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
- `run_e2e_test()` --uses--> `ContentGenerator`  [INFERRED]
  test-script/test_ai_ghostwriter.py → backend/xbot/ai/generator.py
- `main()` --uses--> `CheckUserLatestTweet`  [INFERRED]
  test-script/test_live_actions.py → backend/xbot/browser/actions/check_user_action.py
- `run_step_3_sync_from_x()` --uses--> `SyncProfileFromX`  [INFERRED]
  test-script/e2e_authenticated_session_test.py → backend/xbot/browser/actions/sync_profile_action.py
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_actions.py → backend/xbot/browser/manager.py
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_browser_auth.py → backend/xbot/browser/manager.py

## Import Cycles
- None detected.

## Communities (140 total, 17 thin omitted)

### Community 0 - "Browser Auth & Profile Sync"
Cohesion: 0.05
Nodes (106): create_campaign(), create_profile(), delete_campaign(), delete_profile(), get_campaigns(), get_follower_changelogs(), get_follower_snapshots(), get_profile() (+98 more)

### Community 1 - "Browser Session & Lock Manager"
Cohesion: 0.02
Nodes (107): 10.1 Data Collection, 10.2 Analytics Snapshot Process, 10.3 Performance Scoring, 10.4 Strategy Engine (Weekly Review), 10.5 Monetization Tracking, 10. Analytics & Strategy Engine, 11.1 Dashboard Pages, 11.2 Key Features (+99 more)

### Community 2 - "Viral Hook Optimization"
Cohesion: 0.06
Nodes (39): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Path, setup_db(), test_cooldown_tracking() (+31 more)

### Community 3 - "Playwright CLI Reference (playwright-cli)"
Cohesion: 0.04
Nodes (57): --submit presses Enter after filling the element, Browser Automation with playwright-cli, Browser Sessions, Close all browsers, close the browser, Commands, Connect to a running browser via CDP endpoint, Connect to a running Chrome or Edge by channel name (+49 more)

### Community 4 - "KOL Sniper & Reply Engine"
Cohesion: 0.06
Nodes (39): API_PROVIDERS, CONTEXT_OPTIONS, Dashboard(), getAvatarUrl(), JobModelSelector(), AudienceNetworkTab(), Changelog, GraphLink (+31 more)

### Community 5 - "Playwright CLI Reference (references)"
Cohesion: 0.04
Nodes (53): 1. Name Browser Sessions Semantically, 2. Always Clean Up, 3. Delete Stale Browser Data, A/B Testing Sessions, Attach by channel name, Attach to Chrome, Attach to Chrome Canary, Attach to Edge Dev (+45 more)

### Community 6 - "Trend Radar & Generation"
Cohesion: 0.09
Nodes (48): irrelevant_trend_item(), asyncio, fixture, Tests Pydantic validation and field constraints on TrendEvaluation., Tests removing markdown code fences from LLM responses., Tests parsing trend evaluation from various JSON formats., Tests successful structured parse and hook optimization on relevant trend item., Tests that irrelevant news items return is_relevant=False and do NOT call hook… (+40 more)

### Community 7 - "Playwright CLI Reference (actions)"
Cohesion: 0.11
Nodes (35): Page, Executes poll creation on X: 1. Opens compose modal or navigates to…, human_scroll_to_tweet(), _navigate_home_if_needed(), _post_action_cooldown_browse(), Any, Page, _random_tab_detour() (+27 more)

### Community 8 - "Playwright CLI Reference (references)"
Cohesion: 0.04
Nodes (48): ... later, in a new session ..., Advanced: Multiple Cookies or Custom Options, Advanced: Multiple Operations, Already logged in!, Authentication State Reuse, Basic cookie, Clear All Cookies, Clear All localStorage (+40 more)

### Community 9 - "Viral Poll Creation & Actions"
Cohesion: 0.11
Nodes (37): asyncio, Path, Executes and validates the complete library of browser actions against the…, test_x_actions_integration(), BaseAction, Base action class providing failure recovery, logging, and screenshot tools., Browser action for checking a user's profile and extracting their latest tweet., CreatePoll (+29 more)

### Community 10 - "Trend Radar & Generation"
Cohesion: 0.09
Nodes (41): Scrapes the list of followers or following handles for a given user., ScrapeFollowList, broadcast_session_log(), check_schedules(), check_trend_radar(), collect_analytics_snapshot(), _collect_analytics_snapshot_async(), _extract_or_generate_poll_data() (+33 more)

### Community 11 - "Playwright CLI Reference (references)"
Cohesion: 0.05
Nodes (41): Clear geolocation override, Clipboard, Complex Workflows, Running Code, Emulate dark color scheme, Emulate light color scheme, Emulate print media, Emulate reduced motion (+33 more)

### Community 12 - "Playwright CLI Reference (references)"
Cohesion: 0.05
Nodes (41): 0. How generation works, 1.1 Prerequisite: workspace, 1.2 Prerequisite: seed test, 1.3 Explore the app, 1.4 Write the spec file, 1. <Group Name>, 1. Planning, 2.1 Inputs (+33 more)

### Community 13 - "Viral Poll Creation & Actions"
Cohesion: 0.10
Nodes (37): asyncio, Tests removing markdown code fences., Tests parsing poll from various JSON structures., Tests successful structured parse via OpenAI beta endpoint., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests that options exceeding 25 characters are safely truncated to 25 chars., Tests that network or API exceptions return a high-quality default fallback…, Tests that unparseable JSON response returns a safe fallback poll. (+29 more)

### Community 14 - "Database Schema & ORM Models"
Cohesion: 0.08
Nodes (23): configure_db_override(), create_tables(), drop_tables(), override_get_db(), AsyncSession, fixture, Override database dependency to use test database., Configure dependency override for the duration of the test module. (+15 more)

### Community 15 - "Trend Radar & Generation"
Cohesion: 0.13
Nodes (35): asyncio, test_fetch_atom_1_0_parsing(), test_fetch_rss_2_0_parsing(), test_fetch_rss_trends_default_client(), test_http_status_error_resilience(), test_keyword_filtering(), test_malformed_xml_resilience(), test_max_items_per_feed() (+27 more)

### Community 16 - "Database Schema & ORM Models"
Cohesion: 0.17
Nodes (24): Run migrations in 'offline' mode., run_migrations_offline(), db_session(), fixture, setup_db(), populate_profile_files(), asyncio, Path (+16 more)

### Community 17 - "Dashboard UI (dashboard)"
Cohesion: 0.06
Nodes (34): dependencies, lucide-react, next, react, react-dom, devDependencies, eslint, eslint-config-next (+26 more)

### Community 18 - "KOL Sniper & Reply Engine"
Cohesion: 0.12
Nodes (31): populate_profile_files(), asyncio, AsyncSession, Path, test_content_generator_with_retries(), test_engagement_evaluator_heuristics_and_llm(), test_post_session_processor(), test_session_planning_success() (+23 more)

### Community 19 - "KOL Sniper & Reply Engine"
Cohesion: 0.14
Nodes (31): asyncio, Tests fallback to chat.completions.create with JSON parsing when structured…, Tests fallback when response is plain unformatted text (not JSON)., Tests that various angles (witty, data, contrarian, framework, insight) are…, Tests that when preferred_angle is None, prompt instructs auto-selection among…, Tests that complete LLM failure returns a safe fallback SniperReplyResult…, Tests that when client is None, get_ai_client() is invoked., Tests that excessively long replies (> 280 chars) are trimmed to 280 chars. (+23 more)

### Community 20 - "Viral Poll Creation & Actions"
Cohesion: 0.14
Nodes (31): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Verifies that ActionType and ContentType include POLL enum members., Verifies generate_tweet passes draft_tweet through optimize_post_hook and…, Verifies generate_tweet creates a draft tweet from LLM then runs hook… (+23 more)

### Community 21 - "KOL Sniper & Reply Engine"
Cohesion: 0.14
Nodes (28): test_strategy_reviewer(), Path, test_diary_manager(), test_memory_manager(), test_persona_with_target_kols(), test_yaml_loader_and_saver(), AsyncSession, BaseModel (+20 more)

### Community 22 - "Dashboard UI (dashboard)"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 23 - "Playwright CLI Reference (references)"
Cohesion: 0.07
Nodes (28): 1. Start Tracing Before the Problem, 2. Clean Up Old Traces, ... all steps leading to the issue ..., `resources/`, `trace-{timestamp}.network`, `trace-{timestamp}.trace`, Analyzing Performance, Basic Usage (+20 more)

### Community 24 - "Trend Radar & Generation"
Cohesion: 0.21
Nodes (26): fixture, sample_persona(), sample_tweet(), fixture, sample_persona(), fixture, sample_persona(), sample_persona() (+18 more)

### Community 25 - "KOL Sniper & Reply Engine"
Cohesion: 0.09
Nodes (16): asyncio, Verifies BrowserManager startup, Redis-based locking, context creation, and…, test_browser_manager_flow(), BrowserManager, Releases the execution lock for a profile., Manages Playwright browser automation contexts and anti-detection settings.…, Stops the Playwright driver., Acquires a lock in Redis to prevent multiple workers from running the same… (+8 more)

### Community 26 - "Browser Auth & Profile Sync"
Cohesion: 0.11
Nodes (24): asyncio, Path, Tests count parsing helper function across various formats., Tests avatar URL upgrade helper function to 400x400., Tests extracting profile metrics from an authenticated session., Tests extracting profile metrics from a logged-out guest session., Tests detecting access/login challenge screen., Tests that HTTP 404 or network errors return status='failed' and capture… (+16 more)

### Community 27 - "KOL Sniper & Reply Engine"
Cohesion: 0.13
Nodes (22): asyncio, Path, Tests fallback to second tweet when the first tweet is pinned., Tests extracting the pinned tweet when no second tweet is available., Tests returning None when profile has no tweets., Tests returning None and capturing failure screenshot on navigation error., Tests extracting standard latest tweet from profile., test_check_user_latest_tweet_empty_profile() (+14 more)

### Community 28 - "Persona & Cognitive Memory Engine"
Cohesion: 0.22
Nodes (22): AsyncSession, BaseModel, ReflectionResponse, AccountRelationship, Config, CredentialsConfig, LearnedCharacteristics, LearnedDislikes (+14 more)

### Community 29 - "Browser Auth & Profile Sync"
Cohesion: 0.12
Nodes (22): Test parsing raw JSON object format., Test parsing full Playwright storage_state JSON string., Test parsing multiline newline-separated cookie string., Test format_storage_state generates standard Playwright storage state structure., Test empty, whitespace, and malformed inputs., Test format_storage_state includes twid when provided., Test parsing standard HTTP Cookie header string., Test parsing Cookie: header with quotes and spaces. (+14 more)

### Community 30 - "Browser Auth & Profile Sync"
Cohesion: 0.17
Nodes (18): configure_db_override(), create_tables(), create_test_profile(), drop_tables(), override_get_db(), AsyncSession, fixture, Path (+10 more)

### Community 31 - "Persona & Cognitive Memory Engine"
Cohesion: 0.14
Nodes (16): EngagementDecision, EngagementEvaluator, EngagementResponse, FollowDecision, FollowEvaluator, FollowResponse, Any, AsyncSession (+8 more)

### Community 32 - "Database Schema & ORM Models"
Cohesion: 0.11
Nodes (21): get_all_rate_limits(), get_system_config(), get_system_health(), get_system_models(), pause_entire_system(), Any, AsyncSession, BaseModel (+13 more)

### Community 33 - "Viral Hook Optimization"
Cohesion: 0.19
Nodes (18): _build_hook_optimizer_system_prompt(), _build_hook_optimizer_user_prompt(), clean_text_for_json(), _get_persona_field(), HookCandidate, _HookGenerationResponse, _normalize_candidate(), optimize_post_hook() (+10 more)

### Community 34 - "Persona & Cognitive Memory Engine"
Cohesion: 0.17
Nodes (10): MemoryManager, Any, Path, Appends a persistent high-importance memory., Retrieves a compiled list of memories based on recency, importance, and query.…, Manages episodic, semantic, and high-importance memories for a persona. Saves…, Appends a single JSON record to the specified file., Reads all JSON records from a JSONL file. (+2 more)

### Community 35 - "FastAPI REST Endpoints"
Cohesion: 0.18
Nodes (17): generate_ai_content(), GenerateContentRequest, get_content_detail(), list_profile_content(), Any, AsyncSession, BaseModel, get (+9 more)

### Community 36 - "Viral Hook Optimization"
Cohesion: 0.16
Nodes (15): asyncio, Tests successful structured parse with 4 archetypes and winning hook selection., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests JSON parsing when returned as a dict keyed by archetype name., Tests that LLM network or API exceptions return original content safely., Tests that invalid JSON response triggers safe fallback returning original…, Tests that when client=None, get_ai_client() is invoked., test_optimize_post_hook_api_exception_safe_fallback() (+7 more)

### Community 37 - "Playwright CLI Reference (references)"
Cohesion: 0.12
Nodes (16): 1. Use Descriptive Filenames, 2. Record entire hero scripts., Add a chapter marker for section transitions, Add another chapter, Basic Recording, Best Practices, Video Recording, Include context in filename (+8 more)

### Community 38 - "Persona & Cognitive Memory Engine"
Cohesion: 0.23
Nodes (13): db_session(), asyncio, AsyncSession, fixture, Path, Creates and teardowns the test database structure., Yields a clean database session., setup_db() (+5 more)

### Community 39 - "Browser Auth & Profile Sync"
Cohesion: 0.17
Nodes (15): Path, Test inspect_profile_auth_status when storage_state.json does not exist., Test inspect_profile_auth_status with valid active storage_state.json., Test inspect_profile_auth_status with only auth_token present., Test inspect_profile_auth_status with expired cookies., Test inspect_profile_auth_status when storage_state.json is malformed., test_inspect_profile_auth_status_authenticated(), test_inspect_profile_auth_status_corrupt_file() (+7 more)

### Community 40 - "Trend Radar & Generation"
Cohesion: 0.21
Nodes (15): db_session(), asyncio, AsyncSession, Tests active profile fetches trends, evaluates relevance, stages Content…, Tests that previously seen trend items are skipped and not re-evaluated., Tests that items deemed irrelevant by LLM are cached in Redis but not staged as…, Tests that a failure in one profile (e.g. corrupted persona) does not halt…, Tests that custom trend_sources in persona are passed to fetch_rss_trends. (+7 more)

### Community 41 - "Database Schema & ORM Models"
Cohesion: 0.21
Nodes (12): plan_session(), PlannedAction, Any, AsyncSession, BaseModel, datetime, Assembles context, constructs planning prompts, calls the primary LLM, and…, SessionPlan (+4 more)

### Community 42 - "Browser Session & Lock Manager"
Cohesion: 0.15
Nodes (12): BrowserContext, Creates or retrieves a persistent browser context for the profile. Picks a…, Starts the Playwright driver., apply_stealth(), apply_stealth_to_context(), _build_stealth_script(), BrowserContext, Page (+4 more)

### Community 43 - "Playwright CLI Reference (references)"
Cohesion: 0.13
Nodes (15): Advanced Mocking with run-code, CLI Route Commands, Conditional Response Based on Request, Delayed Response, Request Mocking, List active routes, Mock with custom headers, Mock with custom status (+7 more)

### Community 44 - "Persona & Cognitive Memory Engine"
Cohesion: 0.16
Nodes (8): AsyncSession, UUID, Runs the post-session diary updates and memory extraction operations., DiaryManager, Path, Manages daily diary entries ("inner monologue") for personas. Stores logs in…, Appends a structured session entry to the daily diary markdown file. Auto-…, Retrieves the last `limit` diary entries, sorted from newest to oldest. Returns…

### Community 45 - "Twitter / X Browser Automation"
Cohesion: 0.18
Nodes (9): home_feed(), profile_page(), get, Runs the mock FastAPI application inside a background thread., search_results(), ThreadedUvicorn, mock_x_server(), fixture (+1 more)

### Community 46 - "Viral Hook Optimization"
Cohesion: 0.19
Nodes (12): Tests cleaning archetype prefixes and long strings., Tests body preservation and micro-spacing in format_optimized_post., Tests format_optimized_post with a single line draft., Tests Pydantic validation on HookCandidate., test_clean_hook_text(), test_format_optimized_post_body_preservation(), test_format_optimized_post_single_line(), test_hook_candidate_model_validation() (+4 more)

### Community 47 - "Viral Poll Creation & Actions"
Cohesion: 0.26
Nodes (12): asyncio, Path, Tests creating a standard 2-option poll., Tests creating a 4-option poll with multiple extra choices added., Tests creating a 3-option poll with 1 extra choice., Tests navigating to compose post URL if textarea is not already on page., Tests that execution errors gracefully return False and capture failure…, test_create_poll_2_options_success() (+4 more)

### Community 48 - "Superpowers Specs & Plans"
Cohesion: 0.26
Nodes (13): get_session_actions(), get_session_detail(), list_profile_sessions(), Any, AsyncSession, get, post, UUID (+5 more)

### Community 49 - "Trend Radar & Generation"
Cohesion: 0.36
Nodes (12): load_persona(), Loads persona.yaml from the given profile directory or direct file path., main(), Profile, End-to-End User Experience Verification Script for XBot. Simulates the complete…, verify_api_and_db_integration(), verify_kol_sniper_flow(), verify_poll_generator() (+4 more)

### Community 50 - "Viral Hook Optimization"
Cohesion: 0.15
Nodes (13): 1. Initialize the Environment, 2. Startup Backend Service (FastAPI), 3. Launch Celery Worker & Beat Scheduler, 4. Launch Next.js Dashboard UI, 🛠 Project Structure, 🚀 Quick Start & Launch Runbook, 🧪 Running Tests, 🛡 Safety Guard & Webhook Alerting (+5 more)

### Community 51 - "Persona & Cognitive Memory Engine"
Cohesion: 0.18
Nodes (8): AssembledContext, AsyncSession, BaseModel, datetime, Helper to dump Strategy model to YAML string., Gathers files and database records to construct an AssembledContext for the…, Helper to format the Persona object into a markdown character sheet., Renders the user prompt context following the structure defined in…

### Community 52 - "Persona & Cognitive Memory Engine"
Cohesion: 0.23
Nodes (9): ExtractedMemoriesResponse, ExtractedMemory, GeneratedDiaryEntry, GeneratedDiaryResponse, PostSessionProcessor, BaseModel, Implements Phase 2.5 Post-Session Processing. Evaluates session execution…, Evaluates recent session logs, episodic memories, and content performance to… (+1 more)

### Community 53 - "Database Schema & ORM Models"
Cohesion: 0.17
Nodes (12): 2026-06-18: Initial Architecture Mapping, DEC-001: Backend Framework Choice, DEC-002: Project Init using `uv`, DEC-003: Strict Linting and Type Checking Configuration, DEC-004: Rename Virtual Environment to `.venv`, DEC-005: Switch Database from PostgreSQL to SQLite, DEC-006: Utilize Host Native Redis and External LiteLLM, DEC-011: Local Mock X Server for Browser Automation (+4 more)

### Community 54 - "Twitter / X Browser Automation"
Cohesion: 0.24
Nodes (8): AnalyticsRequest, get_free_analytics(), Any, BaseModel, post, On-demand free analytics scraper that mirrors tools like…, Scrapes recent tweets of a profile to calculate engagement metrics., ScrapeProfileTweets

### Community 55 - "Viral Poll Creation & Actions"
Cohesion: 0.24
Nodes (7): get_ai_client(), Any, Generates a Native X poll tailored to the persona's voice and niche. Enforces…, analyze_sentiment_llm(), analyze_sentiment_rules(), Performs offline, fast rule-based sentiment classification on input text., Performs sentiment analysis using the fast LiteLLM model.

### Community 56 - "Persona & Cognitive Memory Engine"
Cohesion: 0.20
Nodes (10): Project Status, Overall Status, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening (+2 more)

### Community 57 - "Client Engine"
Cohesion: 0.22
Nodes (5): Beta, BetaChat, Chat, A smart facade for AsyncOpenAI that dynamically routes requests to the correct…, RoutingClient

### Community 58 - "Database Schema & ORM Models"
Cohesion: 0.31
Nodes (4): Any, SafeContentStatus, SafeContentType, TypeDecorator

### Community 59 - "Playwright CLI Reference (references)"
Cohesion: 0.22
Nodes (9): ..., ... debugging instructions for "tw-abcdef" session ..., Attach to the test, Debugging Playwright Tests, Playwright Tests, Run all tests, Run all tests through a custom npm script, Run the test (+1 more)

### Community 60 - "Persona & Cognitive Memory Engine"
Cohesion: 0.22
Nodes (9): Active Task, Tasks, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening (+1 more)

### Community 61 - "Client Engine"
Cohesion: 0.43
Nodes (3): AsyncOpenAI, Completions, Any

### Community 62 - "Database Schema & ORM Models"
Cohesion: 0.25
Nodes (8): configure_db_override(), create_tables(), drop_tables(), override_get_db(), AsyncSession, fixture, Configure dependency override for the duration of the test module., setup_database()

### Community 63 - "KOL Sniper & Reply Engine"
Cohesion: 0.25
Nodes (8): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.3 Sniper Angle & Response Engine (`xbot/ai/sniper.py`), 3.5 Periodic Task Runner (`xbot/tasks.py`), 3. Detailed Component Specifications, 4. Error Handling & Edge Cases, 5. Verification & Testing Plan, 2026 08 18 Kol Sniper Reply Design

### Community 64 - "Viral Poll Creation & Actions"
Cohesion: 0.25
Nodes (8): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Hook Optimization Engine (`xbot/ai/hook_optimizer.py`), 3.2 Poll Generation Engine (`xbot/ai/poll_generator.py`), 3. Detailed Component Specifications, 4. Integration into Session Planner & Content Pipeline, 5. Testing & Verification, 2026 08 18 Viral Hook And Poll Design

### Community 65 - "Viral Poll Creation & Actions"
Cohesion: 0.25
Nodes (8): 1. Overview & Objectives, 2. Changes Made, 3. Verification & Test Results, Archetypes Implemented:, Task 1 Report, Files Created / Modified:, Status: COMPLETE, Task 1 Report: Viral Hook Multi-Generator & Evaluator

### Community 66 - "Viral Poll Creation & Actions"
Cohesion: 0.25
Nodes (8): 1. Overview & Objectives, 2. Files Modified & Created, 3. Verification & Test Results, 4. Git Commit, Task 4 Report, Full Unit & Integration Test Suite, Key Accomplishments, Targeted Integration Tests

### Community 67 - "Generator Engine"
Cohesion: 0.29
Nodes (6): calculate_similarity(), clean_text_for_json(), AsyncSession, Calculates similarity ratio between two strings using difflib., Clean markdown json wrap., Generates content, validates it, and handles automatic regeneration on failure…

### Community 68 - "Playwright CLI Reference (references)"
Cohesion: 0.29
Nodes (7): Element Attributes, Examples, get a computed style property, get a specific attribute, get all CSS classes, get the element's id, Inspecting Element Attributes

### Community 69 - "Trend Radar & Generation"
Cohesion: 0.29
Nodes (7): 1. Executive Summary & Objective, 2. Architecture & Data Flow, 3.1 Feed & Trend Ingestion Layer (`xbot/ai/trend_radar.py`), 3.3 Celery Periodic Task & Queue Routing (`xbot/tasks.py`), 3. Detailed Component Specifications, 4. Verification & Testing, 2026 08 18 Trend Radar Design

### Community 70 - "Superpowers Specs & Plans"
Cohesion: 0.33
Nodes (6): 1. Executive Summary, 2. Architecture & Data Flow, 3.3 REST Endpoints (`backend/xbot/api/profiles.py`), 3. Component Specifications, 4. Verification & Testing, 2026 08 18 Profile Auth And Metrics Sync Design

### Community 71 - "KOL Sniper & Reply Engine"
Cohesion: 0.33
Nodes (6): Changes Made, Task 3 Report, Git Commit, Overview, Task 3 Report: Build AI Sniper Angle & Response Generator, Test Verification

### Community 72 - "Superpowers Specs & Plans"
Cohesion: 0.33
Nodes (6): 1. Summary of Changes, 2. Test Verification, 3. Next Steps, Task 1 Report, Files Created/Modified, Task 1 Report: Cookie Converter & Auth State Engine

### Community 73 - "Env Engine"
Cohesion: 0.40
Nodes (5): do_run_migrations(), Any, Helper method to run migrations synchronously., Run migrations in 'online' mode using async engine., run_migrations_online()

### Community 74 - "FastAPI REST Endpoints"
Cohesion: 0.40
Nodes (5): Streams real-time updates for a single session execution., Streams live session updates system-wide., websocket_live_global_logs(), websocket_session_logs(), websocket

### Community 75 - "Main Engine"
Cohesion: 0.40
Nodes (5): health_check(), Any, get, Health check endpoint returning system status., root()

### Community 76 - "KOL Sniper & Reply Engine"
Cohesion: 0.40
Nodes (5): 2026 08 18 Kol Sniper Reply Plan, Global Constraints, Plan Verification & Self-Review Checklist, Task 1: Extend Persona Model and Schema with Target KOLs, Task 3: Build AI Sniper Angle & Response Generator

### Community 77 - "Viral Poll Creation & Actions"
Cohesion: 0.40
Nodes (5): 2026 08 18 Viral Hook And Poll Plan, Global Constraints, Task 1: Build the Viral Hook Optimizer & Scorer, Task 2: Build the AI Poll Generator, Task 3: Implement `CreatePoll` Playwright Browser Action

### Community 78 - "KOL Sniper & Reply Engine"
Cohesion: 0.40
Nodes (5): Changes Made, Task 1 Report, Git Commit, Overview, Test Verification

### Community 79 - "KOL Sniper & Reply Engine"
Cohesion: 0.40
Nodes (5): Changes Made, Task 2 Report, Git Commit, Overview, Test Verification

### Community 80 - "KOL Sniper & Reply Engine"
Cohesion: 0.40
Nodes (5): Changes Made, Task 4 Report, Git Commit, Overview, Test Verification

### Community 81 - "Superpowers Specs & Plans"
Cohesion: 0.40
Nodes (5): 1. Summary of Changes, 2. Test Verification, 3. Git Commit, Created & Modified Files, Task 2 Report

### Community 82 - "Trend Radar & Generation"
Cohesion: 0.40
Nodes (5): 1. Summary of Changes, 2. Test Execution Results, 3. Git Commit, Task 1 Report, Task 1 Report: Real-Time Trend Radar Ingestion Engine

### Community 83 - "Viral Poll Creation & Actions"
Cohesion: 0.40
Nodes (5): 1. Overview & Objectives, 2. Changes Made, 3. Verification & Test Results, Task 2 Report, Task 2 Report: AI Poll Generator Implementation

### Community 84 - "Viral Poll Creation & Actions"
Cohesion: 0.40
Nodes (5): Commit, Task 3 Report, Implementation Summary, Task 3 Report: CreatePoll Playwright Browser Action, Verification Evidence

### Community 86 - "Dashboard UI (dashboard)"
Cohesion: 0.50
Nodes (4): Deploy on Vercel, Readme, Getting Started, Learn More

### Community 88 - "KOL Sniper & Reply Engine"
Cohesion: 0.50
Nodes (4): Progress, Pre-flight Conflict Scan, Task Status, Verification Status

### Community 89 - "Superpowers Specs & Plans"
Cohesion: 0.50
Nodes (4): 1. Summary of Changes, 2. Test Coverage & Verification, Task 3 Report, Pytest Results

### Community 90 - "Trend Radar & Generation"
Cohesion: 0.50
Nodes (4): Progress, Pre-flight Conflict Scan, Task Status, Verification Status

### Community 91 - "Trend Radar & Generation"
Cohesion: 0.50
Nodes (4): 1. Overview & Key Deliverables, 2. Test Coverage & Verification, 3. Git Commit, Task 2 Report

### Community 92 - "Trend Radar & Generation"
Cohesion: 0.50
Nodes (4): 1. Summary of Changes, 2. Verification Results, 3. Git Commit, Task 3 Report

### Community 93 - "Viral Poll Creation & Actions"
Cohesion: 0.50
Nodes (4): Progress, Pre-flight Conflict Scan, Task Status, Verification Status

### Community 98 - "Trend Radar & Generation"
Cohesion: 0.67
Nodes (3): 2026 08 18 Trend Radar Plan, Global Constraints, Task 1: Build the Trend Radar Ingestion Engine

### Community 99 - "2026-06-29 Engine"
Cohesion: 0.67
Nodes (3): 2026 06 29, Memory Log - June 29, 2026, Work Accomplished

### Community 100 - "2026-06-30 Engine"
Cohesion: 0.67
Nodes (3): 2026 06 30, Memory Log - June 30, 2026, Work Accomplished

### Community 101 - "Superpowers Specs & Plans"
Cohesion: 0.67
Nodes (3): Progress, Pre-flight Conflict Scan, Task Status

### Community 102 - "Superpowers Specs & Plans"
Cohesion: 0.67
Nodes (3): Changes Summary, Task 4 Report, Status: COMPLETE

## Knowledge Gaps
- **647 isolated node(s):** `xbot`, `backup.sh script`, `eslintConfig`, `nextConfig`, `name` (+642 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Browser Auth & Profile Sync` to `Viral Hook Optimization`, `Viral Poll Creation & Actions`, `Trend Radar & Generation`, `Database Schema & ORM Models`, `Trend Radar & Generation`, `Database Schema & ORM Models`, `KOL Sniper & Reply Engine`, `Viral Poll Creation & Actions`, `KOL Sniper & Reply Engine`, `Trend Radar & Generation`, `Persona & Cognitive Memory Engine`, `Browser Auth & Profile Sync`, `Persona & Cognitive Memory Engine`, `Database Schema & ORM Models`, `FastAPI REST Endpoints`, `Persona & Cognitive Memory Engine`, `Trend Radar & Generation`, `Database Schema & ORM Models`, `Trend Radar & Generation`, `Persona & Cognitive Memory Engine`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `get_ai_client()` connect `Viral Poll Creation & Actions` to `Browser Auth & Profile Sync`, `Trend Radar & Generation`, `Trend Radar & Generation`, `Viral Poll Creation & Actions`, `Database Schema & ORM Models`, `Database Schema & ORM Models`, `KOL Sniper & Reply Engine`, `Viral Poll Creation & Actions`, `KOL Sniper & Reply Engine`, `Persona & Cognitive Memory Engine`, `Persona & Cognitive Memory Engine`, `Viral Hook Optimization`, `Viral Hook Optimization`, `Database Schema & ORM Models`, `Persona & Cognitive Memory Engine`, `Persona & Cognitive Memory Engine`, `Client Engine`, `Client Engine`, `Generator Engine`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `SyncProfileFromX` connect `Viral Poll Creation & Actions` to `Browser Auth & Profile Sync`, `Browser Auth & Profile Sync`, `Trend Radar & Generation`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 99 inferred relationships involving `Profile` (e.g. with `test_assembler_missing_directory()` and `test_assembler_success()`) actually correct?**
  _`Profile` has 99 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `Persona` (e.g. with `test_generate_sniper_reply_angles_and_prompts()` and `test_generate_sniper_reply_auto_angle_selection()`) actually correct?**
  _`Persona` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `ProfileStatus` (e.g. with `test_assembler_missing_directory()` and `test_assembler_success()`) actually correct?**
  _`ProfileStatus` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `xbot`, `backup.sh script`, `eslintConfig` to the rest of the system?**
  _647 weakly-connected nodes found - possible documentation gaps or missing edges._