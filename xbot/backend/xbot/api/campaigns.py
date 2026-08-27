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
    prompt: str = Field(..., min_length=5, description="Natural-language creative instructions")


class PublishCampaignRequest(BaseModel):
    content_ids: list[str] = Field(..., min_length=1, description="List of generated Content UUIDs to publish")
    mode: Literal["instant", "schedule"] = Field("schedule", description="'instant' (now) or 'schedule' (spaced)")
    interval_minutes: int = Field(60, ge=5, le=1440, description="Spacing in minutes between scheduled items")


async def _run_campaign_in_background(profile_id: str, prompt: str, campaign_id: str):
    """Background execution runner for on-demand campaigns."""
    async with AsyncSessionLocal() as db:
        try:
            await execute_on_demand_campaign(
                profile_id=profile_id,
                prompt=prompt,
                campaign_id=campaign_id,
                db=db,
            )
        except Exception as e:
            logger.error("Background campaign execution failed for %s: %s", campaign_id, e)
            update_campaign_status(
                campaign_id,
                status="failed",
                current_step="Campaign generation failed.",
                error=str(e),
            )


@router.post("/generate")
async def generate_campaign(
    req: GenerateCampaignRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submits a natural-language campaign instruction and triggers asynchronous
    campaign planning, X search research, media scraping, and synthesis.
    """
    campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
    update_campaign_status(
        campaign_id,
        status="initializing",
        current_step="Analyzing prompt and initializing Campaign Studio...",
        progress_percent=5,
    )

    background_tasks.add_task(_run_campaign_in_background, req.profile_id, req.prompt, campaign_id)

    return {
        "campaign_id": campaign_id,
        "status": "initializing",
        "message": "Campaign planning and research initiated in background.",
    }


@router.get("/{campaign_id}/status")
async def get_campaign_generation_status(
    campaign_id: str,
) -> dict[str, Any]:
    """
    Polls the live research and synthesis status of an on-demand campaign.
    """
    status_info = get_campaign_status(campaign_id)
    if status_info.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign {campaign_id} not found.",
        )
    return status_info


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
            detail=str(e),
        )
