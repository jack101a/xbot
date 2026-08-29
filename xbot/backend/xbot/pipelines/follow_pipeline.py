"""
Independent Follow Pipeline for XBot Pro.

Runs every 10 minutes (during active hours: 6:00 AM - 2:00 AM IST):
1. Audits live followers and notification events on X.
2. Instantly executes reciprocal follow-backs for all new followers.
3. Proactively follows high-reciprocity verified blue-tick creators in the target niche.
4. Prunes unreciprocated follows outside the 4-day grace period to safeguard TweepCred (>65).
5. Enforces CentralGuard rate limits and logs in PipelineRun.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.browser.actions.x_actions import FollowUser, ScrapeFollowList, UnfollowUser
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter
from xbot.database import AsyncSessionLocal
from xbot.growth.f4f_engine import populate_f4f_candidates, record_follow_action, record_unfollow_action
from xbot.models.analytics import AnalyticsSnapshot, FollowerChangeLog
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def run_follow_pipeline_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    manager: BrowserManager,
) -> dict[str, Any]:
    """Executes follow and reciprocity cycle for a profile."""
    profile_slug = profile.profile_slug
    clean_handle = profile.x_handle.lstrip("@")

    can_proceed = await guard.can_act(db, profile_slug, "follow")
    if not can_proceed:
        return {"status": "skipped", "reason": "guard_check_failed", "actions_executed": 0}

    lock_acquired = False
    for _ in range(3):
        if manager.acquire_lock(profile_slug, timeout_seconds=120):
            lock_acquired = True
            break
        await asyncio.sleep(1.5)

    if not lock_acquired:
        return {"status": "skipped", "reason": "browser_lock_busy", "actions_executed": 0}

    context = None
    followed_back_count = 0
    proactive_followed_count = 0
    pruned_count = 0

    try:
        context = await manager.get_context(profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        # 1. Scrape followers & following
        logger.info("FollowPipeline: Scanning live followers & following for @%s...", clean_handle)
        current_followers = await ScrapeFollowList().execute(page, username=clean_handle, list_type="followers", limit=100, verified_only=False)
        current_following = await ScrapeFollowList().execute(page, username=clean_handle, list_type="following", limit=100, verified_only=False)

        # 1b. Check Notifications for new followers
        try:
            await page.goto("https://x.com/notifications", wait_until="domcontentloaded", timeout=20000)
            await sleep_with_jitter(2000)
            notif_articles = await page.query_selector_all("article, [data-testid='cellInnerDiv']")
            for notif in notif_articles[:25]:
                notif_text = await notif.inner_text()
                if "followed you" in notif_text.lower():
                    links = await notif.query_selector_all("a[href^='/']")
                    for link in links:
                        href = await link.get_attribute("href") or ""
                        cand = href.strip("/")
                        if cand and "/" not in cand and cand.lower() not in [
                            "home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings", clean_handle.lower()
                        ]:
                            if cand not in current_followers:
                                current_followers.append(cand)
        except Exception as notif_err:
            logger.debug("FollowPipeline notifications scan: %s", notif_err)

        followers_set = {f.lstrip("@").lower() for f in current_followers}
        following_set = {f.lstrip("@").lower() for f in current_following}

        if current_followers or current_following:
            snap = AnalyticsSnapshot(
                profile_id=profile.id,
                snapshot_date=datetime.date.today(),
                followers=len(current_followers),
                following=len(current_following),
                captured_at=datetime.datetime.utcnow(),
            )
            db.add(snap)
            await db.commit()

        # 2. Reciprocal follow-backs (Follow all users who follow us)
        missing_reciprocal = [f for f in followers_set if f not in following_set and f != clean_handle.lower()]
        logger.info("FollowPipeline: Found %d users who follow us whom we haven't followed back.", len(missing_reciprocal))

        for target_user in missing_reciprocal[:5]:
            can_follow = await guard.can_act(db, profile_slug, "follow", target_id=f"follow_{target_user}")
            if not can_follow:
                break

            logger.info("Executing reciprocal follow-back on @%s...", target_user)
            follow_res = await FollowUser().execute(page, username=target_user)
            if follow_res.get("status") in ("followed", "already_following"):
                await record_follow_action(db, profile.id, target_user, is_proactive=False, is_reciprocal=True)
                await guard.record_action(db, profile_slug, "follow", target_id=f"follow_{target_user}")
                followed_back_count += 1
                await sleep_with_jitter(3000)

        # 3. Proactive verified blue-tick follows
        if followed_back_count < 3:
            await populate_f4f_candidates(profile.id, db)

            cands_res = await db.execute(
                select(FollowCandidate)
                .where(
                    FollowCandidate.profile_id == profile.id,
                    FollowCandidate.is_followed.is_(False),
                )
                .order_by(FollowCandidate.reciprocity_score.desc())
                .limit(2)
            )
            top_candidates = cands_res.scalars().all()

            for cand in top_candidates:
                target_user = cand.target_handle.lstrip("@").lower()
                if target_user in following_set:
                    cand.is_followed = True
                    await db.commit()
                    continue

                can_follow = await guard.can_act(db, profile_slug, "follow", target_id=f"follow_{target_user}")
                if not can_follow:
                    break

                logger.info("Executing proactive follow on candidate @%s...", target_user)
                follow_res = await FollowUser().execute(page, username=target_user)
                if follow_res.get("status") in ("followed", "already_following"):
                    cand.is_followed = True
                    cand.followed_at = datetime.datetime.utcnow()
                    await record_follow_action(db, profile.id, target_user, is_proactive=True, is_reciprocal=False)
                    await guard.record_action(db, profile_slug, "follow", target_id=f"follow_{target_user}")
                    proactive_followed_count += 1
                    await sleep_with_jitter(3000)

        # 4. Pruning non-mutual accounts (outside 4-day grace period)
        grace_period_cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=4)
        stale_res = await db.execute(
            select(FollowRelationship)
            .where(
                FollowRelationship.profile_id == profile.id,
                FollowRelationship.is_following.is_(True),
                FollowRelationship.is_followed_back.is_(False),
                FollowRelationship.followed_at < grace_period_cutoff,
            )
            .limit(2)
        )
        stale_relations = stale_res.scalars().all()

        for rel in stale_relations:
            target_user = rel.target_handle.lstrip("@").lower()
            if target_user in followers_set:
                rel.is_followed_back = True
                await db.commit()
                continue

            can_unfollow = await guard.can_act(db, profile_slug, "unfollow", target_id=f"unfollow_{target_user}")
            if not can_unfollow:
                break

            logger.info("Pruning unreciprocated follow @%s after 4-day grace period...", target_user)
            unf_res = await UnfollowUser().execute(page, username=target_user)
            if unf_res.get("status") in ("unfollowed", "not_following"):
                await record_unfollow_action(db, profile.id, target_user)
                await guard.record_action(db, profile_slug, "unfollow", target_id=f"unfollow_{target_user}")
                pruned_count += 1
                await sleep_with_jitter(3000)

    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        manager.release_lock(profile_slug)

    total_actions = followed_back_count + proactive_followed_count + pruned_count
    return {
        "status": "success",
        "actions_executed": total_actions,
        "followed_back": followed_back_count,
        "proactive_followed": proactive_followed_count,
        "pruned": pruned_count,
    }


async def _run_follow_pipeline_async() -> dict[str, Any]:
    guard = CentralGuard()
    manager = BrowserManager()
    started_at = datetime.datetime.utcnow()
    total_actions = 0
    results_by_profile: dict[str, Any] = {}

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            profiles = (await db.execute(stmt)).scalars().all()

            for profile in profiles:
                try:
                    res = await run_follow_pipeline_for_profile(db, profile, guard, manager)
                    results_by_profile[profile.profile_slug] = res
                    total_actions += res.get("actions_executed", 0)

                    run_log = PipelineRun(
                        pipeline_name="follow",
                        profile_id=profile.id,
                        status=res.get("status", "success"),
                        actions_count=res.get("actions_executed", 0),
                        details=res,
                        started_at=started_at,
                        completed_at=datetime.datetime.utcnow(),
                    )
                    db.add(run_log)
                    await db.commit()

                except Exception as e:
                    logger.error("FollowPipeline: Error for profile %s: %s", profile.profile_slug, e, exc_info=True)
                    run_log = PipelineRun(
                        pipeline_name="follow",
                        profile_id=profile.id,
                        status="failed",
                        actions_count=0,
                        error_message=str(e),
                        started_at=started_at,
                        completed_at=datetime.datetime.utcnow(),
                    )
                    db.add(run_log)
                    await db.commit()

    finally:
        try:
            await manager.stop()
        except Exception:
            pass

    return {
        "pipeline": "follow",
        "total_actions": total_actions,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.follow_pipeline.run_follow_pipeline")
def run_follow_pipeline() -> dict[str, Any]:
    """Celery task entry point for Follow Pipeline."""
    return asyncio.run(_run_follow_pipeline_async())

