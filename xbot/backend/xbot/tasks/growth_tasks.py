from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import random
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.analytics import AnalyticsSnapshot, FollowerSnapshot, FollowerChangeLog
from xbot.models.realgraph import RealGraphEdge
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter, sleep_think_time
from xbot.browser.actions.x_actions import *
from xbot.celery_app import celery_app
from xbot.ai.client import get_ai_client
from xbot.ai.planner import plan_session
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.ai.poll_generator import generate_poll
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.post_session import PostSessionProcessor
from xbot.growth.f4f_engine import populate_f4f_candidates, record_follow_action, record_unfollow_action

logger = logging.getLogger("xbot.tasks")

async def _run_growth_and_autofollowback_async() -> dict[str, Any]:
    """
    Periodic Growth & Follow-Back Engine (runs every 10-15 minutes):
    1. Audits our profile's followers on X. If anyone new followed us, instantly executes reciprocal follow-back!
    2. Proactively advances the 500+ Verified Blue-Tick Followers mission by following 1-2 top reciprocity candidates from target communities.
    3. Prunes non-mutual accounts outside the 4-day grace period to protect TweepCred PageRank (>65).
    """
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ScrapeFollowList, FollowUser, UnfollowUser
    from xbot.models.profile import Profile, ProfileStatus
    from xbot.models.follow_growth import FollowCandidate, FollowRelationship
    from xbot.models.analytics import FollowerChangeLog
    from xbot.growth.f4f_engine import populate_f4f_candidates, record_follow_action, record_unfollow_action
    from xbot.safety.guard import SafetyGuard

    manager = BrowserManager()
    guard = SafetyGuard()
    results = {}

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile).where(Profile.status == ProfileStatus.ACTIVE))
            profiles = p_res.scalars().all()

            for prof in profiles:
                clean_handle = prof.x_handle.lstrip("@")
                lock_acquired = False
                for _ in range(5):
                    if manager.acquire_lock(prof.profile_slug, timeout_seconds=120):
                        lock_acquired = True
                        break
                    import asyncio as _aio
                    await _aio.sleep(2.0)

                if not lock_acquired:
                    logger.info("Skipping growth cycle for %s: browser lock busy.", prof.profile_slug)
                    continue

                context = None
                followed_back_count = 0
                proactive_followed_count = 0
                pruned_count = 0

                try:
                    context = await manager.get_context(prof.profile_slug)
                    page = await context.new_page()
                    page.set_default_timeout(25000)

                    # 1. Scrape current followers & following lists from live profile (check EVERY follower)
                    logger.info("Scanning live followers & following for @%s...", clean_handle)
                    current_followers = await ScrapeFollowList().execute(page, username=clean_handle, list_type="followers", limit=100, verified_only=False)
                    current_following = await ScrapeFollowList().execute(page, username=clean_handle, list_type="following", limit=100, verified_only=False)

                    # 1b. Also check Notifications tab for new follower notifications
                    try:
                        logger.info("Checking notifications section for new follower events...")
                        await page.goto("https://x.com/notifications", wait_until="domcontentloaded", timeout=20000)
                        await sleep_with_jitter(2000)
                        notif_articles = await page.query_selector_all("article, [data-testid='cellInnerDiv']")
                        for notif in notif_articles[:25]:
                            notif_text = await notif.inner_text()
                            if "followed you" in notif_text.lower():
                                links = await notif.query_selector_all("a[href^='/']")
                                for link in links:
                                    href = await link.get_attribute("href") or ""
                                    handle_candidate = href.strip("/")
                                    if handle_candidate and "/" not in handle_candidate and handle_candidate.lower() not in [
                                        "home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings", clean_handle.lower()
                                    ]:
                                        if handle_candidate not in current_followers:
                                            current_followers.append(handle_candidate)
                                            logger.info("Discovered new follower @%s from notifications!", handle_candidate)
                    except Exception as notif_err:
                        logger.debug("Notifications follower scan exception: %s", notif_err)

                    followers_set = {f.lstrip("@").lower() for f in current_followers}
                    following_set = {f.lstrip("@").lower() for f in current_following}

                    # Record updated snapshot in AnalyticsSnapshot
                    if current_followers or current_following:
                        from xbot.models.analytics import AnalyticsSnapshot
                        import datetime as _dt
                        snap = AnalyticsSnapshot(
                            profile_id=prof.id,
                            snapshot_date=_dt.date.today(),
                            followers=len(current_followers),
                            following=len(current_following),
                            captured_at=_dt.datetime.utcnow(),
                        )
                        db.add(snap)
                        await db.commit()

                    # 2. AUTO FOLLOW-BACK (EVERY USER WHO FOLLOWS US):
                    unfollowed_followers = [f for f in current_followers if f.lstrip("@").lower() not in following_set and f.lstrip("@").lower() != clean_handle.lower()]
                    logger.info("Total incoming followers needing reciprocal follow-back: %d", len(unfollowed_followers))
                    for target_follower in unfollowed_followers:
                        can_follow = await guard.is_action_safe(db, prof.profile_slug, "follow")
                        if not can_follow:
                            logger.info("Daily follow safety limit reached for %s. Pausing follow-back.", prof.profile_slug)
                            break

                        logger.info("🤝 Auto Follow-Back triggered for incoming follower @%s!", target_follower)
                        f_ok = await FollowUser().execute(page, username=target_follower)
                        if f_ok:
                            followed_back_count += 1
                            following_set.add(target_follower.lstrip("@").lower())
                            await record_follow_action(prof.id, target_follower, db, is_blue_tick=False, niche="incoming_follower")
                            await guard.record_action_success(prof.profile_slug, "follow")
                            db.add(FollowerChangeLog(profile_id=prof.id, change_type="new_follower", handle=target_follower))
                            await db.commit()
                            await sleep_with_jitter(3000)

                    # 3. PROACTIVE 500+ VERIFIED FOLLOWER GROWTH MISSION:
                    # If daily follow limit allows, harvest & follow 1-2 top verified blue-tick candidates
                    can_follow_more = await guard.is_action_safe(db, prof.profile_slug, "follow")
                    if can_follow_more and (followed_back_count < 2):
                        # Ensure candidate pool is populated with verified creators only
                        c_stmt = (
                            select(FollowCandidate)
                            .where(
                                FollowCandidate.profile_id == prof.id,
                                FollowCandidate.status == "discovered",
                                FollowCandidate.is_blue_tick == True,
                            )
                            .order_by(FollowCandidate.reciprocity_score.desc())
                            .limit(5)
                        )
                        c_res = await db.execute(c_stmt)
                        candidates = list(c_res.scalars().all())

                        if len(candidates) < 3:
                            await populate_f4f_candidates(prof.id, db, niche="all", limit=15)
                            c_res = await db.execute(c_stmt)
                            candidates = list(c_res.scalars().all())

                        for cand in candidates[:2]:
                            cand_handle = cand.handle.lstrip("@").lower()
                            if cand_handle in following_set:
                                cand.status = "followed"
                                continue

                            if not await guard.is_action_safe(db, prof.profile_slug, "follow"):
                                break

                            logger.info("🎯 Proactive Verified Follow targeting @%s (Reciprocity Score: %.1f, Niche: %s)...", cand.handle, cand.reciprocity_score, cand.niche)
                            f_ok = await FollowUser().execute(page, username=cand.handle)
                            if f_ok:
                                proactive_followed_count += 1
                                following_set.add(cand_handle)
                                cand.status = "followed"
                                await record_follow_action(prof.id, cand.handle, db, is_blue_tick=cand.is_blue_tick, niche=cand.niche)
                                await guard.record_action_success(prof.profile_slug, "follow")
                                await db.commit()
                                await sleep_with_jitter(3500)

                    # 4. GRACE PERIOD PRUNING (Protect TweepCred > 65):
                    # Check for accounts we followed > 4 days ago that did NOT follow back
                    now = datetime.datetime.utcnow()
                    exp_stmt = (
                        select(FollowRelationship)
                        .where(
                            FollowRelationship.profile_id == prof.id,
                            FollowRelationship.status == "following",
                            FollowRelationship.grace_period_expires_at <= now,
                        )
                        .limit(3)
                    )
                    exp_res = await db.execute(exp_stmt)
                    expired_rels = exp_res.scalars().all()

                    for exp_rel in expired_rels:
                        clean_exp = exp_rel.target_handle.lstrip("@").lower()
                        # If they actually followed back, mark as mutual
                        if clean_exp in followers_set:
                            exp_rel.status = "followed_back"
                            await db.commit()
                            continue

                        # Otherwise safely unfollow to maintain ratio
                        can_unfollow = await guard.is_action_safe(db, prof.profile_slug, "unfollow")
                        if not can_unfollow:
                            break

                        logger.info("✂️ Grace period expired (4 days) for @%s without reciprocal follow. Unfollowing to protect TweepCred...", exp_rel.target_handle)
                        unf_ok = await UnfollowUser().execute(page, username=exp_rel.target_handle)
                        if unf_ok:
                            pruned_count += 1
                            await record_unfollow_action(prof.id, exp_rel.target_handle, db)
                            await guard.record_action_success(prof.profile_slug, "unfollow")
                            await db.commit()
                            await sleep_with_jitter(2500)

                    results[prof.profile_slug] = {
                        "followed_back": followed_back_count,
                        "proactive_followed": proactive_followed_count,
                        "pruned": pruned_count,
                        "current_followers": len(current_followers),
                        "current_following": len(current_following),
                    }
                    logger.info("Completed growth cycle for %s: %s", prof.profile_slug, results[prof.profile_slug])

                except Exception as p_err:
                    logger.error("Error during growth cycle for %s: %s", prof.profile_slug, p_err, exc_info=True)
                    results[prof.profile_slug] = {"error": str(p_err)}
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(prof.profile_slug)

        return {"status": "success", "results": results}
    except Exception as e:
        logger.error("Failed overall growth cycle: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        await manager.stop()


def run_growth_and_autofollowback() -> dict[str, Any]:
    """Celery periodic task executing Auto Follow-Back and Proactive 500+ Verified Follower Growth."""
    logger.info("Starting Auto Follow-Back & Growth Celery task...")
    return asyncio.run(_run_growth_and_autofollowback_async())
