"""
Notification & Reciprocal Follow-Back Engagement Pipeline for XBot Pro.

Periodically:
1. Navigates to https://x.com/notifications and scrapes new replies, mentions, and follows.
2. Automatically likes and counter-replies to incoming comments on our posts.
3. Automatically follows back new users who followed us.
4. Scrapes our followers list (https://x.com/{handle}/followers) and follows back any non-followed followers.
5. Respects CentralGuard safety rate limits and logs all actions.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import random
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.celery_app import celery_app
from xbot.database import AsyncSessionLocal
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona.loader import load_persona
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def run_notification_engagement_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    container: Container | None = None,
) -> dict[str, Any]:
    """Runs a single notification engagement cycle for a profile using BrowserPort."""
    profile_slug = profile.profile_slug
    clean_handle = profile.x_handle.lstrip("@")
    c = container or get_container()

    logger.info("NotificationEngagement: Starting cycle for @%s...", clean_handle)

    likes_count = 0

    try:
        # Step 1: Scrape Notifications via BrowserPort
        logger.info("NotificationEngagement: Scraping notifications for @%s to like incoming posts...", clean_handle)
        scrape_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SCRAPE_NOTIFICATIONS,
            params={"limit": 20},
            timeout_seconds=60,
        )
        scrape_res = await c.browser.execute(scrape_req)

        notifications = []
        if scrape_res.status in ("success", "ok") and scrape_res.scrape:
            for n in scrape_res.scrape.notifications:
                notifications.append({
                    "author_handle": n.actor_handle,
                    "tweet_url": n.tweet_url,
                })
        elif scrape_res.scrape and scrape_res.scrape.raw.get("notifications"):
            notifications = scrape_res.scrape.raw["notifications"]

        # Step 2: Process Notifications -> ONLY LIKE ❤️ posts seen
        for notif in notifications:
            author = notif.get("author_handle", "").lstrip("@")
            tweet_url = notif.get("tweet_url")

            if not author or author.lower() == clean_handle.lower():
                continue

            if tweet_url:
                if await guard.can_act(db, profile_slug, "like"):
                    if not guard.is_target_acted_upon(profile_slug, "like", tweet_url):
                        try:
                            like_req = BrowserRequest(
                                profile_slug=profile_slug,
                                action=BrowserActionType.LIKE,
                                params={"tweet_url": tweet_url},
                                timeout_seconds=20,
                            )
                            like_res = await c.browser.execute(like_req)
                            if like_res.status in ("success", "liked") or (like_res.action_result and like_res.action_result.status == "success"):
                                guard.record_action(profile_slug, "like", tweet_url)
                                likes_count += 1
                                logger.info("NotificationEngagement: Liked ❤️ post from @%s (%s)", author, tweet_url)
                        except Exception as l_err:
                            logger.debug("Like failed: %s", l_err)

    except Exception as e:
        logger.error("NotificationEngagement error for @%s: %s", clean_handle, e)
        return {"status": "error", "error": str(e)}

    result = {
        "status": "success",
        "profile": clean_handle,
        "likes_count": likes_count,
    }
    logger.info("NotificationEngagement completed for @%s: %s", clean_handle, result)
    return result


@celery_app.task(name="xbot.pipelines.notification_engagement_pipeline.run_notification_engagement")
def run_notification_engagement() -> dict[str, Any]:
    """Celery task: Periodically runs Notification Engagement for all active profiles."""
    async def _async_run():
        guard = CentralGuard()
        c = get_container()
        results = []

        async with AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            profiles = (await db.execute(stmt)).scalars().all()

            for profile in profiles:
                res = await run_notification_engagement_for_profile(db, profile, guard, container=c)
                results.append(res)

        return {"status": "success", "results": results}

    return asyncio.run(_async_run())
