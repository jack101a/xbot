"""
Reply Pipeline Orchestration and Celery Entrypoint.
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
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.central_guard import CentralGuard
from xbot.pipelines.reply_pipeline.generator import (
    execute_fast_response_replies,
    execute_feed_replies,
)
from xbot.pipelines.reply_pipeline.kol_sniper import execute_kol_sniper_replies

logger = logging.getLogger(__name__)


def _get_pkg():
    return sys.modules.get("xbot.pipelines.reply_pipeline") or sys.modules[__name__]


async def run_reply_pipeline_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_total_replies: int = 4,
) -> dict[str, Any]:
    """Executes full unified reply cycle for a profile."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug

    can_proceed = await guard.can_act(db, profile_slug, "reply")
    if not can_proceed:
        return {"status": "skipped", "reason": "guard_check_failed", "replies_executed": 0}

    # 1. Sniper KOL replies
    sniper_count = await pkg.execute_kol_sniper_replies(db, profile, guard, max_replies=2)

    # 2. Fast response conversation follow-ups
    sentinel_count = 0
    if sniper_count < max_total_replies:
        sentinel_count = await pkg.execute_fast_response_replies(
            db, profile, guard, max_replies=(max_total_replies - sniper_count)
        )

    # 3. Feed Opportunity Replies (if remaining budget)
    feed_count = 0
    remaining_budget = max_total_replies - (sniper_count + sentinel_count)
    if remaining_budget > 0:
        feed_count = await pkg.execute_feed_replies(db, profile, guard, max_replies=remaining_budget)

    total_replies = sniper_count + sentinel_count + feed_count
    return {
        "status": "success",
        "replies_executed": total_replies,
        "sniper_replies": sniper_count,
        "sentinel_replies": sentinel_count,
        "feed_replies": feed_count,
    }


async def _run_reply_pipeline_async() -> dict[str, Any]:
    pkg = _get_pkg()
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_replies = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await pkg.run_reply_pipeline_for_profile(db, profile, guard)
                results_by_profile[profile.profile_slug] = res
                total_replies += res.get("replies_executed", 0)

                run_log = PipelineRun(
                    pipeline_name="reply",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("replies_executed", 0),
                    details=res,
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

            except Exception as e:
                logger.error("ReplyPipeline: Error processing profile %s: %s", profile.profile_slug, e, exc_info=True)
                run_log = PipelineRun(
                    pipeline_name="reply",
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
        "pipeline": "reply",
        "total_replies": total_replies,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.reply_pipeline.run_reply_pipeline")
def run_reply_pipeline() -> dict[str, Any]:
    """Celery task entry point for Unified Reply Pipeline."""
    return asyncio.run(_run_reply_pipeline_async())
