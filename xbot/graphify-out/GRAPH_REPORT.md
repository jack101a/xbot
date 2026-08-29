# Graph Report - xbot  (2026-08-28)

## Corpus Check
- 306 files · ~714,931 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3292 nodes · 7969 edges · 192 communities (165 shown, 27 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 905 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5e1effc2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_x_actions.py
- Master Plan
- formatting_engine.py
- Skill
- page.tsx
- Session Management
- test_trend_generator.py
- sleep_with_jitter
- Storage State
- _run_session_async
- trend_generator_pipeline.py
- Running Code
- Test Generation
- get_all_rate_limits
- trend_radar.py
- generate_sniper_reply
- models/profile.py
- devDependencies
- test_trend_task.py
- Persona
- ProfileStatus
- loader.py
- compilerOptions
- Tracing
- _build_clean_creator_prompt
- manager.py
- test_sync_profile_action.py
- test_sniper_browser_action.py
- CentralGuard
- test_profile_auth.py
- test_profile_auth_api.py
- engagement.py
- database.py
- SafetyGuard
- ._append_to_jsonl
- generate_ai_content
- run_follow_pipeline_for_profile
- Video Recording
- tasks.py
- score_tweet_opportunity
- Technical Specification: XBot Autonomous AI Persona Platform & UI Modernization
- inspect_profile_auth_status
- ai/__init__.py
- Request Mocking
- schemas/profile.py
- mock_x_server.py
- Global Constraints
- test_poll_browser_action.py
- get_session_actions
- test_nvidia_image.py
- Readme
- test_safety_and_scheduling.py
- tools.py
- Decisions
- ground_context_with_live_facts
- quote_pipeline.py
- Project Status
- AntiAIGatekeeper
- Any
- Playwright Tests
- Tasks
- Profile
- .execute
- 2026 08 18 Kol Sniper Reply Design
- 2026 08 18 Viral Hook And Poll Design
- Task 1 Report
- Task 4 Report
- test_opportunity_radar.py
- Element Attributes
- 2026 08 18 Trend Radar Design
- 2026 08 18 Profile Auth And Metrics Sync Design
- Task 3 Report
- Task 1 Report
- env.py
- load_persona
- get_all_pipelines_status
- 2026 08 18 Kol Sniper Reply Plan
- 2026 08 18 Viral Hook And Poll Plan
- Task 1 Report
- Task 2 Report
- Task 4 Report
- Task 2 Report
- Task 1 Report
- Task 2 Report
- Task 3 Report
- test_f4f_growth.py
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
- trend_generator.py
- backup.sh
- Agents
- eslint.config.mjs
- next.config.ts
- postcss.config.mjs
- 2026 08 18 Profile Auth And Metrics Sync Plan
- generate_poll
- test_visual_engine.py
- ViralTweet
- RoutingClient
- campaigns.py
- e2e_full_user_experience.py
- test_reflection_learning.py
- trend_researcher_pipeline.py
- Design Spec: Natural Content Diversity & Context-Aware Reply Engine
- on_demand_campaign_pipeline.py
- verify_sniper_reply
- SimClusterTopicScorer
- Readme
- Proposed Changes
- test_sniper_check_targets_executes_reply_and_records_db
- Litellm Config
- Claude
- guard.py
- test_ai_decision_system.py
- meme_renderer.py
- Docker Compose
- e2e_authenticated_session_test.py
- evaluate_content_safety
- hook_optimizer.py
- Implementation Details
- xbot
- TrendItem
- Task 1 Report: Algorithmic Opportunity & Growth Scorer
- Task 2 Report: "Value-First + Debate Catalyst" Sniper Reply Upgrades
- e2e_automation_safety_validation.py
- Task 5 Report: Browser Action Native GIF Search & File Upload Automation
- VerificationReport
- Task 4 Report: Bookmark-Bait & Open-Loop Hook Optimizer
- purge_live_x_account.py
- scheduler.py
- TestReportCollector
- xbot.sh
- Global Constraints
- Global Constraints
- test_x_actions_context.py
- XBot Pro UI/UX Redesign: The Command Center
- Deliverables & Changes
- Global Constraints
- Implementation Report: Task 5 — 1st-Reply Link Injection & Execution Loop Integration
- plan_campaign_from_prompt
- SDD ledger — plan: docs/superpowers/plans/2026-08-25-algorithmic-growth-and-visual-engine.md
- Task 2 Brief: AI Room-Reader & Dynamic Reply Generator with 6 Modalities
- Task 1 Brief: Multi-Modal Target Context Scraper & Payload Builder
- Task 1 Completion Report: Multi-Modal Target Context Scraper & Payload Builder
- restart.sh
- start.sh
- status.sh
- stop.sh
- task-1-brief.md
- task-2-brief.md
- task-3-brief.md
- task-4-brief.md
- task-5-brief.md
- Deliverables & Changes
- .assemble
- Task 3 Brief: Context-Enriched Reply Pipeline & Feed/KOL Integration
- Task 4 Brief: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)
- Task 5 Brief: Browser Action Native GIF Search & File Upload Automation
- Global Constraints
- explore_follow_back_ecosystem.py
- SDD Ledger: Natural Content Diversity & Context-Aware Reply Engine
- health_check
- Task 4 Report: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)
- like_pipeline.py
- GrowthEngineTestReport
- mock_live_fact_grounding
- stealth.py
- analyze_sentiment_llm
- ScrapeProfileMetrics

## God Nodes (most connected - your core abstractions)
1. `Profile` - 241 edges
2. `Persona` - 133 edges
3. `ProfileStatus` - 123 edges
4. `Master Plan` - 106 edges
5. `_run_session_async()` - 66 edges
6. `BrowserManager` - 60 edges
7. `load_persona()` - 56 edges
8. `Skill` - 56 edges
9. `Session Management` - 52 edges
10. `get_ai_client()` - 51 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_browser_auth.py → backend/xbot/browser/manager.py
- `main()` --uses--> `BrowserManager`  [INFERRED]
  test-script/diag_follow_selectors.py → backend/xbot/browser/manager.py
- `inspect()` --uses--> `BrowserManager`  [INFERRED]
  test-script/inspect_x_dom.py → backend/xbot/browser/manager.py
- `run_verification()` --uses--> `AntiAIGatekeeper`  [INFERRED]
  test-script/verify_anti_ai_and_threads.py → backend/xbot/ai/anti_ai_gatekeeper.py
- `test_dynamic_session_planning()` --uses--> `ContextAssembler`  [INFERRED]
  test-script/e2e_automation_safety_validation.py → backend/xbot/ai/assembler.py

## Import Cycles
- None detected.

## Communities (192 total, 27 thin omitted)

### Community 0 - "test_x_actions.py"
Cohesion: 0.13
Nodes (26): asyncio, Path, Test _attach_gif_if_requested successfully opens picker, searches, and selects…, Test _attach_gif_if_requested returns False immediately when query is None or…, Test _attach_gif_if_requested gracefully returns False when GIF search button…, Test _attach_gif_if_requested gracefully returns False when GIF search input…, Test _attach_gif_if_requested gracefully returns False when search box exists…, Test ComposePost successfully posts with attached GIF. (+18 more)

