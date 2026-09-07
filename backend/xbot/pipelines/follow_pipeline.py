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

from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
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
    container: Container | None = None,
) -> dict[str, Any]:
    """Executes follow and reciprocity cycle for a profile using BrowserPort."""
    profile_slug = profile.profile_slug
    clean_handle = profile.x_handle.lstrip("@")
    c = container or get_container()

    can_proceed = await guard.can_act(db, profile_slug, "follow")
    if not can_proceed:
        return {"status": "skipped", "reason": "guard_check_failed", "actions_executed": 0}

    followed_back_count = 0
    proactive_followed_count = 0
    pruned_count = 0

    # 1. Scrape verified_followers, regular followers & following via BrowserPort
    logger.info("FollowPipeline: Scanning verified_followers, followers & following for @%s...", clean_handle)
    verified_res = await c.browser.execute(
        BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SCRAPE_FOLLOW_LIST,
            params={"username": clean_handle, "list_type": "verified_followers", "limit": 100},
            timeout_seconds=30,
        )
    )
    def _extract_handles(resp: Any) -> list[str]:
        if not resp:
            return []
        if resp.scrape and resp.scrape.follow_list and resp.scrape.follow_list.handles:
            return resp.scrape.follow_list.handles
        if resp.scrape and resp.scrape.raw:
            raw = resp.scrape.raw
            if isinstance(raw.get("follow_list"), dict) and raw["follow_list"].get("handles"):
                return raw["follow_list"]["handles"]
            if isinstance(raw.get("handles"), list) and raw["handles"]:
                return raw["handles"]
            if isinstance(raw.get("followers"), list) and raw["followers"]:
                return raw["followers"]
        return []

    verified_followers = _extract_handles(verified_res)

    followers_res = await c.browser.execute(
        BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SCRAPE_FOLLOW_LIST,
            params={"username": clean_handle, "list_type": "followers", "limit": 100},
            timeout_seconds=30,
        )
    )
    current_followers = _extract_handles(followers_res)

    following_res = await c.browser.execute(
        BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SCRAPE_FOLLOW_LIST,
            params={"username": clean_handle, "list_type": "following", "limit": 100},
            timeout_seconds=30,
        )
    )
    current_following = _extract_handles(following_res)

    # Merge verified followers into full follower list
    for vf in verified_followers:
        if vf not in current_followers:
            current_followers.append(vf)

    # 1b. Check Notifications for new followers via BrowserPort
    try:
        notifs_res = await c.browser.execute(
            BrowserRequest(
                profile_slug=profile_slug,
                action=BrowserActionType.SCRAPE_NOTIFICATIONS,
                params={"limit": 25},
                timeout_seconds=30,
            )
        )
        if notifs_res.scrape and notifs_res.scrape.notifications:
            for n in notifs_res.scrape.notifications:
                if n.kind == "follow" and n.actor_handle:
                    cand = n.actor_handle.lstrip("@").strip()
                    if cand and cand not in current_followers:
                        current_followers.append(cand)
    except Exception as notif_err:
        logger.debug("FollowPipeline notifications scan: %s", notif_err)

    followers_set = {f.lstrip("@").lower() for f in current_followers}
    following_set = {f.lstrip("@").lower() for f in current_following}
    verified_set = {f.lstrip("@").lower() for f in verified_followers}

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

    # 2. Reciprocal follow-backs (Priority 1: Verified Followers -> Priority 2: General Followers)
    missing_verified = [f for f in verified_set if f not in following_set and f != clean_handle.lower()]
    missing_general = [f for f in followers_set if f not in following_set and f != clean_handle.lower() and f not in missing_verified]
    missing_reciprocal = missing_verified + missing_general

    logger.info(
        "FollowPipeline: Found %d users who follow us (including %d verified followers) whom we haven't followed back.",
        len(missing_reciprocal),
        len(missing_verified),
    )

    for target_user in missing_reciprocal[:10]:
        can_follow = await guard.can_act(db, profile_slug, "follow", target_id=f"follow_{target_user}")
        if not can_follow:
            break

        is_vf = target_user in verified_set
        logger.info("Executing reciprocal follow-back on @%s (Verified: %s)...", target_user, is_vf)
        follow_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.FOLLOW,
            params={"username": target_user},
            timeout_seconds=20,
        )
        follow_res = await c.browser.execute(follow_req)
        if follow_res.status in ("success", "followed") or (follow_res.action_result and follow_res.action_result.status == "success"):
            await record_follow_action(profile_id=profile.id, target_handle=target_user, db=db)
            await guard.record_action(db, profile_slug, "follow", target_id=f"follow_{target_user}")
            followed_back_count += 1

    # 3. Proactive verified blue-tick follows
    if followed_back_count < 3:
        await populate_f4f_candidates(profile.id, db, container=c, profile_slug=profile_slug)

        cands_res = await db.execute(
            select(FollowCandidate)
            .where(
                FollowCandidate.profile_id == profile.id,
                FollowCandidate.status == "discovered",
            )
            .order_by(FollowCandidate.reciprocity_score.desc())
            .limit(2)
        )
        top_candidates = cands_res.scalars().all()

        for cand in top_candidates:
            target_user = cand.handle.lstrip("@").lower()
            if target_user in following_set:
                cand.status = "followed"
                await db.commit()
                continue

            can_follow = await guard.can_act(db, profile_slug, "follow", target_id=f"follow_{target_user}")
            if not can_follow:
                break

            logger.info("Executing proactive follow on candidate @%s...", target_user)
            follow_req = BrowserRequest(
                profile_slug=profile_slug,
                action=BrowserActionType.FOLLOW,
                params={"username": target_user},
                timeout_seconds=20,
            )
            follow_res = await c.browser.execute(follow_req)
            if follow_res.status in ("success", "followed") or (follow_res.action_result and follow_res.action_result.status == "success"):
                cand.status = "followed"
                await record_follow_action(profile_id=profile.id, target_handle=target_user, db=db)
                await guard.record_action(db, profile_slug, "follow", target_id=f"follow_{target_user}")
                proactive_followed_count += 1

    # 4. Pruning non-mutual accounts (outside 4-day grace period)
    grace_period_cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=4)
    stale_res = await db.execute(
        select(FollowRelationship)
        .where(
            FollowRelationship.profile_id == profile.id,
            FollowRelationship.status == "following",
            FollowRelationship.followed_at < grace_period_cutoff,
        )
        .limit(2)
    )
    stale_relations = stale_res.scalars().all()

    for rel in stale_relations:
        target_user = rel.target_handle.lstrip("@").lower()
        if target_user in followers_set:
            rel.status = "followed_back"
            await db.commit()
            continue

        can_unfollow = await guard.can_act(db, profile_slug, "unfollow", target_id=f"unfollow_{target_user}")
        if not can_unfollow:
            break

        logger.info("Pruning unreciprocated follow @%s after 4-day grace period...", target_user)
        unf_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.UNFOLLOW,
            params={"username": target_user},
            timeout_seconds=20,
        )
        unf_res = await c.browser.execute(unf_req)
        raw_detail = (unf_res.action_result.raw if (unf_res.action_result and unf_res.action_result.raw) else {}) or {}
        if unf_res.status == "skipped" or raw_detail.get("reason") == "mutual_follower":
            logger.info("Mutual follower protected: User @%s follows us back! Marking as followed_back in DB.", target_user)
            rel.status = "followed_back"
            await db.commit()
            continue
        elif unf_res.status in ("success", "unfollowed") or (unf_res.action_result and unf_res.action_result.status == "success"):
            rel.status = "unfollowed"
            rel.unfollowed_at = datetime.datetime.utcnow()
            await record_unfollow_action(profile_id=profile.id, target_handle=target_user, db=db)
            await guard.record_action(db, profile_slug, "unfollow", target_id=f"unfollow_{target_user}")
            pruned_count += 1
        else:
            rel.status = "unfollowed"
            rel.unfollowed_at = datetime.datetime.utcnow()
            await db.commit()

    total_actions = followed_back_count + proactive_followed_count + pruned_count
    return {
        "status": "success",
        "actions_executed": total_actions,
        "followed_back": followed_back_count,
        "proactive_followed": proactive_followed_count,
        "pruned": pruned_count,
    }


async def _run_follow_pipeline_async(container: Container | None = None) -> dict[str, Any]:
    c = container or get_container()
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_actions = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await run_follow_pipeline_for_profile(db, profile, guard, container=c)
                results_by_profile[profile.profile_slug] = res
                total_actions += res.get("actions_executed", 0)

                run_log = PipelineRun(
                    pipeline_name="follow",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("actions_executed", 0),
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                    details={"duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(), "results": res},
                )
                db.add(run_log)
                await db.commit()
            except Exception as e:
                logger.error("Error running follow pipeline for %s: %s", profile.profile_slug, e, exc_info=True)
    return {
        "status": "success",
        "actions_executed": total_actions,
        "results_by_profile": results_by_profile,
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.follow_pipeline.run_follow_pipeline")
def run_follow_pipeline() -> dict[str, Any]:
    """Celery task entry point for Follow Pipeline."""
    return asyncio.run(_run_follow_pipeline_async())

