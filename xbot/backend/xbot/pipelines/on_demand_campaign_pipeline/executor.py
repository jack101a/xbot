"""
On-Demand Campaign Deliverables Publisher and Scheduler.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import AsyncSessionLocal
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.profile import Profile
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, process_browser_queue
from xbot.pipelines.on_demand_campaign_pipeline.prompts import CAMPAIGN_TRACKER

logger = logging.getLogger(__name__)


async def publish_campaign_deliverables(
    campaign_id: str,
    content_ids: list[str],
    mode: str,
    interval_minutes: int = 60,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Publishes selected deliverables either instantly (via BrowserQueue) or
    schedules them by setting status = APPROVED.
    """
    if db is None:
        async with AsyncSessionLocal() as session:
            return await publish_campaign_deliverables(campaign_id, content_ids, mode, interval_minutes, session)

    target_uuids = [uuid.UUID(cid) for cid in content_ids]
    stmt = select(Content).where(Content.id.in_(target_uuids))
    records = (await db.execute(stmt)).scalars().all()

    published_count = 0
    now = datetime.datetime.utcnow()

    for idx, rec in enumerate(records):
        rec.status = ContentStatus.APPROVED
        meta = dict(rec.ai_metadata or {})

        # Fetch profile slug
        prof = (await db.execute(select(Profile).where(Profile.id == rec.profile_id))).scalar_one_or_none()
        profile_slug = prof.profile_slug if prof else "test_profile1"

        if mode == "instant":
            # Direct immediate queue dispatch
            meta["scheduled_for"] = now.isoformat()
            rec.ai_metadata = meta
            await db.commit()

            try:
                if rec.content_type in (ContentType.POLL, "poll"):
                    meta_poll = meta.get("poll", {})
                    q = meta_poll.get("question") or rec.body.split("\n")[0]
                    opts = meta_poll.get("options") or ["Yes", "No"]
                    duration_days = meta_poll.get("duration_days", 1)
                    enqueue_browser_job(BrowserJob(
                        action_type="poll",
                        profile_slug=profile_slug,
                        params={"question": q, "options": opts, "duration_minutes": duration_days * 1440},
                        priority=1,
                    ))
                elif rec.content_type in (ContentType.THREAD, "thread"):
                    tweets = []
                    if getattr(rec, "thread_items", None) and len(rec.thread_items) > 0:
                        tweets = [item.text for item in rec.thread_items]
                    elif "thread_items" in meta and isinstance(meta["thread_items"], list):
                        tweets = meta["thread_items"]
                    elif "tweets" in meta and isinstance(meta["tweets"], list):
                        tweets = meta["tweets"]
                    else:
                        tweets = [p.strip() for p in rec.body.split("\n\n") if p.strip()]
                    media_paths = meta.get("media_paths")
                    enqueue_browser_job(BrowserJob(
                        action_type="thread",
                        profile_slug=profile_slug,
                        params={"tweets": tweets, "media_paths": media_paths},
                        priority=1,
                    ))
                else:
                    media_paths = meta.get("media_paths")
                    gif_q = meta.get("gif_query")
                    enqueue_browser_job(BrowserJob(
                        action_type="post",
                        profile_slug=profile_slug,
                        params={"text": rec.body, "media_paths": media_paths, "gif_query": gif_q},
                        priority=1,
                    ))
            except Exception as q_err:
                logger.warning("Could not enqueue direct browser job for deliverable %s: %s", rec.id, q_err)

            published_count += 1
        else:
            # Staggered schedule: space out items
            meta["scheduled_for"] = (now + datetime.timedelta(minutes=idx * interval_minutes)).isoformat()
            rec.ai_metadata = meta
            await db.commit()
            published_count += 1

    # Update in-memory tracker deliverable status
    if campaign_id in CAMPAIGN_TRACKER:
        c_status = CAMPAIGN_TRACKER[campaign_id]
        if "deliverables" in c_status:
            for d in c_status["deliverables"]:
                if d.get("content_id") in content_ids:
                    d["status"] = "queued" if mode == "instant" else "scheduled"

    # Trigger background Celery workers
    try:
        from xbot.tasks import auto_publish_pending_drafts
        auto_publish_pending_drafts.delay()
    except Exception:
        pass

    try:
        process_browser_queue.delay()
    except Exception:
        pass

    logger.info("Published/Scheduled %d deliverables for campaign %s in %s mode", published_count, campaign_id, mode)

    return {
        "status": "success",
        "campaign_id": campaign_id,
        "mode": mode,
        "items_updated": published_count,
    }