### Community 1 - "Master Plan"
Cohesion: 0.02
Nodes (107): 10.1 Data Collection, 10.2 Analytics Snapshot Process, 10.3 Performance Scoring, 10.4 Strategy Engine (Weekly Review), 10.5 Monetization Tracking, 10. Analytics & Strategy Engine, 11.1 Dashboard Pages, 11.2 Key Features (+99 more)

### Community 2 - "formatting_engine.py"
Cohesion: 0.14
Nodes (28): test_archetype_registry_completeness(), test_enforce_length_cadence_micro(), test_enforce_pacing_whitespace(), test_post_process_formatted_content_full_pipeline(), test_preserve_clean_ending(), test_select_archetype_anti_monotony_cooldown(), test_select_archetype_keyword_contrast(), test_select_archetype_media_bias() (+20 more)

### Community 3 - "Skill"
Cohesion: 0.04
Nodes (57): --submit presses Enter after filling the element, Browser Automation with playwright-cli, Browser Sessions, Close all browsers, close the browser, Commands, Connect to a running browser via CDP endpoint, Connect to a running Chrome or Edge by channel name (+49 more)

### Community 4 - "page.tsx"
Cohesion: 0.06
Nodes (54): DashboardPage(), BottomConsole(), ActionItem, CommandPalette(), DesktopSidebar(), DesktopTopBar(), MobileHeader(), MobileNavigation() (+46 more)

### Community 5 - "Session Management"
Cohesion: 0.04
Nodes (53): 1. Name Browser Sessions Semantically, 2. Always Clean Up, 3. Delete Stale Browser Data, A/B Testing Sessions, Attach by channel name, Attach to Chrome, Attach to Chrome Canary, Attach to Edge Dev (+45 more)

### Community 6 - "test_trend_generator.py"
Cohesion: 0.16
Nodes (26): asyncio, Tests Pydantic validation and field constraints on TrendEvaluation., Tests successful structured parse and hook optimization on relevant trend item., Tests that irrelevant news items return is_relevant=False and do NOT call hook…, Tests fallback to chat.completions.create with JSON mode when structured parse…, Tests fallback to standard chat completions when json_object mode fails., Tests that network or API exceptions return a safe non-relevant fallback…, Tests that unparseable LLM output returns a safe non-relevant fallback. (+18 more)

### Community 7 - "sleep_with_jitter"
Cohesion: 0.08
Nodes (45): Page, Executes poll creation on X: 1. Opens compose modal or navigates to…, _attach_media_files(), check_target_tweet_status(), _extract_tweet_id_from_url(), human_scroll_to_tweet(), _navigate_home_if_needed(), _post_action_cooldown_browse() (+37 more)

### Community 8 - "Storage State"
Cohesion: 0.04
Nodes (48): ... later, in a new session ..., Advanced: Multiple Cookies or Custom Options, Advanced: Multiple Operations, Already logged in!, Authentication State Reuse, Basic cookie, Clear All Cookies, Clear All localStorage (+40 more)

### Community 9 - "_run_session_async"
Cohesion: 0.07
Nodes (62): Verify browser queue routes gif_query and media_paths to action executors., test_e2e_browser_queue_gif_and_media_routing(), Executes and validates the complete library of browser actions against the…, test_x_actions_integration(), approve_and_publish_draft(), Approves a staged draft post/poll/thread and publishes it to live X., BaseAction, Base action class providing failure recovery, logging, and screenshot tools. (+54 more)

