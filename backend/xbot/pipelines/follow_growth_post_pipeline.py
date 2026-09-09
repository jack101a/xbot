"""
Follow Growth & Visual Promotion Pipeline for XBot Pro.

Runs periodically (every 1 hour):
1. Synthesizes an engaging, high-converting growth/connection post with interactive CTA.
2. Generates an eye-catching 4:5 vertical portrait image via NVIDIA GenAI (Flux).
3. Publishes the post with the attached NVIDIA image to promote the account.
4. Scrapes active commenters from previous growth posts and executes reciprocal follow-backs + likes.
5. Persists state in database (Content, Actions, FollowCandidate, PipelineRun).
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from pathlib import Path
import re
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.growth_post_generator import generate_growth_post_with_image
from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.growth.f4f_engine import record_follow_action
from xbot.celery_app import celery_app
from xbot.database import AsyncSessionLocal
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona.loader import load_persona
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def run_follow_growth_post_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    container: Container | None = None,
) -> dict[str, Any]:
    """Executes an autonomous visual growth post cycle & commenter follow-back using BrowserPort."""
    profile_slug = profile.profile_slug
    clean_handle = profile.x_handle.lstrip("@")
    c = container or get_container()

    import time
    import random
    r = getattr(guard, "r", None)
    redis_key_next_due = f"xbot:growth_post:next_due:{profile_slug}"
    next_due_ts_str = r.get(redis_key_next_due) if r else None
    now_ts = int(time.time())

    if next_due_ts_str:
        try:
            next_due_ts = int(next_due_ts_str)
            if now_ts < next_due_ts:
                remaining_m = max(1, (next_due_ts - now_ts) // 60)
                logger.info(
                    "FollowGrowthPost: @%s in randomized 40-120m cadence window (%d mins remaining)",
                    clean_handle,
                    remaining_m,
                )
                return {"status": "skipped", "reason": f"interval_cooldown_{remaining_m}m"}
        except (ValueError, TypeError):
            pass

    # 1. Rate Limit & Safety Check
    can_post = await guard.can_act(db, profile_slug, "growth_post")
    if not can_post:
        logger.info("FollowGrowthPost: Skipped for @%s (daily growth post rate limit reached)", clean_handle)
        return {"status": "skipped", "reason": "growth_post_rate_limit"}

    session_file = Path(settings.BASE_PROFILE_DIR) / profile_slug / "storage_state.json"
    if not session_file.exists():
        logger.warning("FollowGrowthPost: Skipped for @%s (no storage_state.json auth session file)", clean_handle)
        return {"status": "skipped", "reason": "no_auth_session"}

    # 1b. Check if 3-day F4F growth research is due; if so, dispatch background task
    try:
        from xbot.growth.growth_researcher import is_growth_research_due, run_f4f_growth_research_task
        if is_growth_research_due(r):
            logger.info("FollowGrowthPost: 3-day F4F research cycle is due. Dispatching background research task...")
            run_f4f_growth_research_task.delay(profile_slug=profile_slug)
    except Exception as res_trigger_err:
        logger.debug("Could not dispatch F4F growth research task: %s", res_trigger_err)

    persona = None
    try:
        persona = load_persona(profile_slug)
    except Exception as e:
        logger.debug("Could not load custom persona for %s, using defaults: %s", profile_slug, e)

    post_published = False
    new_post_id: uuid.UUID | None = None
    followed_commenters_count = 0
    liked_comments_count = 0

    try:
        # 2. Determine current follower count from latest snapshot or profile config
        followers_count = 0
        if profile.config and "followers_count" in profile.config:
            try:
                followers_count = int(profile.config.get("followers_count") or 0)
            except Exception:
                followers_count = 0
        else:
            try:
                from xbot.models.analytics import AnalyticsSnapshot
                res_snap = await db.execute(
                    select(AnalyticsSnapshot)
                    .where(AnalyticsSnapshot.profile_id == profile.id)
                    .order_by(AnalyticsSnapshot.snapshot_at.desc())
                    .limit(1)
                )
                latest_snap = res_snap.scalar_one_or_none()
                if latest_snap and latest_snap.followers_count:
                    followers_count = int(latest_snap.followers_count)
            except Exception as snap_err:
                logger.debug("Could not read analytics snapshot for %s: %s", profile_slug, snap_err)

        # 3. Generate Dynamic Growth Copy & Image via AI
        logger.info(
            "FollowGrowthPost: Generating dynamic visual growth post for @%s (current followers: %d)...",
            clean_handle,
            followers_count,
        )
        growth_spec, image_path = await generate_growth_post_with_image(
            persona=persona,
            current_followers=followers_count,
        )
        if not growth_spec:
            logger.warning("FollowGrowthPost: AI growth generation returned None for @%s", clean_handle)
            return {"status": "failed", "reason": "generation_failed"}

        content_record = Content(
            profile_id=profile.id,
            content_type=ContentType.ORIGINAL,
            status=ContentStatus.APPROVED,
            body=growth_spec.tweet_copy,
            ai_metadata={
                "archetype": growth_spec.archetype,
                "cta_type": growth_spec.cta_type,
                "image_prompt": growth_spec.image_prompt,
                "image_path": image_path,
                "media_urls": [image_path],
                "is_growth_promotion": True,
                "target_milestone": growth_spec.target_milestone,
                "hashtags_count": growth_spec.hashtags_count,
            },
            posted_at=datetime.datetime.utcnow(),
        )
        db.add(content_record)
        await db.commit()
        await db.refresh(content_record)
        new_post_id = content_record.id

        # 4. Launch Browser & Publish Post via BrowserPort
        logger.info("FollowGrowthPost: Publishing growth post with image on X via BrowserPort...")
        media_to_send = [image_path] if (image_path and os.path.exists(image_path)) else None
        post_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.POST,
            params={
                "text": growth_spec.tweet_copy,
                "media_paths": media_to_send,
            },
            timeout_seconds=120,
        )
        post_res = await c.browser.execute(post_req)
        post_success = post_res.status in ("success", "posted") or (post_res.action_result and post_res.action_result.status == "success")

        if post_success:
            captured_id = None
            if post_res.action_result:
                captured_id = post_res.action_result.target_id or post_res.action_result.raw.get("tweet_id")
            if captured_id:
                content_record.tweet_id = str(captured_id)
            content_record.status = ContentStatus.POSTED
            post_published = True
            logger.info("FollowGrowthPost: Successfully published visual promotion on @%s (tweet_id=%s)", clean_handle, content_record.tweet_id)
            await guard.record_action(db, profile_slug, "growth_post", target_id=str(new_post_id))
            await db.commit()
        else:
            content_record.status = ContentStatus.FAILED
            logger.warning("FollowGrowthPost: Failed to publish post on X: %s", post_res.error)
            await db.commit()

        # 5. Commenter Harvesting & Reciprocal Follows on Growth Posts
        # Scan recent posted growth posts with tweet_ids to follow back interactive commenters
        past_growth_stmt = (
            select(Content)
            .where(
                Content.profile_id == profile.id,
                Content.status == ContentStatus.POSTED,
                Content.tweet_id.isnot(None),
            )
            .order_by(Content.posted_at.desc())
            .limit(3)
        )
        past_growth_res = await db.execute(past_growth_stmt)
        past_growth_posts = list(past_growth_res.scalars().all())

        if post_published and content_record.tweet_id and content_record not in past_growth_posts:
            past_growth_posts.insert(0, content_record)

        for past_post in past_growth_posts:
            if not past_post.tweet_id:
                continue
            tweet_url = f"https://x.com/{clean_handle}/status/{past_post.tweet_id}"
            logger.info("FollowGrowthPost: Harvesting commenters from growth post: %s", tweet_url)
            harvest_req = BrowserRequest(
                profile_slug=profile_slug,
                action=BrowserActionType.HARVEST_THREAD,
                params={"tweet_url": tweet_url, "max_candidates": 8},
                timeout_seconds=30,
            )
            harvest_res = await c.browser.execute(harvest_req)
            commenters = (
                harvest_res.scrape.candidates
                if (harvest_res.scrape and harvest_res.scrape.candidates)
                else []
            )

            for cand in commenters:
                cand_handle = (cand.get("handle") or "").lstrip("@").strip()
                if not cand_handle or cand_handle.lower() == clean_handle.lower():
                    continue

                existing_rel_stmt = (
                    select(FollowRelationship)
                    .where(
                        FollowRelationship.profile_id == profile.id,
                        FollowRelationship.target_handle == cand_handle,
                    )
                )
                rel_check = (await db.execute(existing_rel_stmt)).scalar_one_or_none()
                if rel_check and rel_check.status in ("following", "followed_back"):
                    continue

                can_follow = await guard.can_act(db, profile_slug, "follow", target_id=f"commenter_{cand_handle}")
                if not can_follow:
                    logger.info("FollowGrowthPost: Follow rate limit reached; pausing commenter follow-backs")
                    break

                logger.info("FollowGrowthPost: Reciprocally following commenter @%s from growth post...", cand_handle)
                follow_req = BrowserRequest(
                    profile_slug=profile_slug,
                    action=BrowserActionType.FOLLOW,
                    params={"username": cand_handle},
                    timeout_seconds=20,
                )
                f_res = await c.browser.execute(follow_req)
                if f_res.status in ("success", "followed") or (f_res.action_result and f_res.action_result.status == "success"):
                    is_blue = bool(cand.get("is_blue_tick"))
                    await record_follow_action(
                        profile_id=profile.id,
                        target_handle=cand_handle,
                        db=db,
                        is_blue_tick=is_blue,
                        niche="growth_commenter",
                    )
                    await guard.record_action(db, profile_slug, "follow", target_id=f"commenter_{cand_handle}")
                    followed_commenters_count += 1

    except Exception as e:
        logger.error("FollowGrowthPost: Error in growth cycle for @%s: %s", clean_handle, e, exc_info=True)
        return {"status": "error", "error": str(e)}

    # Schedule next random interval between 40 and 120 minutes (2400 to 7200 seconds)
    next_gap_sec = random.randint(40 * 60, 120 * 60)
    if r:
        r.set(redis_key_next_due, str(now_ts + next_gap_sec), ex=86400)
    logger.info(
        "FollowGrowthPost: Scheduled next growth cycle for @%s in %d mins (random 40-120m cadence)",
        clean_handle,
        next_gap_sec // 60,
    )

    return {
        "status": "success",
        "post_published": post_published,
        "post_id": str(new_post_id) if new_post_id else None,
        "followed_commenters": followed_commenters_count,
        "liked_comments": liked_comments_count,
    }


@celery_app.task(name="xbot.pipelines.follow_growth_post_pipeline.run_follow_growth_post")
def run_follow_growth_post() -> dict[str, Any]:
    """Celery entrypoint for periodic Follow Growth Promotion Pipeline."""
    async def _async_run():
        guard = CentralGuard()
        c = get_container()
        results = {}

        async with AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            profiles = res.scalars().all()

            for profile in profiles:
                r = await run_follow_growth_post_for_profile(db, profile, guard, container=c)
                results[profile.profile_slug] = r

                run_status = "success" if r.get("status") == "success" else ("skipped" if r.get("status") == "skipped" else "failed")
                prun = PipelineRun(
                    profile_id=profile.id,
                    pipeline_name="follow_growth_post",
                    status=run_status,
                    actions_count=(1 if r.get("post_published") else 0) + r.get("followed_commenters", 0),
                    details=r,
                )
                db.add(prun)
                await db.commit()

        return results

    return asyncio.run(_async_run())
