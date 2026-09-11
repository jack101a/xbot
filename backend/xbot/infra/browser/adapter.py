"""
xbot.infra.browser.adapter: Concrete implementation of BrowserPort using Playwright & BrowserManager.
"""
from __future__ import annotations

import logging
from typing import Any

from xbot.config import settings
from xbot.contracts.browser import (
    ActionResult,
    BrowserActionType,
    BrowserRequest,
    BrowserResponse,
    FollowListResult,
    NotificationData,
    ScrapeResult,
    TweetData,
)
from xbot.contracts.ports import BrowserPort
from xbot.browser.manager import BrowserManager

logger = logging.getLogger(__name__)


def _normalize_browser_output(req: BrowserRequest, raw: dict[str, Any]) -> BrowserResponse:
    """Explicit normalizer mapping legacy raw action dictionaries into typed BrowserResponse."""
    status_str = raw.get("status", "success")
    if status_str not in ("success", "failed", "skipped", "expired", "error"):
        status_str = "success" if status_str in ("ok", "replied", "liked", "quoted", "posted", "thread_posted", "poll_created", "followed", "unfollowed") else "error"

    error_msg = raw.get("error")

    # Read/Scrape actions
    if req.action in (
        BrowserActionType.SCRAPE_FEED,
        BrowserActionType.SCRAPE_TRENDING,
        BrowserActionType.SCRAPE_NOTIFICATIONS,
        BrowserActionType.SCRAPE_FOLLOW_LIST,
        BrowserActionType.SCRAPE_PROFILE_TWEETS,
        BrowserActionType.SCRAPE_TWEET_CONTEXT,
        BrowserActionType.SEARCH,
    ):
        scrape_res = ScrapeResult(raw=raw)

        tweet_list = raw.get("tweets") or raw.get("results") or []
        if isinstance(tweet_list, list):
            for t in tweet_list:
                if isinstance(t, dict):
                    metrics = t.get("metrics") or {}
                    if not metrics:
                        metrics = {
                            "views": int(t.get("views") or t.get("impressions") or 0),
                            "likes": int(t.get("likes") or 0),
                            "replies": int(t.get("replies") or 0),
                            "retweets": int(t.get("retweets") or 0),
                            "top_comments": t.get("top_comments") or [],
                            "media_alts": t.get("media_alts") or [],
                        }
                    else:
                        if "top_comments" not in metrics and "top_comments" in t:
                            metrics["top_comments"] = t["top_comments"]
                        if "media_alts" not in metrics and "media_alts" in t:
                            metrics["media_alts"] = t["media_alts"]
                    scrape_res.tweets.append(
                        TweetData(
                            tweet_id=str(t.get("tweet_id") or t.get("id") or ""),
                            url=t.get("url") or t.get("tweet_url") or "",
                            handle=t.get("handle") or t.get("author") or "",
                            text=t.get("text") or "",
                            created_at=t.get("created_at"),
                            is_pinned=bool(t.get("is_pinned", False)),
                            metrics=metrics,
                            top_comments=t.get("top_comments") or [],
                            media_alts=t.get("media_alts") or [],
                            media_urls=t.get("media_urls") or [],
                            hashtags=t.get("hashtags") or [],
                            has_video=bool(t.get("has_video", False)),
                        )
                    )

        if "trends" in raw and isinstance(raw["trends"], list):
            scrape_res.trends = raw["trends"]

        if "notifications" in raw and isinstance(raw["notifications"], list):
            for n in raw["notifications"]:
                if isinstance(n, dict):
                    scrape_res.notifications.append(
                        NotificationData(
                            kind=n.get("kind") or n.get("type") or "unknown",
                            actor_handle=n.get("actor_handle") or n.get("author") or "",
                            text=n.get("text") or "",
                            tweet_url=n.get("tweet_url"),
                        )
                    )

        if "candidates" in raw and isinstance(raw["candidates"], list):
            scrape_res.candidates = raw["candidates"]

        if "follow_list" in raw and isinstance(raw["follow_list"], dict):
            fl = raw["follow_list"]
            scrape_res.follow_list = FollowListResult(
                list_type=fl.get("list_type", req.params.get("list_type", "followers")),
                handles=fl.get("handles") or [],
                unreciprocated_handles=fl.get("unreciprocated_handles") or [],
                verified_unreciprocated_handles=fl.get("verified_unreciprocated_handles") or [],
                following_handles=fl.get("following_handles") or [],
            )
        elif "followers" in raw and isinstance(raw["followers"], list):
            scrape_res.follow_list = FollowListResult(
                list_type=req.params.get("list_type", "followers"),
                handles=raw["followers"],
                unreciprocated_handles=raw.get("unreciprocated_handles") or [],
                verified_unreciprocated_handles=raw.get("verified_unreciprocated_handles") or [],
                following_handles=raw.get("following_handles") or [],
            )
        elif "handles" in raw and isinstance(raw["handles"], list):
            scrape_res.follow_list = FollowListResult(
                list_type=req.params.get("list_type", "followers"),
                handles=raw["handles"],
                unreciprocated_handles=raw.get("unreciprocated_handles") or [],
                verified_unreciprocated_handles=raw.get("verified_unreciprocated_handles") or [],
                following_handles=raw.get("following_handles") or [],
            )

        return BrowserResponse(
            status=status_str,
            action=req.action,
            error=error_msg,
            scrape=scrape_res,
        )

    # State-modifying actions (post, reply, quote, like, follow, unfollow, etc.)
    act_res = ActionResult(
        status=status_str,
        detail=raw.get("detail") or raw.get("message"),
        target_id=str(raw.get("tweet_id") or raw.get("root_tweet_id") or raw.get("id") or "") or None,
        url=raw.get("url") or raw.get("tweet_url"),
        raw=raw,
    )
    return BrowserResponse(
        status=status_str,
        action=req.action,
        error=error_msg,
        action_result=act_res,
    )


class PlaywrightBrowserAdapter(BrowserPort):
    """Direct execution adapter using BrowserManager and Playwright pages."""

    def __init__(self, manager: BrowserManager | None = None) -> None:
        self._manager = manager or BrowserManager(base_profile_dir=settings.BASE_PROFILE_DIR)

    async def execute(self, request: BrowserRequest) -> BrowserResponse:
        logger.info(f"[BrowserAdapter] Executing action '{request.action}' for profile '{request.profile_slug}'")
        ctx = None
        try:
            from xbot.infra.browser.queue.worker import execute_browser_action

            if not self._manager.playwright:
                await self._manager.start()

            ctx = await self._manager.get_context(request.profile_slug)
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()

            raw = await execute_browser_action(
                page=page,
                action_type=request.action.value,
                params=request.params,
            )
            return _normalize_browser_output(request, raw)
        except Exception as exc:
            logger.error(f"[BrowserAdapter] Action '{request.action}' failed: {exc}", exc_info=True)
            return BrowserResponse(
                status="error",
                action=request.action,
                error=str(exc),
                action_result=ActionResult(status="error", detail=str(exc)),
            )
        finally:
            if ctx:
                try:
                    await ctx.close()
                except Exception:
                    pass
            self._manager.release_lock(request.profile_slug)
