from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import get_db
from xbot.models.profile import Profile
from xbot.models.session import Action, ActionType
from xbot.pipelines.browser_queue.queue import get_redis_client
from xbot.pipelines.post_pruner_pipeline import (
    PrunerFilterCriteria,
    run_post_pruner_for_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{profile_id}/pruner/run")
async def run_profile_post_pruner(
    profile_id: uuid.UUID,
    criteria: PrunerFilterCriteria,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    On-demand endpoint to run the Post Pruner for a profile.
    Scans the profile's main timeline, filters for underperforming original posts,
    and enqueues deletion jobs.
    """
    stmt = select(Profile).where(Profile.id == profile_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    try:
        r = get_redis_client()
        report = await run_post_pruner_for_profile(
            profile_id=profile_id,
            criteria=criteria,
            db=db,
            r=r,
        )
        return report
    except Exception as e:
        logger.error("Error executing post pruner for %s: %s", profile_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pruner execution failed: {str(e)}")


@router.get("/{profile_id}/pruner/history")
async def get_profile_pruner_history(
    profile_id: uuid.UUID,
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Retrieves the historical log of deleted posts for this profile.
    """
    stmt = (
        select(Action)
        .where(Action.profile_id == profile_id, Action.action_type == ActionType.DELETE)
        .order_by(desc(Action.executed_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    actions = res.scalars().all()

    history = []
    for act in actions:
        history.append({
            "id": str(act.id),
            "target_url": act.target_url,
            "content": act.content,
            "status": act.status,
            "executed_at": act.executed_at.isoformat() if act.executed_at else None,
            "result": act.result or {},
        })

    return {
        "profile_id": str(profile_id),
        "total_count": len(history),
        "history": history,
    }
