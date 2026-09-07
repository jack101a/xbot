from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.container import get_container
from xbot.database import get_db
from xbot.models.pipeline import InstantTrendCampaign
from xbot.models.profile import Profile
from xbot.pipelines.instant_trend.pipeline import run_instant_trend_cycle
from xbot.pipelines.instant_trend.types import CampaignCreateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trends/instant", tags=["instant-trend"])


@router.post("/start")
async def start_instant_trend_campaign(
    payload: CampaignCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Starts an autonomous instant trend growth campaign that executes recurring cycles on X."""
    stmt = select(Profile).where(Profile.profile_slug == payload.profile_slug)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile '{payload.profile_slug}' not found")

    now = datetime.utcnow()
    duration = min(payload.duration_hours, 192)  # Maximum 192 hours boundary (8 days)
    expires_at = now + timedelta(hours=duration)

    campaign = InstantTrendCampaign(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic=payload.topic.strip(),
        status="active",
        duration_hours=duration,
        interval_minutes=payload.interval_minutes,
        quote_percentage=payload.quote_percentage,
        sentiment_tone=payload.sentiment_tone,
        ragebait_percentage=payload.ragebait_percentage,
        seen_tweet_ids=[],
        posted_actions=[],
        started_at=now,
        expires_at=expires_at,
        last_run_at=None,
        next_run_at=now,  # Due immediately
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    # Trigger first iteration asynchronously in background
    asyncio.create_task(
        _run_initial_cycle_async(campaign.id)
    )

    return {
        "status": "success",
        "message": f"Instant trend campaign started for '{campaign.topic}'",
        "campaign_id": str(campaign.id),
        "topic": campaign.topic,
        "duration_hours": campaign.duration_hours,
        "expires_at": campaign.expires_at.isoformat(),
        "interval_minutes": campaign.interval_minutes,
    }


async def _run_initial_cycle_async(campaign_id: uuid.UUID) -> None:
    """Helper to kick off the very first cycle without blocking API return."""
    await asyncio.sleep(1)
    from xbot.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            container = get_container()
            await run_instant_trend_cycle(campaign_id, session, container)
    except Exception as e:
        logger.error("Error in initial cycle for campaign %s: %s", campaign_id, e)


@router.post("/{campaign_id}/stop")
async def stop_instant_trend_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually stops an ongoing instant trend campaign."""
    try:
        c_uuid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign UUID format")

    campaign = await db.get(InstantTrendCampaign, c_uuid)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "stopped"
    await db.commit()
    return {
        "status": "success",
        "message": f"Campaign '{campaign.topic}' stopped by user",
        "campaign_id": str(campaign.id),
    }


@router.get("/active")
async def list_active_campaigns(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists all currently active instant trend campaigns."""
    now = datetime.utcnow()
    stmt = select(InstantTrendCampaign).where(InstantTrendCampaign.status == "active").order_by(InstantTrendCampaign.started_at.desc())
    res = await db.execute(stmt)
    campaigns = res.scalars().all()

    output = []
    for c in campaigns:
        time_left_sec = max(0, int((c.expires_at - now).total_seconds()))
        output.append({
            "id": str(c.id),
            "topic": c.topic,
            "status": c.status,
            "duration_hours": c.duration_hours,
            "interval_minutes": c.interval_minutes,
            "started_at": c.started_at.isoformat(),
            "expires_at": c.expires_at.isoformat(),
            "seconds_remaining": time_left_sec,
            "hours_remaining": round(time_left_sec / 3600, 1),
            "actions_executed_count": len(c.posted_actions or []),
            "unique_seen_tweets_count": len(c.seen_tweet_ids or []),
            "next_run_at": c.next_run_at.isoformat() if c.next_run_at else None,
        })
    return output


@router.get("/{campaign_id}/status")
async def get_campaign_status(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves full telemetry, history, and actions for a campaign."""
    try:
        c_uuid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign UUID format")

    campaign = await db.get(InstantTrendCampaign, c_uuid)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    now = datetime.utcnow()
    time_left_sec = max(0, int((campaign.expires_at - now).total_seconds()))

    return {
        "id": str(campaign.id),
        "topic": campaign.topic,
        "status": campaign.status,
        "duration_hours": campaign.duration_hours,
        "interval_minutes": campaign.interval_minutes,
        "quote_percentage": campaign.quote_percentage,
        "started_at": campaign.started_at.isoformat(),
        "expires_at": campaign.expires_at.isoformat(),
        "seconds_remaining": time_left_sec,
        "hours_remaining": round(time_left_sec / 3600, 1),
        "actions_executed": campaign.posted_actions or [],
        "seen_tweet_ids": campaign.seen_tweet_ids or [],
        "last_run_at": campaign.last_run_at.isoformat() if campaign.last_run_at else None,
        "next_run_at": campaign.next_run_at.isoformat() if campaign.next_run_at else None,
    }
