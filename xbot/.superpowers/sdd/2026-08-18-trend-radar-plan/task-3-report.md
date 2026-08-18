# Task 3 Report: Integrate Celery Periodic Task `check_trend_radar` & Content Staging

**Date:** 2026-08-18  
**Task:** Task 3 of Real-Time Trend Radar Implementation Plan  
**Status:** COMPLETED  

---

## 1. Summary of Changes

1. **Periodic Schedule Registration (`backend/xbot/celery_app.py`)**:
   - Registered `check-trend-radar-every-1800-seconds` in `celery_app.conf.beat_schedule` configured with a 30-minute interval (1800.0s) targeting `xbot.tasks.check_trend_radar`.

2. **Celery Task Implementation (`backend/xbot/tasks.py`)**:
   - Implemented `_check_trend_radar_async(base_profile_dir)`:
     - Queries active `Profile` records from the DB (`Profile.status == ProfileStatus.ACTIVE`).
     - Loads persona configuration and extracts custom `trend_sources` (RSS feeds & keywords) or defaults to `["https://hnrss.org/frontpage"]` and primary persona interests.
     - Fetches RSS/Atom trends via `fetch_rss_trends(feed_urls, keywords=keywords)`.
     - Performs 2-tier Redis deduplication check using keys `xbot:seen_trends:{profile.id}:{item.id}` and set `xbot:seen_trends:{profile.id}`.
     - Evaluates unseen trend stories using `generate_trend_take(persona, item)`.
     - Caches evaluated item IDs in Redis with a 7-day TTL (604800s).
     - When `eval_result.is_relevant` is True and `eval_result.optimized_post` is present:
       - Stages `Content` records in the database with `profile_id=profile.id`, `content_type=ContentType.ORIGINAL` / `TWEET`, `status=ContentStatus.APPROVED`, body text, and rich metadata (`trend_id`, `trend_title`, `relevance_score`, `reasoning`, `key_takeaways`, `hot_take`, `draft_post`, `optimized_post`).
     - Implemented robust per-profile error handling guaranteeing that failures or timeouts on one profile do not disrupt processing of remaining profiles.
   - Implemented synchronous Celery task wrapper `check_trend_radar()` registered as `@celery_app.task(name="xbot.tasks.check_trend_radar")`.

3. **Content Model Enhancement (`backend/xbot/models/content.py`)**:
   - Added `ContentStatus.APPROVED = "approved"` and `ContentType.TWEET = "original"`.
   - Added `@property def text` and `__init__` compatibility for `text`/`body` interchangeability.

4. **Integration & Unit Testing (`backend/tests/test_trend_task.py`)**:
   - Created 7 test cases covering:
     - `test_celery_schedule_registered`
     - `test_check_trend_radar_executes_and_stages_content`
     - `test_check_trend_radar_redis_deduplication`
     - `test_check_trend_radar_skips_irrelevant_trends`
     - `test_check_trend_radar_profile_error_isolation`
     - `test_check_trend_radar_custom_feed_urls_and_keywords`
     - `test_celery_task_wrapper`

---

## 2. Verification Results

- **Task Test Suite (`backend/tests/test_trend_task.py`)**: 7 passed in 4.38s (100% pass rate).
- **Trend Suite (`test_trend_radar.py`, `test_trend_generator.py`, `test_trend_task.py`)**: 31 passed in 4.98s.
- **Full Backend Suite**: 105 passed across all modules.

---

## 3. Git Commit

- Commit SHA: `d9dae8a`
- Message: `feat(tasks): integrate check_trend_radar Celery periodic task`
