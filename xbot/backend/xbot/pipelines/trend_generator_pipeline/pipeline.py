"""
Trend Generator Pipeline Generation and Execution.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import AsyncSessionLocal
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.pipeline import PipelineRun, ResearchedTopic
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, process_browser_queue
from xbot.pipelines.central_guard import CentralGuard
from xbot.pipelines.trend_generator_pipeline.collector import (
    _get_default_persona,
    _get_persona_for_profile,
)
from xbot.pipelines.trend_generator_pipeline.scorer import determine_creation_format
from xbot.pipelines.trend_generator_pipeline.synthesizers import (
    synthesize_poll_topic,
    synthesize_post_topic,
    synthesize_thread_topic,
    synthesize_visual_topic,
)

logger = logging.getLogger(__name__)


def _get_pkg():
    return sys.modules.get("xbot.pipelines.trend_generator_pipeline") or sys.modules[__name__]


async def generate_content_for_topic(
    db: AsyncSession,
    profile: Profile,
    topic: ResearchedTopic,
    guard: CentralGuard,
) -> dict[str, Any]:
    """Synthesizes and stages a post/thread/poll/visual spec for a researched topic."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug
    gatekeeper = pkg.AntiAIGatekeeper()
    persona = _get_persona_for_profile(profile_slug) or _get_default_persona(profile)

    has_media = bool(topic.media_paths)
    media_to_attach = topic.media_paths[:4] if topic.media_paths else []

    creation_format = determine_creation_format(topic, persona)
    logger.info("TrendGenerator: Routing topic '%s' to format '%s'", topic.topic, creation_format)

    if creation_format == "visual":
        content_record = await synthesize_visual_topic(db, profile, topic, persona, media_to_attach, gatekeeper, profile_slug, pkg)
    elif creation_format == "thread":
        content_record = await synthesize_thread_topic(db, profile, topic, persona, media_to_attach, profile_slug, pkg)
    elif creation_format == "poll":
        content_record = await synthesize_poll_topic(db, profile, topic, persona, pkg)
    else:
        content_record = await synthesize_post_topic(db, profile, topic, persona, media_to_attach, has_media, gatekeeper, profile_slug, pkg)

    # Mark topic processed
    topic.processed = True
    await db.commit()

    # Automatically post live to X via browser queue
    try:
        if content_record.content_type in (ContentType.POLL, "poll"):
            meta_poll = content_record.ai_metadata.get("poll", {}) if content_record.ai_metadata else {}
            enqueue_browser_job(BrowserJob(
                action_type="poll",
                profile_slug=profile.profile_slug,
                params={"question": meta_poll.get("question") or content_record.body, "options": meta_poll.get("options") or ["Yes", "No"], "duration_minutes": 1440},
                priority=1,
            ))
        elif content_record.content_type in (ContentType.THREAD, "thread"):
            t_items = content_record.ai_metadata.get("thread_items", []) if content_record.ai_metadata else []
            enqueue_browser_job(BrowserJob(
                action_type="thread",
                profile_slug=profile.profile_slug,
                params={"tweets": t_items, "media_paths": media_to_attach},
                priority=1,
            ))
        else:
            meta = content_record.ai_metadata or {}
            enqueue_browser_job(BrowserJob(
                action_type="post",
                profile_slug=profile.profile_slug,
                params={
                    "text": content_record.body,
                    "media_paths": meta.get("media_paths"),
                    "gif_query": meta.get("gif_query"),
                },
                priority=1,
            ))
            process_browser_queue.delay()
    except Exception as auto_p_err:
        logger.warning("Auto-publish dispatch skipped: %s", auto_p_err)

    logger.info(
        "TrendGenerator: Successfully generated and dispatched %s (%s) for topic '%s'",
        content_record.content_type,
        creation_format,
        topic.topic,
    )
    return {
        "status": "success",
        "content_id": str(content_record.id),
        "content_type": content_record.content_type.value if hasattr(content_record.content_type, "value") else str(content_record.content_type),
        "creation_format": creation_format,
        "topic": topic.topic,
    }


async def run_trend_generator_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_items: int = 2,
) -> dict[str, Any]:
    """Generates content from pending researched topics for a profile."""
    pkg = _get_pkg()
    stmt = (
        select(ResearchedTopic)
        .where(
            ResearchedTopic.profile_id == profile.id,
            ResearchedTopic.processed.is_(False),
        )
        .order_by(ResearchedTopic.created_at.desc())
        .limit(max_items)
    )
    pending_topics = (await db.execute(stmt)).scalars().all()
    if not pending_topics:
        return {"status": "success", "items_generated": 0, "message": "No pending researched topics"}

    generated_count = 0
    generated_details: list[dict[str, Any]] = []

    for topic in pending_topics:
        try:
            res = await pkg.generate_content_for_topic(db, profile, topic, guard)
            if res.get("status") == "success":
                generated_count += 1
                generated_details.append(res)
        except Exception as e:
            logger.error("TrendGenerator: Error generating for topic '%s': %s", topic.topic, e, exc_info=True)

    return {
        "status": "success",
        "items_generated": generated_count,
        "details": generated_details,
    }


async def _run_trend_generator_async() -> dict[str, Any]:
    pkg = _get_pkg()
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_generated = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await pkg.run_trend_generator_for_profile(db, profile, guard)
                results_by_profile[profile.profile_slug] = res
                total_generated += res.get("items_generated", 0)

                run_log = PipelineRun(
                    pipeline_name="trend_generator",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("items_generated", 0),
                    details=res,
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

            except Exception as e:
                logger.error("TrendGenerator: Error for profile %s: %s", profile.profile_slug, e, exc_info=True)
                run_log = PipelineRun(
                    pipeline_name="trend_generator",
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
        "pipeline": "trend_generator",
        "total_generated": total_generated,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.trend_generator_pipeline.run_trend_generator")
def run_trend_generator() -> dict[str, Any]:
    """Celery task entry point for Trend Generator Pipeline."""
    return asyncio.run(_run_trend_generator_async())
