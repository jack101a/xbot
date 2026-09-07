from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any

from sqlalchemy import select

from xbot.celery_app import celery_app
from xbot.container import get_container
from xbot.database import AsyncSessionLocal
from xbot.models.pipeline import InstantTrendCampaign
from xbot.pipelines.instant_trend.pipeline import run_instant_trend_cycle

logger = logging.getLogger("xbot.tasks.instant_trend")


async def _process_active_instant_trend_campaigns_async() -> dict[str, Any]:
    """
    Scans for active instant trend campaigns that are due for execution or expired.
    Executes one cycle per due campaign.
    """
    now = datetime.utcnow()
    processed_count = 0
    expired_count = 0
    errors: list[str] = []

    try:
        async with AsyncSessionLocal() as db:
            stmt = select(InstantTrendCampaign).where(InstantTrendCampaign.status == "active")
            res = await db.execute(stmt)
            campaigns = res.scalars().all()

            if not campaigns:
                return {"status": "success", "processed": 0, "active_count": 0}

            container = get_container()

            for campaign in campaigns:
                try:
                    # 1. Check 48h limit
                    if now >= campaign.expires_at:
                        logger.info("InstantTrendTask: Campaign %s expired. Completing.", campaign.id)
                        campaign.status = "completed"
                        await db.commit()
                        expired_count += 1
                        continue

                    # 2. Check if due for next interval
                    if campaign.next_run_at and now < campaign.next_run_at:
                        continue

                    logger.info("InstantTrendTask: Executing cycle for campaign '%s' (topic: %s)", campaign.id, campaign.topic)
                    cycle_res = await run_instant_trend_cycle(
                        campaign_id=campaign.id,
                        db=db,
                        container=container,
                    )
                    processed_count += 1
                    logger.info("InstantTrendTask: Cycle finished for %s with status=%s, action=%s", campaign.topic, cycle_res.status, cycle_res.action_type)
                except Exception as c_err:
                    err_msg = f"Campaign {campaign.id} error: {c_err}"
                    logger.error("InstantTrendTask: %s", err_msg)
                    errors.append(err_msg)

    except Exception as e:
        logger.error("InstantTrendTask: Root execution error: %s", e)
        return {"status": "error", "error": str(e)}

    return {
        "status": "success",
        "processed": processed_count,
        "expired": expired_count,
        "errors": errors,
    }


@celery_app.task(name="xbot.tasks.process_active_instant_trend_campaigns")
def process_active_instant_trend_campaigns() -> dict[str, Any]:
    """Celery entry point to periodically check and run active instant trend campaigns."""
    return asyncio.run(_process_active_instant_trend_campaigns_async())
