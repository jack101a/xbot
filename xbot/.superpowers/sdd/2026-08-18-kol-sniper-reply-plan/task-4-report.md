# Task 4 Report: Integrate Celery Periodic Task sniper_check_targets with Redis Deduplication & Safety

## Overview
- **Task ID**: Task 4
- **Status**: Completed
- **Timestamp**: 2026-08-18T14:13:00+05:30

## Changes Made
1. **Celery Beat Schedule Registration** ([`backend/xbot/celery_app.py`](file:///home/ubuntu/projects/xbot/backend/xbot/celery_app.py)):
   - Added periodic beat schedule `sniper-check-targets-every-120-seconds` configured to run `xbot.tasks.sniper_check_targets` every 120.0 seconds.

2. **Celery Periodic Task Implementation** ([`backend/xbot/tasks.py`](file:///home/ubuntu/projects/xbot/backend/xbot/tasks.py)):
   - Implemented `_sniper_check_targets_async() -> dict[str, Any]` and registered `@celery_app.task(name="xbot.tasks.sniper_check_targets")`:
     - Queries all active `Profile` records from the database (`Profile.status == ProfileStatus.ACTIVE`).
     - Loads each profile's persona config (`persona.yaml`) and verifies `persona.target_kols` is non-empty.
     - Runs safety limits check (`SafetyGuard.is_action_safe(db, profile_slug, "reply")`) before launching browser.
     - Uses `BrowserManager` to acquire exclusive profile browser locks (`acquire_lock(profile_slug, timeout_seconds=600)`).
     - Iterates through each configured target KOL and scans for their latest tweet via `CheckUserLatestTweet()`.
     - Deduplicates against previously seen tweets using Redis key `xbot:seen_tweets:{profile_id}:{tweet_id}` with 7-day expiration and set membership `xbot:seen_tweets:{profile_id}`.
     - Calls `generate_sniper_reply(persona, tweet_data, preferred_angle=kol.preferred_angle)` from `xbot.ai.sniper`.
     - Executes reply using `ReplyToTweet()` with jitter delays.
     - Records successful replies in database `Action` records with `action_type=ActionType.REPLY`, `status=ActionStatus.COMPLETED`, and metadata payload `{"sniper": True, "target_kol": kol.handle, "angle": result.angle_used, ...}`.
     - Updates `SafetyGuard.record_action_success` and applies cooldowns, or records failures via `SafetyGuard.record_action_failure`.
     - Guarantees clean browser context closing and lock release in `finally` blocks.

3. **Session Model Support** ([`backend/xbot/models/session.py`](file:///home/ubuntu/projects/xbot/backend/xbot/models/session.py)):
   - Made `session_id` nullable on the `Action` model (`session_id: Mapped[uuid.UUID | None]`) to seamlessly persist standalone actions triggered by periodic tasks outside of interactive browser sessions.

4. **Comprehensive Test Suite** ([`backend/tests/test_sniper_task.py`](file:///home/ubuntu/projects/xbot/backend/tests/test_sniper_task.py)):
   - Added unit and integration tests verifying:
     - `test_celery_schedule_registered`: Confirms periodic schedule registration in Celery app.
     - `test_sniper_check_targets_executes_reply_and_records_db`: Verifies end-to-end task execution on active profiles, latest tweet checking, sniper reply generation, reply posting, Redis dedup marking, and DB Action creation.
     - `test_sniper_check_targets_redis_deduplication`: Verifies already-seen tweets are skipped without triggering LLM calls or replies.
     - `test_sniper_check_targets_safety_guard_rate_limit`: Verifies safety guard limits prevent execution when rate limits or cooldowns are active.
     - `test_sniper_check_targets_skips_profiles_without_target_kols`: Verifies profiles without target KOLs are skipped without acquiring browser locks.
     - `test_sniper_check_targets_lock_collision_and_release_on_error`: Tests lock collision handling and guaranteed lock release when errors occur.
     - `test_celery_task_wrapper`: Tests synchronous Celery entrypoint wrapper execution.

## Test Verification
- Executed: `backend/.venv/bin/pytest backend/tests/test_sniper_task.py -v`
- Result: 7 passed in 7.04s
  - `test_celery_schedule_registered` PASSED [14%]
  - `test_sniper_check_targets_executes_reply_and_records_db` PASSED [28%]
  - `test_sniper_check_targets_redis_deduplication` PASSED [42%]
  - `test_sniper_check_targets_safety_guard_rate_limit` PASSED [57%]
  - `test_sniper_check_targets_skips_profiles_without_target_kols` PASSED [71%]
  - `test_sniper_check_targets_lock_collision_and_release_on_error` PASSED [85%]
  - `test_celery_task_wrapper` PASSED [100%]
- Full sniper suite execution (`test_ai_sniper.py`, `test_sniper_browser_action.py`, `test_sniper_task.py`): 20 passed in 23.52s.

## Git Commit
- Commit: `bcf5370`
- Message: `feat(tasks): integrate sniper_check_targets Celery periodic task`
