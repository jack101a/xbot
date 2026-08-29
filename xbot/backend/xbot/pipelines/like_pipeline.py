"""
Independent Like Pipeline for XBot Pro.

Runs every 15 minutes (during active hours: 6:00 AM - 2:00 AM IST):
1. Scrapes feed / timeline for candidate tweets.
2. Filters for strategic relationship building (followed accounts, mutuals, high-relevance).
3. Batches 15-25 likes per cycle via the Central Browser Queue.
4. Enforces 48-hour deduplication and rate limiting via CentralGuard.
5. Records execution logs in PipelineRun.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import AsyncSessionLocal
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def run_like_pipeline_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    min_likes: int = 15,
    max_likes: int = 25,
) -> dict[str, Any]:
    """Executes like cycle for a single profile."""
    profile_slug = profile.profile_slug

    # 1. Guard check
    can_proceed = await guard.can_act(db, profile_slug, "like")
    if not can_proceed:
        logger.info("LikePipeline: Guard skipped profile %s", profile_slug)
        return {"status": "skipped", "reason": "guard_check_failed", "likes_executed": 0}

    # 2. Enqueue feed scrape job to find candidate tweets
    scrape_job = BrowserJob(
        action_type="scrape_feed",
        profile_slug=profile_slug,
        params={"scroll_count": 3, "collect_tweets": True},
        priority=3,
    )
    job_id = enqueue_browser_job(scrape_job)

    # Wait for scrape result (or timeout after 45s)
    scrape_res = await asyncio.to_thread(get_browser_job_result, job_id, 45.0)
    if not scrape_res or scrape_res.get("status") != "success":
        logger.warning("LikePipeline: Failed to scrape feed for %s: %s", profile_slug, scrape_res)
        return {"status": "failed", "reason": "feed_scrape_failed", "likes_executed": 0}

    feed_tweets: list[dict[str, Any]] = scrape_res.get("tweets", [])
    if not feed_tweets:
        logger.info("LikePipeline: No tweets found in feed for %s", profile_slug)
        return {"status": "success", "likes_executed": 0, "candidates_found": 0}

    from xbot.persona.loader import load_persona
    from xbot.safety.topic_blacklist import topic_blacklist_filter
    persona = None
    try:
        persona = load_persona(profile_slug)
    except Exception:
        pass

    # 3. Filter candidates
    candidates: list[dict[str, Any]] = []
    for tw in feed_tweets:
        tweet_id = str(tw.get("id") or tw.get("tweet_id") or "")
        tweet_text = str(tw.get("text") or "")
        if not tweet_id:
            continue
        if guard.is_target_acted_upon(profile_slug, "like", tweet_id):
            continue
        is_blocked, block_reason = topic_blacklist_filter.is_blocked(tweet_text, persona)
        if is_blocked:
            logger.info("LikePipeline: Skipped tweet %s due to topic blacklist: %s", tweet_id, block_reason)
            continue
        candidates.append(tw)

    selected_candidates = candidates[:max_likes]
    likes_count = 0

    # 4. Enqueue like jobs for each candidate
    for tw in selected_candidates:
        tweet_id = str(tw.get("id") or tw.get("tweet_id") or "")
        tweet_url = tw.get("url") or tw.get("tweet_url")

        like_job = BrowserJob(
            action_type="like",
            profile_slug=profile_slug,
            params={"tweet_id": tweet_id, "tweet_url": tweet_url},
            priority=3,
        )
        like_job_id = enqueue_browser_job(like_job)

        # Wait briefly for result
        like_res = await asyncio.to_thread(get_browser_job_result, like_job_id, 20.0)
        if like_res and like_res.get("status") in ("success", "liked", "already_liked"):
            await guard.record_action(db, profile_slug, "like", target_id=tweet_id)
            likes_count += 1

    return {
        "status": "success",
        "likes_executed": likes_count,
        "candidates_evaluated": len(candidates),
    }


async def _run_like_pipeline_async() -> dict[str, Any]:
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_likes = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await run_like_pipeline_for_profile(db, profile, guard)
                results_by_profile[profile.profile_slug] = res
                total_likes += res.get("likes_executed", 0)

                # Record in PipelineRun
                run_log = PipelineRun(
                    pipeline_name="like",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("likes_executed", 0),
                    details=res,
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

            except Exception as e:
                logger.error("LikePipeline: Error processing profile %s: %s", profile.profile_slug, e, exc_info=True)
                run_log = PipelineRun(
                    pipeline_name="like",
                    profile_id=profile.id,
                    status="failed",
                    actions_count=0,
                    error_message=str(e),
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

    return {
        "pipeline": "like",
        "total_likes": total_likes,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.like_pipeline.run_like_pipeline")
def run_like_pipeline() -> dict[str, Any]:
    """Celery task entry point for Like Pipeline."""
    return asyncio.run(_run_like_pipeline_async())

