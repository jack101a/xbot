"""
Campaign Studio API Endpoints for XBot Pro.
Enables creators to submit natural language prompt instructions, track real-time research,
and publish/schedule multi-asset campaigns.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import get_db, AsyncSessionLocal
from xbot.pipelines.on_demand_campaign_pipeline import (
    execute_on_demand_campaign,
    get_campaign_status,
    publish_campaign_deliverables,
    update_campaign_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


class GenerateCampaignRequest(BaseModel):
    profile_id: str = Field(..., description="Target profile UUID")
    prompt: str = Field(..., min_length=3, description="Natural-language creative instructions or selected trending topic")
    duration_hours: int = Field(0, ge=0, le=168, description="0 for sprint pack, 12-168 for continuous multi-day campaign")
    interval_minutes: int = Field(60, ge=5, le=1440, description="Spacing in minutes between drops/actions")
    source_type: Literal["on_demand", "trend_radar"] = Field("on_demand", description="Source of campaign idea")
    media_preference: Literal["x_official", "ai_generated"] = Field("x_official", description="Priority for attached media")


class PublishCampaignRequest(BaseModel):
    content_ids: list[str] = Field(..., min_length=1, description="List of generated Content UUIDs to publish")
    mode: Literal["instant", "schedule"] = Field("schedule", description="'instant' (now) or 'schedule' (spaced)")
    interval_minutes: int = Field(60, ge=5, le=1440, description="Spacing in minutes between scheduled items")


async def _run_campaign_in_background(
    profile_id: str,
    prompt: str,
    campaign_id: str,
    duration_hours: int = 0,
    interval_minutes: int = 60,
    source_type: str = "on_demand",
    media_preference: str = "x_official",
):
    """Background execution runner for on-demand & continuous campaigns."""
    async with AsyncSessionLocal() as db:
        try:
            await execute_on_demand_campaign(
                profile_id=profile_id,
                prompt=prompt,
                campaign_id=campaign_id,
                db=db,
                duration_hours=duration_hours,
                interval_minutes=interval_minutes,
                source_type=source_type,
                media_preference=media_preference,
            )
        except Exception as e:
            logger.error("Background campaign execution failed for %s: %s", campaign_id, e)
            update_campaign_status(
                campaign_id,
                status="failed",
                current_step="Campaign generation failed.",
                error=str(e),
            )


@router.get("/trends/live")
async def get_live_trends_for_campaigns(
    profile_id: str | None = None,
    limit: int = 6,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Scans live RSS/trend feeds, scores alignment to the profile's persona,
    and returns trending topics directly to the AI Campaign Studio for 1-click campaign generation.
    """
    try:
        from xbot.api.tools import _resolve_persona, DEFAULT_RSS_FEEDS
        from xbot.ai.trend_radar import fetch_rss_trends, TrendItem
        from xbot.ai.trend_generator import generate_trend_take

        persona, slug = await _resolve_persona(db, profile_id, None)
        raw_trends = await fetch_rss_trends(feed_urls=DEFAULT_RSS_FEEDS, max_items_per_feed=3)
        trends_to_process = raw_trends[:limit]

        async def _eval_single(t: TrendItem):
            try:
                eval_res = await generate_trend_take(persona, t)
                return t, eval_res
            except Exception as e:
                logger.warning("Error evaluating trend take for %s: %s", t.title, e)
                return t, None

        eval_results = await asyncio.gather(*[_eval_single(t) for t in trends_to_process], return_exceptions=True)

        trends_out = []
        for res in eval_results:
            if isinstance(res, tuple) and len(res) == 2:
                t, eval_res = res
                score = round(eval_res.relevance_score * 100) if eval_res else 70
                angle = (eval_res.hot_take if eval_res and eval_res.hot_take else "Industry impact & critique")
                trends_out.append({
                    "title": t.title,
                    "summary": t.summary,
                    "url": t.source_url,
                    "alignment_score": score,
                    "category": t.source_name,
                    "recommended_angle": angle,
                })

        return {
            "status": "success",
            "trends": sorted(trends_out, key=lambda x: x["alignment_score"], reverse=True),
            "profile_slug": slug,
        }
    except Exception as e:
        logger.error("Error fetching live trends for Campaign Studio: %s", e)
        return {
            "status": "error",
            "error": str(e),
            "trends": [],
        }


