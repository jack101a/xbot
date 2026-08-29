"""
Browser Queue Worker and Execution Engine.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

from playwright.async_api import Page
import redis

from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    ComposePost,
    ComposeThread,
    DeleteTweet,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    ScrapeCreatorStudioMetrics,
    ScrapeProfileTweets,
    ScrapeTrends,
    SearchQuery,
    UnfollowUser,
    scrape_target_tweet_context,
)
from xbot.browser.manager import BrowserManager
from xbot.config import settings
from xbot.pipelines.browser_queue.queue import (
    BrowserJob,
    QUEUE_LOCK_KEY,
    get_redis_client,
    pop_next_job,
    set_browser_job_result,
)

logger = logging.getLogger(__name__)


def _get_pkg():
    return sys.modules.get("xbot.pipelines.browser_queue") or sys.modules[__name__]


async def execute_browser_action(
    page: Page,
    action_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Routes an action type to its browser action implementation."""
    pkg = _get_pkg()

    if action_type == "like":
        action = pkg.LikeTweet()
        res = await action.execute(
            page,
            tweet_url=params.get("tweet_url"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "liked": bool(res)}

    elif action_type == "reply":
        action = pkg.ReplyToTweet()
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
        action = pkg.QuoteTweet()
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
        action = pkg.ComposePost()
        res = await action.execute(
            page,
            text=params.get("text", ""),
            media_paths=params.get("media_paths"),
            gif_query=params.get("gif_query"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "posted": bool(res)}

    elif action_type == "thread":
        action = pkg.ComposeThread()
        res = await action.execute(
            page,
            tweets=params.get("tweets", []),
            media_paths=params.get("media_paths"),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "thread_posted": bool(res)}

    elif action_type == "poll":
        action = pkg.CreatePoll()
        res = await action.execute(
            page,
            question=params.get("question", ""),
            options=params.get("options", []),
            duration_minutes=params.get("duration_minutes", 1440),
        )
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "poll_created": bool(res)}

    elif action_type == "follow":
        action = pkg.FollowUser()
        res = await action.execute(page, username=params.get("username", ""))
        return res if isinstance(res, dict) else {"status": "success" if res else "followed", "followed": bool(res)}

    elif action_type == "unfollow":
        action = pkg.UnfollowUser()
        res = await action.execute(page, username=params.get("username", ""))
        return res if isinstance(res, dict) else {"status": "success" if res else "failed", "unfollowed": bool(res)}

    elif action_type == "scrape_feed":
        action = pkg.BrowseFeed()
        tweets = await action.execute(
            page,
            max_scrolls=params.get("scroll_count", 3),
        )
        return {"status": "success", "tweets": tweets or []}

    elif action_type == "scrape_trending":
        action = pkg.ScrapeTrends()
        trends = await action.execute(page, limit=params.get("limit", 10))
        return {"status": "success", "trends": trends or []}

    elif action_type == "check_user_tweets":
        action = pkg.CheckUserLatestTweet()
        res = await action.execute(
            page,
            username=params.get("username", ""),
            max_age_minutes=params.get("max_age_minutes", 60),
        )
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    elif action_type == "sync_profile":
        action = pkg.SyncProfileFromX()
        res = await action.execute(page, username=params.get("username", ""))
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    elif action_type == "search_and_scrape":
        action = pkg.SearchQuery()
        results = await action.execute(page, query=params.get("query", ""))
        return {"status": "success", "results": results or []}

    elif action_type == "sync_creator_studio":
        action = pkg.ScrapeCreatorStudioMetrics()
        res = await action.execute(page)
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    elif action_type == "delete_tweet":
        action = pkg.DeleteTweet()
        res = await action.execute(
            page,
            tweet_url=params.get("tweet_url"),
            tweet_id=params.get("tweet_id"),
            username=params.get("username"),
        )
        return res if isinstance(res, dict) else {"status": "success", "result": res}

    elif action_type == "scrape_profile_tweets":
        action = pkg.ScrapeProfileTweets()
        res = await action.execute(
            page,
            username=params.get("username", ""),
            limit=params.get("limit", 20),
        )
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
