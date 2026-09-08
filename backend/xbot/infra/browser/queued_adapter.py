"""
xbot.infra.browser.queued_adapter: Queue-backed implementation of BrowserPort over Redis.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from xbot.contracts.browser import (
    ActionResult,
    BrowserActionType,
    BrowserRequest,
    BrowserResponse,
)
from xbot.contracts.ports import BrowserPort
from xbot.infra.browser.adapter import _normalize_browser_output
from xbot.pipelines.browser_queue.queue import (
    BrowserJob,
    enqueue_browser_job,
    get_browser_job_result,
)

logger = logging.getLogger(__name__)

_PRIORITY_MAP: dict[BrowserActionType, int] = {
    BrowserActionType.POST: 0,
    BrowserActionType.THREAD: 0,
    BrowserActionType.POLL: 0,
    BrowserActionType.QUOTE: 1,
    BrowserActionType.REPLY: 2,
    BrowserActionType.SEARCH: 1,
    BrowserActionType.FOLLOW: 3,
    BrowserActionType.UNFOLLOW: 3,
    BrowserActionType.LIKE: 3,
    BrowserActionType.CHECK_USER_LATEST: 2,
    BrowserActionType.SCRAPE_FEED: 3,
    BrowserActionType.SCRAPE_FOLLOW_LIST: 3,
    BrowserActionType.SCRAPE_TWEET_CONTEXT: 3,
    BrowserActionType.SCRAPE_NOTIFICATIONS: 3,
    BrowserActionType.SCRAPE_TRENDING: 4,
    BrowserActionType.SCRAPE_PROFILE_TWEETS: 4,
    BrowserActionType.SYNC_PROFILE: 4,
    BrowserActionType.SYNC_CREATOR_STUDIO: 4,
    BrowserActionType.DELETE_TWEET: 1,
    BrowserActionType.PRUNE_TIMELINE: 1,
}


class QueuedBrowserAdapter(BrowserPort):
    """Submits BrowserRequest into Redis queue and awaits the background worker result."""

    def __init__(self, poll_interval_seconds: float = 0.5) -> None:
        self._poll_interval = poll_interval_seconds

    async def execute(self, request: BrowserRequest) -> BrowserResponse:
        logger.info(f"[QueuedBrowserAdapter] Enqueueing '{request.action}' for '{request.profile_slug}'")
        try:
            if request.timeout_seconds:
                wait_timeout = float(request.timeout_seconds)
            elif request.action in (BrowserActionType.POST, BrowserActionType.REPLY, BrowserActionType.QUOTE, BrowserActionType.THREAD, BrowserActionType.POLL):
                wait_timeout = 120.0
            elif request.action in (BrowserActionType.SCRAPE_FEED, BrowserActionType.SCRAPE_TWEET_CONTEXT, BrowserActionType.SCRAPE_TRENDING):
                wait_timeout = 60.0
            else:
                wait_timeout = 45.0
            ttl = max(180, int(wait_timeout) + 60)
            priority = _PRIORITY_MAP.get(request.action, 4)
            job = BrowserJob(
                action_type=request.action.value,
                profile_slug=request.profile_slug,
                params=request.params,
                priority=priority,
                ttl_seconds=ttl,
            )

            job_id = await asyncio.to_thread(
                enqueue_browser_job,
                job,
            )

            # Wait for background queue worker result with generous allowance for human typing
            result_raw = await asyncio.to_thread(
                get_browser_job_result,
                job_id,
                wait_timeout,
            )

            if result_raw is None:
                return BrowserResponse(
                    status="expired",
                    action=request.action,
                    error=f"Job {job_id} timed out waiting for queue worker response after {request.timeout_seconds}s",
                    action_result=ActionResult(status="expired", detail="Queue timeout"),
                )

            return _normalize_browser_output(request, result_raw)
        except Exception as exc:
            logger.error(f"[QueuedBrowserAdapter] Execution error for job: {exc}", exc_info=True)
            return BrowserResponse(
                status="error",
                action=request.action,
                error=str(exc),
                action_result=ActionResult(status="error", detail=str(exc)),
            )