### Community 10 - "trend_generator_pipeline.py"
Cohesion: 0.10
Nodes (41): asyncio, Comprehensive End-to-End Verification of New XBot Pipelines. Verifies: 1.…, Verify 4-way creation decision matrix (4:5 memes, media threads, polls, punchy…, Verify that scrape_target_tweet_context extracts root tweet, media, and top 10…, test_e2e_target_tweet_context_scraping(), test_e2e_trend_generator_4way_creation_matrix(), asyncio, test_determine_creation_format_matrix() (+33 more)

### Community 11 - "Running Code"
Cohesion: 0.05
Nodes (41): Clear geolocation override, Clipboard, Complex Workflows, Running Code, Emulate dark color scheme, Emulate light color scheme, Emulate print media, Emulate reduced motion (+33 more)

### Community 12 - "Test Generation"
Cohesion: 0.05
Nodes (41): 0. How generation works, 1.1 Prerequisite: workspace, 1.2 Prerequisite: seed test, 1.3 Explore the app, 1.4 Write the spec file, 1. <Group Name>, 1. Planning, 2.1 Inputs (+33 more)

### Community 13 - "get_all_rate_limits"
Cohesion: 0.11
Nodes (21): get_all_rate_limits(), get_system_config(), get_system_health(), get_system_models(), pause_entire_system(), Any, AsyncSession, BaseModel (+13 more)

### Community 14 - "trend_radar.py"
Cohesion: 0.28
Nodes (15): _clean_text(), fetch_multi_source_trends(), fetch_web_search_trends(), _find_child_by_tags(), _get_child_text(), _is_recent_timestamp(), _parse_atom_entry(), parse_feed_xml() (+7 more)

### Community 15 - "generate_sniper_reply"
Cohesion: 0.06
Nodes (59): asyncio, Tests all 6 dynamic reply modalities and schema validation., Tests DynamicReplyResult and SniperReplyResult aliases., Tests that leading and trailing quotes are stripped on model initialization., Tests that debate_catalyst is extracted only when a question mark is present., Tests that structured parse does NOT force '?' onto declarative replies., Tests that raw text fallback does NOT force '?' onto replies., Tests that short replies (<40 chars) like 'real', '💀', 'pure cinema' are… (+51 more)

### Community 16 - "models/profile.py"
Cohesion: 0.06
Nodes (62): configure_db_override(), drop_tables(), override_get_db(), populate_profile_files(), asyncio, AsyncSession, fixture, Path (+54 more)

### Community 17 - "devDependencies"
Cohesion: 0.05
Nodes (40): clsx, dependencies, clsx, lucide-react, next, react, react-dom, tailwind-merge (+32 more)

### Community 18 - "test_trend_task.py"
Cohesion: 0.14
Nodes (23): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Verifies that the periodic schedule for trend researcher pipeline is registered…, Tests active profile fetches trends, evaluates relevance, stages Content…, Tests that previously seen trend items are skipped and not re-evaluated. (+15 more)

### Community 19 - "Persona"
Cohesion: 0.14
Nodes (48): Tests that JSON fallback does NOT force '?' onto replies., Tests that system prompt includes 6 dynamic reply modalities and anti-cliché…, sample_persona(), test_build_sniper_system_prompt_6_modalities(), test_generate_sniper_reply_no_forced_question_json_fallback(), fixture, Unit Tests for CampaignPlanner (AI Director Intent Decomposer)., sample_persona() (+40 more)

### Community 20 - "ProfileStatus"
Cohesion: 0.06
Nodes (67): asyncio, fixture, sample_profile_with_actions(), test_get_profile_activities_time_filters(), test_get_profile_activities_type_and_search_filters(), db_session(), asyncio, AsyncSession (+59 more)

### Community 21 - "loader.py"
Cohesion: 0.11
Nodes (46): Path, test_diary_manager(), test_memory_manager(), test_persona_with_target_kols(), test_yaml_loader_and_saver(), Any, AsyncSession, AsyncSession (+38 more)

### Community 22 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 23 - "Tracing"
Cohesion: 0.07
Nodes (28): 1. Start Tracing Before the Problem, 2. Clean Up Old Traces, ... all steps leading to the issue ..., `resources/`, `trace-{timestamp}.network`, `trace-{timestamp}.trace`, Analyzing Performance, Basic Usage (+20 more)

### Community 24 - "_build_clean_creator_prompt"
Cohesion: 0.40
Nodes (5): Tests that prompt directives include <100 char open-loop hook, bookmark-bait,…, test_build_clean_creator_prompt_includes_open_loop_and_bookmark_directives(), test_build_clean_creator_prompt_strips_db_bloat(), _build_clean_creator_prompt(), Constructs a clean, high-signal, zero-bloat prompt for the heavy writing model.…

### Community 25 - "manager.py"
Cohesion: 0.10
Nodes (14): asyncio, Verifies BrowserManager startup, Redis-based locking, context creation, and…, test_browser_manager_flow(), main(), scrape_feed_posts(), scrape_tweet_comments(), Direct action diagnostic: test Post, Reply, Retweet, Follow with the real…, main() (+6 more)

### Community 26 - "test_sync_profile_action.py"
Cohesion: 0.11
Nodes (24): asyncio, Path, Tests count parsing helper function across various formats., Tests avatar URL upgrade helper function to 400x400., Tests extracting profile metrics from an authenticated session., Tests extracting profile metrics from a logged-out guest session., Tests detecting access/login challenge screen., Tests that HTTP 404 or network errors return status='failed' and capture… (+16 more)

### Community 27 - "test_sniper_browser_action.py"
Cohesion: 0.26
Nodes (12): asyncio, Path, Tests fallback to second tweet when the first tweet is pinned., Tests extracting the pinned tweet when no second tweet is available., Tests returning None when profile has no tweets., Tests returning None and capturing failure screenshot on navigation error., Tests extracting standard latest tweet from profile., test_check_user_latest_tweet_empty_profile() (+4 more)

### Community 28 - "CentralGuard"
Cohesion: 0.11
Nodes (23): asyncio, test_can_act_active_hours_and_safety_guard(), test_is_action_24_7(), test_is_within_active_hours(), test_ist_time_conversion(), test_record_action_and_daily_stats(), test_target_deduplication(), CentralGuard (+15 more)

### Community 29 - "test_profile_auth.py"
Cohesion: 0.11
Nodes (25): Test parsing raw JSON object format., Test parsing full Playwright storage_state JSON string., Test parsing multiline newline-separated cookie string., Test format_storage_state generates standard Playwright storage state structure., Test empty, whitespace, and malformed inputs., Test inspect_profile_auth_status with valid active storage_state.json., Test format_storage_state includes twid when provided., Test parsing standard HTTP Cookie header string. (+17 more)

### Community 30 - "test_profile_auth_api.py"
Cohesion: 0.17
Nodes (18): configure_db_override(), create_tables(), create_test_profile(), drop_tables(), override_get_db(), AsyncSession, fixture, Path (+10 more)

### Community 31 - "engagement.py"
Cohesion: 0.14
Nodes (16): EngagementDecision, EngagementEvaluator, EngagementResponse, FollowDecision, FollowEvaluator, FollowResponse, Any, AsyncSession (+8 more)

### Community 32 - "database.py"
Cohesion: 0.06
Nodes (42): asyncio, API Tests for Campaign Studio Endpoints., test_campaign_api_full_cycle(), asyncio, fixture, setup_database(), test_get_pipeline_status_endpoint(), test_trigger_pipeline_endpoint() (+34 more)

### Community 33 - "SafetyGuard"
Cohesion: 0.18
Nodes (10): AsyncSession, datetime, Runs safety check pipeline: DB status, active cooldowns, and sliding window…, Records the action success in rate limits and applies configured cooldowns., Implements Phase 3.3 (cooldowns, warm-ups, variance), Phase 3.4 (circuit…, Sends a synchronous JSON POST webhook payload to external alerts handler…, Processes failures. Checks for CAPTCHAs, account locking (health signals), 429…, Calculates account age and returns multiplier based on Section 9.5 Table. (+2 more)

### Community 34 - "._append_to_jsonl"
Cohesion: 0.16
Nodes (8): Any, Path, Appends a persistent high-importance memory., Retrieves a compiled list of memories based on recency, importance, and query.…, Appends a single JSON record to the specified file., Reads all JSON records from a JSONL file., Appends an episodic memory (events that happened)., Appends a semantic memory (things learned/facts).

### Community 35 - "generate_ai_content"
Cohesion: 0.18
Nodes (17): generate_ai_content(), GenerateContentRequest, get_content_detail(), list_profile_content(), Any, AsyncSession, BaseModel, get (+9 more)

### Community 36 - "run_follow_pipeline_for_profile"
Cohesion: 0.22
Nodes (12): asyncio, test_run_follow_pipeline_for_profile_skipped_by_guard(), test_run_follow_pipeline_lock_busy(), Any, AsyncSession, Profile, task, Celery task entry point for Follow Pipeline. (+4 more)

### Community 37 - "Video Recording"
Cohesion: 0.12
Nodes (16): 1. Use Descriptive Filenames, 2. Record entire hero scripts., Add a chapter marker for section transitions, Add another chapter, Basic Recording, Best Practices, Video Recording, Include context in filename (+8 more)

### Community 38 - "tasks.py"
Cohesion: 0.06
Nodes (62): Scrapes the list of followers or following handles for a given user, with…, ScrapeFollowList, BrowserManager, Releases the execution lock for a profile., Manages Playwright browser automation contexts and anti-detection settings.…, Stops the Playwright driver., Acquires a lock in Redis to prevent multiple workers from running the same…, load_config() (+54 more)

### Community 39 - "score_tweet_opportunity"
Cohesion: 0.08
Nodes (42): Tests integrating OpportunityScore from growth_scorer with sniper reply…, test_generate_sniper_reply_with_growth_opportunity_score(), Tests detection of F4F trains and ensuring quote_tweet recommendation is…, test_is_f4f_or_engagement_growth_post_detection(), Tests that tweets containing external links receive a 70% penalty (0.3x…, Tests OpportunityScore Pydantic model structure and validation., Tests that tweets older than 12h are strongly decayed and recommended to skip., Tests that candidate tweets with under 5k impressions are allowed for replies. (+34 more)

### Community 40 - "Technical Specification: XBot Autonomous AI Persona Platform & UI Modernization"
Cohesion: 0.20
Nodes (9): 1. Product Identity & Purpose, 2. Feature Inventory: Final Decisions, 3. System Architecture & Components, 4. Frontend Modularization (5-Tab Glassmorphic UI), 5. Implementation & Migration Steps, Central Tab Breakdown, Kept & Enhanced Features, Purged / Removed Features (+1 more)

### Community 41 - "inspect_profile_auth_status"
Cohesion: 0.19
Nodes (13): Path, Test inspect_profile_auth_status when storage_state.json does not exist., Test inspect_profile_auth_status with only auth_token present., Test inspect_profile_auth_status with expired cookies., Test inspect_profile_auth_status when storage_state.json is malformed., test_inspect_profile_auth_status_corrupt_file(), test_inspect_profile_auth_status_expired(), test_inspect_profile_auth_status_missing() (+5 more)

### Community 42 - "ai/__init__.py"
Cohesion: 0.10
Nodes (21): asyncio, Verifies generate_tweet passes draft_tweet through optimize_post_hook and…, Verifies generate_tweet creates a draft tweet from LLM then runs hook…, Verifies ContentGenerator.generate_poll generates validated Native X polls., test_content_generator_generate_poll(), test_content_generator_generate_tweet_with_existing_draft(), test_content_generator_generate_tweet_without_draft_generates_and_optimizes(), calculate_similarity() (+13 more)

### Community 43 - "Request Mocking"
Cohesion: 0.13
Nodes (15): Advanced Mocking with run-code, CLI Route Commands, Conditional Response Based on Request, Delayed Response, Request Mocking, List active routes, Mock with custom headers, Mock with custom status (+7 more)

### Community 44 - "schemas/profile.py"
Cohesion: 0.62
Nodes (5): ProfileBase, ProfileCreate, ProfileResponse, ProfileUpdate, BaseModel

### Community 45 - "mock_x_server.py"
Cohesion: 0.18
Nodes (9): home_feed(), profile_page(), get, Runs the mock FastAPI application inside a background thread., search_results(), ThreadedUvicorn, mock_x_server(), fixture (+1 more)

### Community 46 - "Global Constraints"
Cohesion: 0.25
Nodes (7): Global Constraints, Task 1: Repository Purge & Legacy Cleanup, Task 2: Backend API & WebSocket Hardening, Task 3: Dashboard API Client & Modular Sub-Components, Task 4: Streamline Dashboard Root Container (`page.tsx`), Task 5: End-to-End Verification & Knowledge Graph Update, XBot Architecture & UI Redesign Implementation Plan

### Community 47 - "test_poll_browser_action.py"
Cohesion: 0.26
Nodes (12): asyncio, Path, Tests creating a standard 2-option poll., Tests creating a 4-option poll with multiple extra choices added., Tests creating a 3-option poll with 1 extra choice., Tests navigating to compose post URL if textarea is not already on page., Tests that execution errors gracefully return False and capture failure…, test_create_poll_2_options_success() (+4 more)

### Community 48 - "get_session_actions"
Cohesion: 0.14
Nodes (21): test_normalize_event_payload(), get_session_actions(), get_session_detail(), list_profile_sessions(), normalize_event_payload(), Any, AsyncSession, get (+13 more)

### Community 49 - "test_nvidia_image.py"
Cohesion: 0.07
Nodes (47): asyncio, Verifies deterministic fallback generation across all archetypes., Verifies LLM-powered growth post generation and parsing., test_generate_fallback_growth_post(), test_generate_growth_post_spec_llm(), asyncio, Verifies extraction across multiple NVIDIA API response formats., Verifies successful asynchronous API call to NVIDIA GenAI. (+39 more)

### Community 50 - "Readme"
Cohesion: 0.15
Nodes (13): 1. Initialize the Environment, 2. Startup Backend Service (FastAPI), 3. Launch Celery Worker & Beat Scheduler, 4. Launch Next.js Dashboard UI, 🛠 Project Structure, 🚀 Quick Start & Launch Runbook, 🧪 Running Tests, 🛡 Safety Guard & Webhook Alerting (+5 more)

### Community 51 - "test_safety_and_scheduling.py"
Cohesion: 0.27
Nodes (11): clean_redis(), db_session(), asyncio, AsyncSession, fixture, Path, setup_db(), test_generate_daily_schedule() (+3 more)

### Community 52 - "tools.py"
Cohesion: 0.21
Nodes (22): api_generate_thread(), api_research_topic(), create_interactive_poll(), create_optimized_hook(), create_sniper_reply(), HookOptimizeRequest, PollGenerateRequest, Any (+14 more)

### Community 53 - "Decisions"
Cohesion: 0.17
Nodes (12): 2026-06-18: Initial Architecture Mapping, DEC-001: Backend Framework Choice, DEC-002: Project Init using `uv`, DEC-003: Strict Linting and Type Checking Configuration, DEC-004: Rename Virtual Environment to `.venv`, DEC-005: Switch Database from PostgreSQL to SQLite, DEC-006: Utilize Host Native Redis and External LiteLLM, DEC-011: Local Mock X Server for Browser Automation (+4 more)

### Community 54 - "ground_context_with_live_facts"
Cohesion: 0.26
Nodes (12): asyncio, test_extract_search_query(), test_ground_context_prompt_block(), test_search_web_grounding_live(), extract_search_query_from_text(), ground_context_with_live_facts(), _is_recent_date_str(), Extracts high-signal keywords and named entities from a tweet or trend text… (+4 more)

### Community 55 - "quote_pipeline.py"
Cohesion: 0.10
Nodes (37): asyncio, test_enqueue_and_pop_priority(), test_execute_browser_action_routing(), test_process_single_job_expired(), test_result_get_and_set(), BrowserJob, enqueue_browser_job(), get_browser_job_result() (+29 more)

### Community 56 - "Project Status"
Cohesion: 0.20
Nodes (10): Project Status, Overall Status, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening (+2 more)

### Community 57 - "AntiAIGatekeeper"
Cohesion: 0.14
Nodes (18): gatekeeper(), fixture, test_rejects_corporate_ai_buzzwords(), test_rejects_emoji_bullet_vomit(), test_rejects_formulaic_linkedin_ctas(), test_rejects_lazy_lowercase_whatsapp_sludge(), test_rejects_routine_beverage_filler(), test_remediate_minor_issues() (+10 more)

### Community 58 - "Any"
Cohesion: 0.31
Nodes (4): Any, SafeContentStatus, SafeContentType, TypeDecorator

### Community 59 - "Playwright Tests"
Cohesion: 0.22
Nodes (9): ..., ... debugging instructions for "tw-abcdef" session ..., Attach to the test, Debugging Playwright Tests, Playwright Tests, Run all tests, Run all tests through a custom npm script, Run the test (+1 more)

### Community 60 - "Tasks"
Cohesion: 0.22
Nodes (9): Active Task, Tasks, Phase 0: Foundation, Phase 1: Browser Engine + Persona, Phase 2: AI Brain, Phase 3: Scheduling & Safety, Phase 4: Analytics & Dashboard, Phase 5: Polish & Hardening (+1 more)

### Community 61 - "Profile"
Cohesion: 0.05
Nodes (120): approve_all_pending_drafts(), create_profile(), delete_profile(), dismiss_all_drafts(), dismiss_draft(), execute_f4f_batch_follow(), execute_f4f_follow(), F4FFollowRequest (+112 more)

### Community 62 - ".execute"
Cohesion: 0.22
Nodes (8): _extract_tweet_id_from_url(), Any, ElementHandle, Page, Navigates to a user's profile and extracts their latest tweet. Handles pinned…, Extract numeric tweet ID from a tweet URL., Determines if a tweet element is a pinned tweet., Extracts structured tweet dictionary from an ElementHandle.

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

### Community 67 - "test_opportunity_radar.py"
Cohesion: 0.12
Nodes (24): test_generate_daily_circadian_schedule_bounds(), test_is_within_active_session(), test_sleep_block_preservation(), test_arbitrage_score_calculation(), test_opportunity_radar_ranking(), test_saturation_penalty(), test_velocity_score_decay(), calculate_arbitrage_score() (+16 more)

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

### Community 73 - "env.py"
Cohesion: 0.29
Nodes (7): do_run_migrations(), Any, Run migrations in 'offline' mode., Helper method to run migrations synchronously., Run migrations in 'online' mode using async engine., run_migrations_offline(), run_migrations_online()

### Community 74 - "load_persona"
Cohesion: 0.31
Nodes (10): load_persona(), Loads persona.yaml from the given profile directory, slug, or direct file path., main(), Profile, Comprehensive End-to-End User Experience Validation for XBot Growth Engine.…, setup_test_persona_profile(), test_01_api_health(), test_02_kol_sniper_engine() (+2 more)

### Community 75 - "get_all_pipelines_status"
Cohesion: 0.13
Nodes (19): get_all_pipelines_status(), get_pipeline_history(), pause_pipeline(), Any, AsyncSession, get, post, Returns execution history log for pipeline runs. (+11 more)

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

### Community 85 - "test_f4f_growth.py"
Cohesion: 0.10
Nodes (39): asyncio, Tests that non-target demographic accounts are penalized unless they have a…, Tests that Indian creator community accounts receive higher reciprocity…, test_calculate_reciprocity_score(), test_f4f_db_lifecycle(), test_grace_period_audit_and_unfollow_lifecycle(), test_harvest_community_candidates(), test_indian_demographic_reciprocity_boost() (+31 more)

### Community 86 - "Readme"
Cohesion: 0.50
Nodes (4): Deploy on Vercel, Readme, Getting Started, Learn More

### Community 87 - "layout.tsx"
Cohesion: 0.40
Nodes (3): inter, metadata, outfit

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

### Community 105 - "trend_generator.py"
Cohesion: 0.15
Nodes (17): Tests removing markdown code fences from LLM responses., Tests parsing trend evaluation from various JSON formats., test_clean_text_for_json(), test_parse_trend_evaluation_from_json(), _assemble_draft_post(), _build_trend_system_prompt(), _build_trend_user_prompt(), _clean_text_for_json() (+9 more)

### Community 112 - "generate_poll"
Cohesion: 0.10
Nodes (37): asyncio, Tests removing markdown code fences., Tests parsing poll from various JSON structures., Tests successful structured parse via OpenAI beta endpoint., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests that options exceeding 25 characters are safely truncated to 25 chars., Tests that network or API exceptions return a high-quality default fallback…, Tests that unparseable JSON response returns a safe fallback poll. (+29 more)

### Community 113 - "test_visual_engine.py"
Cohesion: 0.14
Nodes (28): asyncio, test_generate_visual_post_spec_ai_fallback(), test_generate_visual_post_spec_default_client_resolution(), test_generate_visual_post_spec_enforces_max_140_chars(), test_generate_visual_post_spec_format_inference_when_none(), test_generate_visual_post_spec_four_pillars(), test_generate_visual_post_spec_markdown_json_cleaning(), test_infer_format_type_keywords() (+20 more)

### Community 114 - "ViralTweet"
Cohesion: 0.16
Nodes (14): asyncio, test_downloaded_media_model(), test_parse_engagement_number(), test_research_topic_comprehensively_pipeline(), test_viral_tweet_model_validation(), download_viral_media(), DownloadedMedia, _parse_engagement_number() (+6 more)

### Community 115 - "RoutingClient"
Cohesion: 0.09
Nodes (16): AsyncOpenAI, asyncio, test_routing_client_retries_and_fallback(), Beta, BetaChat, Chat, Completions, Any (+8 more)

### Community 116 - "campaigns.py"
Cohesion: 0.12
Nodes (25): generate_campaign(), GenerateCampaignRequest, get_campaign_generation_status(), publish_campaign(), PublishCampaignRequest, Any, AsyncSession, BaseModel (+17 more)

### Community 117 - "e2e_full_user_experience.py"
Cohesion: 0.40
Nodes (10): main(), Profile, End-to-End User Experience Verification Script for XBot. Simulates the complete…, verify_api_and_db_integration(), verify_kol_sniper_flow(), verify_poll_generator(), verify_profile_and_kol_setup(), verify_services_online() (+2 more)

### Community 118 - "test_reflection_learning.py"
Cohesion: 0.27
Nodes (15): db_session(), populate_test_profile(), asyncio, AsyncSession, fixture, Path, setup_db(), test_reflection_fallback_json_parsing() (+7 more)

### Community 119 - "trend_researcher_pipeline.py"
Cohesion: 0.20
Nodes (16): asyncio, test_discover_candidate_trends(), test_run_trend_researcher_for_profile_success(), discover_candidate_trends(), Any, AsyncSession, Profile, Redis (+8 more)

### Community 120 - "Design Spec: Natural Content Diversity & Context-Aware Reply Engine"
Cohesion: 0.12
Nodes (15): 1.1 Problem Statement, 1.2 Goals & Solutions, 1. Executive Summary & Problem Statement, 2. System Architecture & Component Design, 3.1 Context-Enriched Sniper & Reply Engine (`xbot/ai/sniper.py`), 3.2 Dynamic Creation & Media Pipeline (`xbot/pipelines/trend_generator_pipeline.py`), 3.3 Browser Execution Engine (`xbot/browser/actions/x_actions.py`), 3. Detailed Component Specifications (+7 more)

### Community 121 - "on_demand_campaign_pipeline.py"
Cohesion: 0.07
Nodes (45): asyncio, Tests that external links in synthesized posts are stripped to extracted_link…, Tests link stripping from thread items and open-loop hook extraction., test_synthesize_creator_post_heavy_failure_discards_cleanly(), test_synthesize_creator_post_link_extraction_and_open_loop_hook(), test_synthesize_creator_post_success(), test_synthesize_creator_thread_link_extraction(), DeliverableType (+37 more)

### Community 122 - "verify_sniper_reply"
Cohesion: 0.25
Nodes (8): Tests verify_sniper_reply accepts short replies, emoji reactions, and GIF…, Tests that any reply or target tweet mentioning Indian politics is rejected., Tests that verify_sniper_reply rejects banned AI clichés and bot praise., test_verify_sniper_reply_banned_cliches(), test_verify_sniper_reply_indian_politics_rejection(), test_verify_sniper_reply_short_and_pure_gif(), Validates candidate reply against quality, safety, and domain-matching…, verify_sniper_reply()

### Community 123 - "SimClusterTopicScorer"
Cohesion: 0.14
Nodes (17): test_enforce_natural_entity_density(), test_simcluster_topic_scorer_anti_anchor_violation(), test_simcluster_topic_scorer_delhi_aligned(), test_simcluster_topic_scorer_hashtag_limit(), test_simcluster_topic_scorer_tech_aligned(), calculate_lexical_overlap(), enforce_natural_entity_density(), BaseModel (+9 more)

### Community 126 - "Proposed Changes"
Cohesion: 0.10
Nodes (19): 1. Persona & Identity Realism Layer, 2. Anti-AI Typography & Gatekeeper System, 3. Multi-Tweet Thread Engine, 4. API Endpoints & Dashboard Staging, Anti-AI Formatting, Visual Typography & Multi-Tweet Threading Engine, Automated Tests, Manual & End-to-End Verification, [MODIFY] [`backend/xbot/ai/assembler.py`](file:///home/ubuntu/projects/xbot/backend/xbot/ai/assembler.py) & [`backend/xbot/ai/planner.py`](file:///home/ubuntu/projects/xbot/backend/xbot/ai/planner.py) (+11 more)

### Community 127 - "test_sniper_check_targets_executes_reply_and_records_db"
Cohesion: 0.19
Nodes (14): db_session(), asyncio, AsyncSession, Path, Tests that active profile with target KOLs fetches latest tweet, generates…, Tests that already-seen tweets are skipped via Redis deduplication., Tests that when SafetyGuard indicates rate limit or cooldown, sniper reply is…, Tests that profiles with no configured target KOLs are skipped without… (+6 more)

### Community 131 - "guard.py"
Cohesion: 0.17
Nodes (9): test_cooldown_tracking(), test_sliding_window_rate_limiter(), datetime, Enforces a strict cooling period for this action type., Checks if a cooldown key exists in Redis and has not yet expired., Implements Phase 3.2 Redis-based Sliding Window Rate Limiter. Utilizes Redis…, Records a new execution event in Redis sorted sets and updates TTL., Evaluates hourly and daily rates. Returns True if limit exceeded in either… (+1 more)

### Community 132 - "test_ai_decision_system.py"
Cohesion: 0.10
Nodes (31): db_session(), populate_profile_files(), asyncio, AsyncSession, fixture, Path, setup_db(), test_content_generator_with_retries() (+23 more)

### Community 133 - "meme_renderer.py"
Cohesion: 0.14
Nodes (19): download_trending_media(), _ensure_output_dir(), _get_font(), Any, Path, Autonomous 4:5 Vertical Meme & Visual Infographic Renderer for XBot Pro.…, Renders a 4:5 vertical 4-Panel progression comic/storyboard., Renders a sleek, high-contrast dark infographic cheat-sheet. (+11 more)

### Community 135 - "e2e_authenticated_session_test.py"
Cohesion: 0.38
Nodes (11): main(), Profile, End-to-End Comprehensive Feature Test for Authenticated Profile (@jackds1234 /…, run_step_1_services_health(), run_step_2_auth_status(), run_step_3_sync_from_x(), run_step_4_kol_sniper(), run_step_5_viral_hook_optimizer() (+3 more)

### Community 136 - "evaluate_content_safety"
Cohesion: 0.21
Nodes (12): test_clean_content_passes(), test_empty_content_rejected(), test_religious_offense_blocked(), test_spam_giveaway_blocked(), test_toxic_ragebait_blocked(), ContentSafetyEvaluation, DeterministicSafetyFilter, evaluate_content_safety() (+4 more)

### Community 137 - "hook_optimizer.py"
Cohesion: 0.05
Nodes (75): asyncio, Tests cleaning archetype prefixes and long strings., Tests body preservation and micro-spacing in format_optimized_post., Tests format_optimized_post with a single line draft., Tests successful structured parse with 4 archetypes and winning hook selection., Tests fallback to chat.completions.create with JSON mode when parse fails., Tests JSON parsing when returned as a dict keyed by archetype name., Tests that LLM network or API exceptions return original content safely. (+67 more)

### Community 138 - "Implementation Details"
Cohesion: 0.14
Nodes (13): 1. `VisualPostSpec` Pydantic Schema (`backend/xbot/ai/visual_engine.py`), 2. Format Templates & Aesthetic Directives (`VISUAL_FORMAT_TEMPLATES`), 3. Topic & SimCluster Inference, 4. AI Routing & Deterministic Fallback, 5. Package Exports (`backend/xbot/ai/__init__.py`), Commit Information, Full Core Test Suite, Implementation Details (+5 more)

### Community 140 - "TrendItem"
Cohesion: 0.19
Nodes (21): irrelevant_trend_item(), fixture, relevant_trend_item(), asyncio, test_fetch_atom_1_0_parsing(), test_fetch_rss_2_0_parsing(), test_fetch_rss_trends_default_client(), test_http_status_error_resilience() (+13 more)

### Community 141 - "Task 1 Report: Algorithmic Opportunity & Growth Scorer"
Cohesion: 0.17
Nodes (11): 1. `OpportunityScore` Pydantic Schema (`backend/xbot/ai/growth_scorer.py`), 2. `calculate_engagement_velocity`, 3. `score_tweet_opportunity`, Commit Information, Full Regression Suite, Implementation Details, Overview, Status (+3 more)

### Community 142 - "Task 2 Report: "Value-First + Debate Catalyst" Sniper Reply Upgrades"
Cohesion: 0.17
Nodes (11): 1. `SNIPER_PROMPT_TEMPLATE` & System Prompt Upgrade (`backend/xbot/ai/sniper.py`), 2. `SniperResult` Schema & Validation, 3. Verification & Gatekeeper Updates, Commit Information, Full Core Regression Suite, Implementation Details, Overview, Status (+3 more)

### Community 143 - "e2e_automation_safety_validation.py"
Cohesion: 0.53
Nodes (5): perform_security_and_antiban_audit(), Comprehensive End-to-End Validation Test Suite for XBot: 1. Dynamic Session…, run_all_e2e_validations(), test_dynamic_session_planning(), test_redis_rate_limiting()

### Community 144 - "Task 5 Report: Browser Action Native GIF Search & File Upload Automation"
Cohesion: 0.18
Nodes (10): 1. Robust Native Tenor GIF Search & Selection (`_attach_gif_if_requested`), 2. Action Library Enhancements (`x_actions.py`), 3. Queue Routing (`browser_queue.py`), Deliverables & Implementation Details, Git Commit Details, Overview, Task 5 Report: Browser Action Native GIF Search & File Upload Automation, Test Suite Execution (+2 more)

### Community 145 - "VerificationReport"
Cohesion: 0.28
Nodes (4): main(), Any, run_all_verifications(), VerificationReport

### Community 146 - "Task 4 Report: Bookmark-Bait & Open-Loop Hook Optimizer"
Cohesion: 0.18
Nodes (10): 1. `backend/xbot/ai/hook_optimizer.py`, 1. Module-Specific Test Suite, 2. `backend/xbot/ai/post_synthesizer.py`, 2. Full Core Test Suite, 3. `backend/xbot/ai/__init__.py`, Executive Summary, Git Commit, Key Implementation Details (+2 more)

### Community 147 - "purge_live_x_account.py"
Cohesion: 0.25
Nodes (10): clean_local_memory(), clean_sqlite_db(), delete_all_tweets_on_url(), main(), Live X Account Cleaner & Purger Purges all published tweets, replies, retweets,…, Navigates to https://x.com/jackds1234/likes and unlikes all liked tweets., Cleans local diary files and resets JSONL memory files for test_profile1., Cleans legacy SQLite records in xbot.db for profile c0fb031e-d884-4706-a9ff-… (+2 more)

### Community 148 - "scheduler.py"
Cohesion: 0.33
Nodes (9): check_and_trigger_schedules(), generate_daily_schedule(), AsyncSession, datetime, Saves generated schedule datetimes as sorted set in Redis., Called every 60s by Celery Beat: 1. Checks if active profiles are due for a…, Generates N session times for the day within the wake/sleep local hours,…, save_daily_schedule_to_redis() (+1 more)

### Community 150 - "xbot.sh"
Cohesion: 0.44
Nodes (8): check_status(), ensure_redis(), is_pid_running(), is_port_in_use(), xbot.sh script, show_logs(), start_services(), stop_services()

### Community 151 - "Global Constraints"
Cohesion: 0.25
Nodes (7): 24/7 Autonomous Growth Engine Implementation Plan, Global Constraints, Task 1: Opportunity Radar & Arbitrage Scorer, Task 2: Sniper 4-Archetype Engine & JIT Thread Perception, Task 3: Episodic Circadian Scheduler & Safety Sliding-Window Limiter, Task 4: Human-in-the-Loop Staging & 1-Click Action Verification, Task 5: End-to-End Autonomous Simulation & Live Verification

### Community 152 - "Global Constraints"
Cohesion: 0.25
Nodes (7): Global Constraints, Modern X Algorithmic Growth & Visual Engine Implementation Plan, Task 1: Algorithmic Opportunity & Growth Scorer, Task 2: "Value-First + Debate Catalyst" Sniper Reply Upgrades, Task 3: Visual & 4:5 Meme Engine, Task 4: Bookmark-Bait & Open-Loop Hook Optimizer, Task 5: 1st-Reply Link Injection & Execution Loop Integration

### Community 153 - "test_x_actions_context.py"
Cohesion: 0.29
Nodes (10): asyncio, Path, Tests comprehensive scraping of root tweet text, author, metrics, media alts,…, Tests scraping when root tweet has no metrics, no media, and no comments., Tests parsing of M/K scale metrics, alt text filtering, and comment…, Tests robustness on empty page or invalid target_idx., test_scrape_target_tweet_context_empty_and_out_of_bounds(), test_scrape_target_tweet_context_full() (+2 more)

### Community 154 - "XBot Pro UI/UX Redesign: The Command Center"
Cohesion: 0.20
Nodes (9): 1. Overview, 2.1 The Global Shell, 2.2 Feature Refactoring (Split-Pane Migration), 2.3 Mobile Graceful Degradation, 2. Structural Architecture, 3. Keyboard-First Workflows, 4. State Management, 5. Visual System (Design Tokens) (+1 more)

### Community 155 - "Deliverables & Changes"
Cohesion: 0.20
Nodes (9): 1. 6 Dynamic Reply Modalities & Schema Upgrade, 2. Elimination of Forced Question Marks (`?`) and Length Restraints, 3. Room-Reading Context Injection, 4. Verification & Testing, Deliverables & Changes, Git Commit, Overview, Task 2 Report: AI Room-Reader & Dynamic Reply Generator with 6 Modalities (+1 more)

### Community 156 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Global Constraints, Natural Content Diversity & Context-Aware Reply Engine Implementation Plan, Task 1: Multi-Modal Target Context Scraper & Payload Builder, Task 2: AI Room-Reader & Dynamic Reply Generator with 6 Modalities, Task 3: Context-Enriched Reply Pipeline & Feed/KOL Integration, Task 4: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes), Task 5: Browser Action Native GIF Search & File Upload Automation, Task 6: Full Integration Test & Daemon Verification

### Community 157 - "Implementation Report: Task 5 — 1st-Reply Link Injection & Execution Loop Integration"
Cohesion: 0.50
Nodes (3): Commits, Completed Work, Implementation Report: Task 5 — 1st-Reply Link Injection & Execution Loop Integration

### Community 158 - "plan_campaign_from_prompt"
Cohesion: 0.21
Nodes (13): asyncio, Verifies that invalid LLM output falls back to a safe single deliverable., Verifies that a multi-part prompt is decomposed into discrete deliverables., test_plan_campaign_fallback_on_parse_error(), test_plan_campaign_multi_intent_decomposition(), CampaignPlan, DeliverableSpec, plan_campaign_from_prompt() (+5 more)

### Community 160 - "Task 2 Brief: AI Room-Reader & Dynamic Reply Generator with 6 Modalities"
Cohesion: 0.29
Nodes (6): Critical Rules, Files, Objective, Requirements & TDD Steps, Schema, Task 2 Brief: AI Room-Reader & Dynamic Reply Generator with 6 Modalities

### Community 161 - "Task 1 Brief: Multi-Modal Target Context Scraper & Payload Builder"
Cohesion: 0.33
Nodes (5): Files, Interface Specification, Objective, Requirements & TDD Steps, Task 1 Brief: Multi-Modal Target Context Scraper & Payload Builder

### Community 162 - "Task 1 Completion Report: Multi-Modal Target Context Scraper & Payload Builder"
Cohesion: 0.33
Nodes (5): Git Commit, Key Capabilities Added & Tested:, Summary of Completed Work, Task 1 Completion Report: Multi-Modal Target Context Scraper & Payload Builder, Test Verification

### Community 174 - "Deliverables & Changes"
Cohesion: 0.20
Nodes (9): 1. Enriched Target Context Extraction across Reply Engines, 2. GIF Query Parameter Forwarding, 3. Dynamic Response Modes & Preservation, 4. Comprehensive Unit Testing & Core Pipeline Suite, Deliverables & Changes, Git Commit, Overview, Task 3 Report: Context-Enriched Reply Pipeline & Feed/KOL Integration (+1 more)

### Community 175 - ".assemble"
Cohesion: 0.18
Nodes (8): AssembledContext, AsyncSession, BaseModel, datetime, Helper to dump Strategy model to YAML string., Gathers files and database records to construct an AssembledContext for the…, Helper to format the Persona object into a markdown character sheet., Renders the user prompt context for session planning.

### Community 176 - "Task 3 Brief: Context-Enriched Reply Pipeline & Feed/KOL Integration"
Cohesion: 0.40
Nodes (4): Files, Objective, Requirements & TDD Steps, Task 3 Brief: Context-Enriched Reply Pipeline & Feed/KOL Integration

### Community 177 - "Task 4 Brief: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)"
Cohesion: 0.40
Nodes (4): Files, Objective, Requirements & TDD Steps, Task 4 Brief: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)

### Community 178 - "Task 5 Brief: Browser Action Native GIF Search & File Upload Automation"
Cohesion: 0.40
Nodes (4): Files, Objective, Requirements & TDD Steps, Task 5 Brief: Browser Action Native GIF Search & File Upload Automation

### Community 179 - "Global Constraints"
Cohesion: 0.22
Nodes (8): Global Constraints, Task 1: Extend State Management, Task 2: Build Bottom Console, Task 3: Build Command Palette & Global Shortcuts, Task 4: Refactor Growth Engine (Split-Pane), Task 5: Refactor Campaign Studio (Split-Pane), Task 6: Refactor Overview Tab (Grid Density), UI/UX Command Center Implementation Plan

### Community 180 - "explore_follow_back_ecosystem.py"
Cohesion: 0.67
Nodes (5): main(), _parse_int(), Any, scrape_thread_comments(), scrape_tweet_element()

### Community 181 - "SDD Ledger: Natural Content Diversity & Context-Aware Reply Engine"
Cohesion: 0.50
Nodes (3): Rulings & Log, SDD Ledger: Natural Content Diversity & Context-Aware Reply Engine, Tasks

### Community 182 - "health_check"
Cohesion: 0.40
Nodes (5): health_check(), Any, get, Health check endpoint returning system status., root()

### Community 184 - "Task 4 Report: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes)"
Cohesion: 0.22
Nodes (8): 1. Dynamic 4-Way Creation Decision Matrix (`determine_creation_format`), Deliverables & Implementation Details, Full Pipeline Test Suite Results, Git Commit Details, Overview, Task 4 Report: Dynamic Trend Generator (4:5 Memes, Media Threads, Polls, Hot Takes), Test Suite & Verification, Unit Test Suite (`backend/tests/test_trend_generator_pipeline.py`)

### Community 185 - "like_pipeline.py"
Cohesion: 0.21
Nodes (13): asyncio, test_run_like_pipeline_for_profile_skipped_by_guard(), test_run_like_pipeline_for_profile_success(), Any, AsyncSession, Profile, task, Independent Like Pipeline for XBot Pro. Runs every 15 minutes (during active… (+5 more)

### Community 187 - "mock_live_fact_grounding"
Cohesion: 0.50
Nodes (4): mock_live_fact_grounding(), fixture, Mock live fact grounder across unit tests for fast and deterministic execution., sample_tweet()

### Community 188 - "stealth.py"
Cohesion: 0.15
Nodes (12): BrowserContext, Creates or retrieves a persistent browser context for the profile. Picks a…, Starts the Playwright driver., apply_stealth(), apply_stealth_to_context(), _build_stealth_script(), BrowserContext, Page (+4 more)

### Community 190 - "analyze_sentiment_llm"
Cohesion: 0.50
Nodes (4): analyze_sentiment_llm(), analyze_sentiment_rules(), Performs offline, fast rule-based sentiment classification on input text., Performs sentiment analysis using the fast LiteLLM model.

## Knowledge Gaps
- **800 isolated node(s):** `xbot`, `backup.sh script`, `eslintConfig`, `nextConfig`, `name` (+795 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **27 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Profile` connect `Profile` to `guard.py`, `test_ai_decision_system.py`, `e2e_authenticated_session_test.py`, `sleep_with_jitter`, `_run_session_async`, `trend_generator_pipeline.py`, `get_all_rate_limits`, `generate_sniper_reply`, `models/profile.py`, `e2e_automation_safety_validation.py`, `test_trend_task.py`, `Persona`, `ProfileStatus`, `loader.py`, `scheduler.py`, `test_profile_auth_api.py`, `engagement.py`, `database.py`, `SafetyGuard`, `generate_ai_content`, `run_follow_pipeline_for_profile`, `tasks.py`, `ai/__init__.py`, `test_safety_and_scheduling.py`, `tools.py`, `quote_pipeline.py`, `like_pipeline.py`, `load_persona`, `get_all_pipelines_status`, `test_f4f_growth.py`, `campaigns.py`, `e2e_full_user_experience.py`, `test_reflection_learning.py`, `trend_researcher_pipeline.py`, `on_demand_campaign_pipeline.py`, `test_sniper_check_targets_executes_reply_and_records_db`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Why does `Persona` connect `Persona` to `formatting_engine.py`, `test_trend_generator.py`, `hook_optimizer.py`, `trend_generator_pipeline.py`, `generate_sniper_reply`, `models/profile.py`, `test_trend_task.py`, `ProfileStatus`, `loader.py`, `_build_clean_creator_prompt`, `plan_campaign_from_prompt`, `score_tweet_opportunity`, `ai/__init__.py`, `.assemble`, `test_nvidia_image.py`, `load_persona`, `generate_poll`, `test_visual_engine.py`, `ViralTweet`, `on_demand_campaign_pipeline.py`, `test_sniper_check_targets_executes_reply_and_records_db`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `get_ai_client()` connect `on_demand_campaign_pipeline.py` to `test_ai_decision_system.py`, `test_trend_generator.py`, `tasks.py`, `hook_optimizer.py`, `ai/__init__.py`, `trend_generator.py`, `generate_sniper_reply`, `generate_poll`, `test_nvidia_image.py`, `models/profile.py`, `RoutingClient`, `ProfileStatus`, `loader.py`, `test_visual_engine.py`, `analyze_sentiment_llm`, `Profile`, `plan_campaign_from_prompt`, `engagement.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Are the 180 inferred relationships involving `Profile` (e.g. with `sample_profile_with_actions()` and `test_assembler_missing_directory()`) actually correct?**
  _`Profile` has 180 INFERRED edges - model-reasoned connections that need verification._
- **Are the 89 inferred relationships involving `Persona` (e.g. with `test_build_sniper_system_prompt_6_modalities()` and `test_generate_sniper_reply_exception_safe_fallback()`) actually correct?**
  _`Persona` has 89 INFERRED edges - model-reasoned connections that need verification._
- **Are the 84 inferred relationships involving `ProfileStatus` (e.g. with `sample_profile_with_actions()` and `test_assembler_missing_directory()`) actually correct?**
  _`ProfileStatus` has 84 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `_run_session_async()` (e.g. with `CheckUserLatestTweet` and `FollowCandidate`) actually correct?**
  _`_run_session_async()` has 7 INFERRED edges - model-reasoned connections that need verification._