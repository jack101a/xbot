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

from xbot.ai.client import get_ai_client
from xbot.ai.sniper import generate_sniper_reply
from xbot.browser.actions.x_actions import (
    FollowUser,
    LikeTweet,
    ReplyToTweet,
    ScrapeFollowList,
    ScrapeNotifications,
)
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter
from xbot.celery_app import celery_app
from xbot.database import AsyncSessionLocal
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.persona.loader import load_persona
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def run_notification_engagement_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    manager: BrowserManager,
) -> dict[str, Any]:
    """
    Runs a single notification and follow-back engagement cycle for a profile.
    """
    profile_slug = profile.profile_slug
    clean_handle = profile.x_handle.lstrip("@")
    profile_id = profile.id

    logger.info("NotificationEngagement: Starting cycle for @%s...", clean_handle)

    # 1. Acquire browser lock
    lock_acquired = False
    for _ in range(3):
        if manager.acquire_lock(profile_slug, timeout_seconds=240):
            lock_acquired = True
            break
        await asyncio.sleep(1.5)

    if not lock_acquired:
        return {"status": "skipped", "reason": "browser_lock_busy"}

    persona = None
    try:
        persona = load_persona(profile_slug)
    except Exception as e:
        logger.debug("Could not load persona for %s: %s", profile_slug, e)

    likes_count = 0
    replies_count = 0
    follows_count = 0

    try:
        context = await manager.get_context(profile_slug=profile_slug)
        page = await context.new_page()

        # Step 1: Scrape Notifications
        logger.info("NotificationEngagement: Scraping notifications for @%s to like incoming posts...", clean_handle)
        scraper = ScrapeNotifications()
        notifications = await scraper.execute(page, limit=20)

        # Step 2: Process Notifications -> ONLY LIKE ❤️ posts seen
        for notif in notifications:
            author = notif.get("author_handle", "").lstrip("@")
            tweet_url = notif.get("tweet_url")

            if not author or author.lower() == clean_handle.lower():
                continue

            # If there is a tweet URL associated with this notification (reply, mention, quote, repost)
            if tweet_url:
                if await guard.can_act(db, profile_slug, "like"):
                    if not guard.is_target_acted_upon(profile_slug, "like", tweet_url):
                        try:
                            like_action = LikeTweet()
                            res_like = await like_action.execute(page, tweet_url=tweet_url)
                            if res_like:
                                guard.record_action(profile_slug, "like", tweet_url)
                                likes_count += 1
                                logger.info("NotificationEngagement: Liked ❤️ post from @%s (%s)", author, tweet_url)
                                await sleep_with_jitter(1500)
                        except Exception as l_err:
                            logger.debug("Like failed: %s", l_err)

        await page.close()
        await context.close()

    except Exception as e:
        logger.error("NotificationEngagement error for @%s: %s", clean_handle, e)
        return {"status": "error", "error": str(e)}
    finally:
        manager.release_lock(profile_slug)

    result = {
        "status": "success",
        "profile": clean_handle,
        "likes_count": likes_count,
    }
    logger.info("NotificationEngagement completed for @%s: %s", clean_handle, result)
    return result


@celery_app.task(name="xbot.pipelines.notification_engagement_pipeline.run_notification_engagement")
def run_notification_engagement() -> dict[str, Any]:
    """
    Celery task: Periodically runs the Notification Engagement & Follow-Back Pipeline for all active profiles.
    """
    async def _async_run():
        guard = CentralGuard()
        manager = BrowserManager()
        async with AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            profiles = res.scalars().all()

            results = {}
            for prof in profiles:
                r = await run_notification_engagement_for_profile(db, prof, guard, manager)
                results[prof.profile_slug] = r
            return results

    return asyncio.run(_async_run())
