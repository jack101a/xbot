"""
Browser Queue Worker and Execution Engine.
Dual-Lane Architecture: Processes Action (Write) and Research (Read) queues concurrently
using isolated tabs within shared browser contexts to eliminate head-of-line blocking.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

from playwright.async_api import BrowserContext, Page
import redis

from xbot.browser.actions.registry import dispatch_browser_action
from xbot.browser.manager import BrowserManager
from xbot.config import settings
from xbot.pipelines.browser_queue.queue import (
    ACTION_QUEUE_KEY,
    RESEARCH_QUEUE_KEY,
    BrowserJob,
    QUEUE_LOCK_KEY,
    get_redis_client,
    pop_next_job,
    set_browser_job_result,
)

logger = logging.getLogger(__name__)


async def execute_browser_action(
    page: Page,
    action_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Routes an action type to its browser action implementation via the typed action registry."""
    return await dispatch_browser_action(page, action_type, params)


async def execute_job_on_page(
    job: BrowserJob,
    context: BrowserContext,
    r: redis.Redis,
    lane_name: str = "default",
) -> dict[str, Any]:
    """
    Executes a single browser job on a dedicated page within the given context.
    Automatically closes the page on completion to preserve memory.
    """
    if (time.time() - job.created_at) > job.ttl_seconds:
        logger.warning(
            "[%s] Browser job %s (%s) expired (TTL %ds)",
            lane_name.upper(),
            job.job_id,
            job.action_type,
            job.ttl_seconds,
        )
        result = {"status": "expired", "message": "Job expired in queue"}
        set_browser_job_result(job.job_id, result, r)
        return result

    page: Page | None = None
    try:
        logger.info(
            "[%s] Executing browser job %s (%s) for profile %s",
            lane_name.upper(),
            job.job_id,
            job.action_type,
            job.profile_slug,
        )
        page = await context.new_page()
        action_result = await execute_browser_action(page, job.action_type, job.params)
        set_browser_job_result(job.job_id, action_result, r)
        logger.info(
            "[%s] Completed browser job %s (%s): %s",
            lane_name.upper(),
            job.job_id,
            job.action_type,
            action_result.get("status"),
        )
        return action_result

    except Exception as e:
        logger.error(
            "[%s] Browser job %s (%s) failed with exception: %s",
            lane_name.upper(),
            job.job_id,
            job.action_type,
            e,
            exc_info=True,
        )
        err_result = {"status": "error", "error": str(e), "action_type": job.action_type}
        set_browser_job_result(job.job_id, err_result, r)
        return err_result

    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def process_single_job(
    job: BrowserJob,
    browser_manager: BrowserManager,
    r: redis.Redis,
) -> dict[str, Any]:
    """Executes a single browser job (backward-compatibility wrapper)."""
    # Check TTL
    if (time.time() - job.created_at) > job.ttl_seconds:
        logger.warning("Browser job %s (%s) expired (TTL %ds)", job.job_id, job.action_type, job.ttl_seconds)
        result = {"status": "expired", "message": "Job expired in queue"}
        set_browser_job_result(job.job_id, result, r)
        return result

    context = await browser_manager.get_context(job.profile_slug)
    try:
        from xbot.contracts.browser import BrowserActionType
        is_write = BrowserActionType(job.action_type).is_write_action
    except Exception:
        is_write = True
    lane = "action" if is_write else "research"
    return await execute_job_on_page(job, context, r, lane_name=lane)


async def _process_browser_queue_async(max_jobs: int = 10) -> int:
    """
    Dual-Lane processor: Pops and processes Action and Research jobs concurrently.
    Action jobs (writes) and Research jobs (reads) execute in parallel tabs,
    preventing heavy research crawls from ever blocking urgent sniper replies or posts.
    """
    r = get_redis_client()

    # Acquire worker lock (prevent overlapping drain workers)
    lock_acquired = r.set(QUEUE_LOCK_KEY, "1", ex=60, nx=True)
    if not lock_acquired:
        logger.debug("Browser queue worker lock already held; skipping cycle.")
        return 0

    # Quick check: do not spin up Chromium if both queues are empty
    action_count = r.zcard(ACTION_QUEUE_KEY)
    research_count = r.zcard(RESEARCH_QUEUE_KEY)
    if action_count == 0 and research_count == 0:
        r.delete(QUEUE_LOCK_KEY)
        return 0

    processed_count = 0
    browser_manager = BrowserManager(base_profile_dir=settings.BASE_PROFILE_DIR)
    open_contexts: dict[str, BrowserContext] = {}

    try:
        await browser_manager.start()

        async def get_or_create_context(profile_slug: str) -> BrowserContext:
            if profile_slug not in open_contexts:
                open_contexts[profile_slug] = await browser_manager.get_context(profile_slug)
            return open_contexts[profile_slug]

        while processed_count < max_jobs:
            action_job = pop_next_job(r, queue_key=ACTION_QUEUE_KEY)
            research_job = pop_next_job(r, queue_key=RESEARCH_QUEUE_KEY)

            if not action_job and not research_job:
                break

            tasks = []
            if action_job:
                ctx_action = await get_or_create_context(action_job.profile_slug)
                tasks.append(execute_job_on_page(action_job, ctx_action, r, lane_name="action"))
                processed_count += 1

            if research_job:
                ctx_research = await get_or_create_context(research_job.profile_slug)
                tasks.append(execute_job_on_page(research_job, ctx_research, r, lane_name="research"))
                processed_count += 1

            if tasks:
                # Concurrent execution of Action lane and Research lane!
                await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        for slug, ctx in open_contexts.items():
            try:
                await ctx.close()
            except Exception:
                pass
        open_contexts.clear()

        try:
            await browser_manager.stop()
        except Exception:
            pass
        r.delete(QUEUE_LOCK_KEY)

    return processed_count


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.browser_queue.process_browser_queue")
def process_browser_queue(max_jobs: int = 10) -> int:
    """Synchronous Celery entry point for dual-lane browser queue worker."""
    return asyncio.run(_process_browser_queue_async(max_jobs=max_jobs))
