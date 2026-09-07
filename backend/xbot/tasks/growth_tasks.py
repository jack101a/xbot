from __future__ import annotations

import asyncio
import logging
from typing import Any

from xbot.celery_app import celery_app

logger = logging.getLogger("xbot.tasks.growth")


async def _run_growth_and_autofollowback_async() -> dict[str, Any]:
    """
    Periodic Growth & Follow-Back Engine (runs every 10-15 minutes):
    Delegates to the central queue-driven follow pipeline.
    """
    from xbot.pipelines.follow_pipeline import _run_follow_pipeline_async
    return await _run_follow_pipeline_async()


@celery_app.task(name="xbot.tasks.growth_tasks.run_growth_and_autofollowback")
def run_growth_and_autofollowback() -> dict[str, Any]:
    """Celery periodic task executing Auto Follow-Back and Proactive 500+ Verified Follower Growth."""
    logger.info("Starting Auto Follow-Back & Growth Celery task...")
    return asyncio.run(_run_growth_and_autofollowback_async())
