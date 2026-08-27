"""
Central Browser Queue & Worker for XBot.

Serializes browser operations across all independent pipelines:
- Pipelines create lightweight BrowserJob descriptors and push them to the Redis queue.
- A single Browser Worker processes queued jobs in priority order.
- Guarantees zero lock collisions, no browser crashes from competing sessions, and full visibility.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

import redis
from playwright.async_api import Page

from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    ComposePost,
    ComposeThread,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    ScrapeCreatorStudioMetrics,
    ScrapeTrends,
    SearchQuery,
    UnfollowUser,
)
from xbot.browser.manager import BrowserManager
from xbot.config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "xbot:browser_jobs:queue"
JOB_PREFIX = "xbot:browser_job:"
RESULT_PREFIX = "xbot:browser_result:"
QUEUE_LOCK_KEY = "xbot:lock:browser_queue_worker"


@dataclass
class BrowserJob:
    action_type: str  # "like", "reply", "quote", "post", "follow", "unfollow", "scrape_feed", "scrape_trending", etc.
    profile_slug: str
    params: dict[str, Any] = field(default_factory=dict)
    priority: int = 2  # 0=emergency/sniper, 1=conversation_reply, 2=post/quote, 3=like/follow, 4=scrape
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    ttl_seconds: int = 300  # 5 minutes expiration


def get_redis_client(redis_url: str | None = None) -> redis.Redis:
    return redis.from_url(redis_url or settings.REDIS_URL, decode_responses=True)


def enqueue_browser_job(job: BrowserJob, r: redis.Redis | None = None) -> str:
    """Enqueues a browser job in Redis with priority scoring."""
    if r is None:
        r = get_redis_client()

    job_data = asdict(job)
    # Store job payload
    r.set(f"{JOB_PREFIX}{job.job_id}", json.dumps(job_data), ex=job.ttl_seconds + 300)

    # Score = priority * 1e10 + created_at timestamp (lower score = popped first)
    score = float(job.priority * 1e10 + job.created_at)
    r.zadd(QUEUE_KEY, {job.job_id: score})
    logger.info(
        "Enqueued browser job %s (%s) for %s with priority %d (queue depth: %d)",
        job.job_id,
        job.action_type,
        job.profile_slug,
        job.priority,
        r.zcard(QUEUE_KEY),
    )
    return job.job_id


def get_browser_job_result(
    job_id: str,
    timeout_seconds: float = 0.0,
    r: redis.Redis | None = None,
) -> dict[str, Any] | None:
    """Retrieves result of a processed browser job. Optionally polls up to timeout_seconds."""
    if r is None:
        r = get_redis_client()

    start_time = time.time()
    while True:
        raw_result = r.get(f"{RESULT_PREFIX}{job_id}")
        if raw_result:
            try:
                return json.loads(raw_result)
            except Exception:
                return {"status": "error", "message": "Failed to parse result JSON"}

        if timeout_seconds <= 0 or (time.time() - start_time) >= timeout_seconds:
            break
        time.sleep(0.5)

    return None


def set_browser_job_result(
    job_id: str,
    result: dict[str, Any],
    r: redis.Redis | None = None,
    ttl_seconds: int = 600,
) -> None:
    """Stores result of a processed browser job in Redis."""
    if r is None:
        r = get_redis_client()
    try:
        r.set(f"{RESULT_PREFIX}{job_id}", json.dumps(result), ex=ttl_seconds)
    except Exception as e:
        logger.error("Failed to set browser job result for %s: %s", job_id, e)


def get_queue_depth(r: redis.Redis | None = None) -> int:
    """Returns number of pending jobs in browser queue."""
    if r is None:
        r = get_redis_client()
    try:
        return int(r.zcard(QUEUE_KEY))
    except Exception:
        return 0


def pop_next_job(r: redis.Redis | None = None) -> BrowserJob | None:
    """Atomically pops the highest priority job from the queue."""
    if r is None:
        r = get_redis_client()

    # ZPOPMIN returns list of (member, score) tuples
    items = r.zpopmin(QUEUE_KEY, count=1)
    if not items:
        return None

    job_id, _score = items[0]
    raw_payload = r.get(f"{JOB_PREFIX}{job_id}")
    if not raw_payload:
        logger.warning("Browser job %s payload expired or missing", job_id)
        return None

    try:
        data = json.loads(raw_payload)
        return BrowserJob(**data)
    except Exception as e:
        logger.error("Failed to deserialize browser job %s: %s", job_id, e)
        return None


async def execute_browser_action(
    page: Page,
    action_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Routes an action type to its browser action implementation."""
    if action_type == "like":
        action = LikeTweet()
        res = await action.execute(
            page,
            tweet_url=params.get("tweet_url"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "liked": bool(res)}

    elif action_type == "reply":
        action = ReplyToTweet()
        reply_text = params.get("text") or params.get("reply_text", "")
        res = await action.execute(
            page,
            reply_text=reply_text,
            tweet_url=params.get("tweet_url"),
            tweet_index=params.get("tweet_index"),
            gif_query=params.get("gif_query"),
            media_paths=params.get("media_paths"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "replied": bool(res)}

    elif action_type == "quote":
        action = QuoteTweet()
        quote_text = params.get("text") or params.get("quote_text", "")
        res = await action.execute(
            page,
            quote_text=quote_text,
            tweet_url=params.get("tweet_url"),
            tweet_index=params.get("tweet_index"),
            gif_query=params.get("gif_query"),
            media_paths=params.get("media_paths"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "quoted": bool(res)}

    elif action_type == "post":
        action = ComposePost()
        res = await action.execute(
            page,
            text=params.get("text", ""),
            media_paths=params.get("media_paths"),
            gif_query=params.get("gif_query"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "posted": bool(res)}

    elif action_type == "thread":
        action = ComposeThread()
        res = await action.execute(
            page,
            tweets=params.get("tweets", []),
            media_paths=params.get("media_paths"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "thread_posted": bool(res)}

    elif action_type == "poll":
        action = CreatePoll()
        res = await action.execute(
            page,
            question=params.get("question", ""),
            options=params.get("options", []),
            duration_minutes=params.get("duration_minutes", 1440),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "poll_created": bool(res)}

    elif action_type == "follow":
        action = FollowUser()
        res = await action.execute(page, username=params.get("username", ""))
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "followed": bool(res)}

    elif action_type == "unfollow":
        action = UnfollowUser()
        res = await action.execute(page, username=params.get("username", ""))
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "unfollowed": bool(res)}


    elif action_type == "scrape_feed":
        action = BrowseFeed()
        tweets = await action.execute(
            page,
            max_scrolls=params.get("scroll_count", 3),
        )
        return {"status": "success", "tweets": tweets or []}

    elif action_type == "scrape_trending":
        action = ScrapeTrends()
        trends = await action.execute(page, limit=params.get("limit", 10))
        return {"status": "success", "trends": trends or []}

    elif action_type == "check_user_tweets":
        action = CheckUserLatestTweet()
        res = await action.execute(
            page,
            username=params.get("username", ""),
            max_age_minutes=params.get("max_age_minutes", 60),
        )
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    elif action_type == "sync_profile":
        action = SyncProfileFromX()
        res = await action.execute(page, username=params.get("username", ""))
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    elif action_type == "search_and_scrape":
        action = SearchQuery()
        results = await action.execute(page, query=params.get("query", ""))
        return {"status": "success", "results": results or []}

    elif action_type == "sync_creator_studio":
        action = ScrapeCreatorStudioMetrics()
        res = await action.execute(page)
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    else:
        raise ValueError(f"Unknown browser action type: {action_type}")



async def process_single_job(
    job: BrowserJob,
    browser_manager: BrowserManager,
    r: redis.Redis,
) -> dict[str, Any]:
    """Executes a single browser job with browser context management and error isolation."""
    # Check TTL
    if (time.time() - job.created_at) > job.ttl_seconds:
        logger.warning("Browser job %s (%s) expired (TTL %ds)", job.job_id, job.action_type, job.ttl_seconds)
        result = {"status": "expired", "message": "Job expired in queue"}
        set_browser_job_result(job.job_id, result, r)
        return result

    context = None
    try:
        logger.info("Executing browser job %s (%s) for profile %s", job.job_id, job.action_type, job.profile_slug)
        context = await browser_manager.get_context(job.profile_slug)
        page = context.pages[0] if context.pages else await context.new_page()

        action_result = await execute_browser_action(page, job.action_type, job.params)
        set_browser_job_result(job.job_id, action_result, r)
        logger.info("Completed browser job %s (%s): %s", job.job_id, job.action_type, action_result.get("status"))
        return action_result

    except Exception as e:
        logger.error("Browser job %s (%s) failed with exception: %s", job.job_id, job.action_type, e, exc_info=True)
        err_result = {"status": "error", "error": str(e), "action_type": job.action_type}
        set_browser_job_result(job.job_id, err_result, r)
        return err_result

    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass


async def _process_browser_queue_async(max_jobs: int = 5) -> int:
    """Drains up to max_jobs from the queue in priority order."""
    r = get_redis_client()

    # Acquire worker lock (prevent overlapping drain workers)
    lock_acquired = r.set(QUEUE_LOCK_KEY, "1", ex=30, nx=True)
    if not lock_acquired:
        logger.debug("Browser queue worker lock already held; skipping cycle.")
        return 0

    processed_count = 0
    browser_manager = BrowserManager(base_profile_dir=settings.BASE_PROFILE_DIR)

    try:
        await browser_manager.start()

        for _ in range(max_jobs):
            job = pop_next_job(r)
            if not job:
                break

            await process_single_job(job, browser_manager, r)
            processed_count += 1

    finally:
        try:
            await browser_manager.stop()
        except Exception:
            pass
        r.delete(QUEUE_LOCK_KEY)

    return processed_count


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.browser_queue.process_browser_queue")
def process_browser_queue(max_jobs: int = 5) -> int:
    """Synchronous Celery entry point for browser queue worker."""
    return asyncio.run(_process_browser_queue_async(max_jobs=max_jobs))