@router.get("/active")
async def list_active_campaigns(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists all active and ongoing multi-day campaigns."""
    from datetime import datetime
    from sqlalchemy import select
    from xbot.models.pipeline import Campaign

    now = datetime.utcnow()
    stmt = select(Campaign).where(Campaign.status.in_(["active", "ready"])).order_by(Campaign.started_at.desc())
    res = await db.execute(stmt)
    campaigns = res.scalars().all()

    output = []
    for c in campaigns:
        time_left_sec = max(0, int((c.expires_at - now).total_seconds())) if c.expires_at else 0
        output.append({
            "id": str(c.id),
            "topic": c.topic,
            "status": c.status,
            "campaign_type": getattr(c, "campaign_type", "on_demand"),
            "source_type": getattr(c, "source_type", "custom"),
            "media_preference": getattr(c, "media_preference", "x_official"),
            "duration_hours": c.duration_hours,
            "interval_minutes": c.interval_minutes,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            "seconds_remaining": time_left_sec,
            "hours_remaining": round(time_left_sec / 3600, 1),
            "actions_executed_count": len(c.posted_actions or []),
            "deliverables_count": len(c.deliverables or []),
            "next_run_at": c.next_run_at.isoformat() if c.next_run_at else None,
        })
    return output


@router.post("/{campaign_id}/stop")
async def stop_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually stops an ongoing continuous campaign."""
    from xbot.models.pipeline import Campaign

    c_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, campaign_id) if not isinstance(campaign_id, uuid.UUID) else campaign_id
    campaign = await db.get(Campaign, c_uuid)
    if not campaign:
        try:
            campaign = await db.get(Campaign, uuid.UUID(campaign_id))
        except Exception:
            pass

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")

    campaign.status = "stopped"
    await db.commit()
    return {
        "status": "success",
        "message": f"Campaign '{campaign.topic}' stopped.",
        "campaign_id": str(campaign.id),
    }


@router.post("/generate")
async def generate_campaign(
    req: GenerateCampaignRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submits a natural-language campaign instruction or selected trend and triggers asynchronous
    campaign planning, X search research, media scraping, and synthesis.
    """
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
    update_campaign_status(
        campaign_id,
        status="initializing",
        current_step="Analyzing brief and initializing Campaign Studio...",
        progress_percent=5,
    )

    background_tasks.add_task(
        _run_campaign_in_background,
        req.profile_id,
        req.prompt,
        campaign_id,
        req.duration_hours,
        req.interval_minutes,
        req.source_type,
        req.media_preference,
    )

    return {
        "campaign_id": campaign_id,
        "status": "initializing",
        "message": "Campaign planning and research initiated in background.",
        "duration_hours": req.duration_hours,
        "media_preference": req.media_preference,
    }


@router.get("/{campaign_id}/status")
async def get_campaign_generation_status(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Polls the live research and synthesis status of a campaign.
    Falls back to SQLite database if in-memory cache was cleared by a server restart.
    """
    status_info = get_campaign_status(campaign_id)
    if status_info.get("status") != "not_found":
        return status_info

    # Fallback to database
    from xbot.models.pipeline import Campaign

    c_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, campaign_id) if not isinstance(campaign_id, uuid.UUID) else campaign_id
    camp = await db.get(Campaign, c_uuid)
    if not camp:
        try:
            camp = await db.get(Campaign, uuid.UUID(campaign_id))
        except Exception:
            pass

    if camp:
        return {
            "campaign_id": campaign_id,
            "status": camp.status,
            "current_step": "Campaign loaded from persistent database.",
            "progress_percent": 100 if camp.status in ("ready", "completed", "active") else 50,
            "plan": camp.plan_metadata,
            "deliverables": camp.deliverables or [],
            "duration_hours": camp.duration_hours,
            "campaign_type": getattr(camp, "campaign_type", "on_demand"),
            "source_type": getattr(camp, "source_type", "custom"),
            "media_preference": getattr(camp, "media_preference", "x_official"),
            "error": None,
            "created_at": camp.started_at.isoformat() if camp.started_at else None,
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Campaign {campaign_id} not found.",
    )


@router.post("/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: str,
    req: PublishCampaignRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Publishes or schedules deliverables from a generated campaign.
    """
    try:
        res = await publish_campaign_deliverables(
            campaign_id=campaign_id,
            content_ids=req.content_ids,
            mode=req.mode,
            interval_minutes=req.interval_minutes,
            db=db,
        )
        return res
    except Exception as e:
        logger.error("Failed to publish deliverables for campaign %s: %s", campaign_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish campaign deliverables: {e}",
        )
