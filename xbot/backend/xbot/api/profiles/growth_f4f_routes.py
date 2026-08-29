from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.analytics import FollowerChangeLog
from xbot.browser.manager import BrowserManager
from xbot.safety.guard import SafetyGuard
from xbot.growth.f4f_engine import record_follow_action, record_unfollow_action

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()


class F4FFollowRequest(BaseModel):
    target_handle: str = Field(..., min_length=1)
    is_blue_tick: bool = Field(default=True)
    niche: str | None = Field(default="ai")

@router.get("/{profile_id}/f4f/candidates", response_model=list[dict[str, Any]])
async def get_f4f_candidates(
    profile_id: uuid.UUID,
    niche: str = "all",
    blue_tick_only: bool = True,
    limit: int = 25,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists high-reciprocity Blue Tick candidates across anime, movies, tech, and AI communities."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.follow_growth import FollowCandidate
    from xbot.growth.f4f_engine import populate_f4f_candidates

    query = select(FollowCandidate).where(FollowCandidate.profile_id == profile_id)
    if niche != "all":
        query = query.where(FollowCandidate.niche == niche)
    if blue_tick_only:
        query = query.where(FollowCandidate.is_blue_tick == True)
    
    query = query.order_by(FollowCandidate.reciprocity_score.desc()).limit(limit)
    res = await db.execute(query)
    candidates = res.scalars().all()

    if not candidates:
        candidates = await populate_f4f_candidates(profile_id=profile_id, db=db, niche=niche, limit=limit)

    return [
        {
            "id": str(c.id),
            "handle": c.handle,
            "display_name": c.display_name,
            "niche": c.niche,
            "is_blue_tick": c.is_blue_tick,
            "follower_count": c.follower_count,
            "following_count": c.following_count,
            "bio": c.bio,
            "source_discussion": c.source_discussion,
            "reciprocity_score": c.reciprocity_score,
            "status": c.status,
            "discovered_at": c.discovered_at.isoformat() if c.discovered_at else None,
        }
        for c in candidates
    ]

@router.post("/{profile_id}/f4f/scan", response_model=dict[str, Any])
async def trigger_f4f_scan(
    profile_id: uuid.UUID,
    niche: str = "all",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Scans community discussions and refreshes the candidate radar."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.growth.f4f_engine import populate_f4f_candidates
    candidates = await populate_f4f_candidates(profile_id=profile_id, db=db, niche=niche, limit=limit)
    return {
        "status": "success",
        "message": f"Harvested {len(candidates)} high-reciprocity Blue Tick candidates.",
        "count": len(candidates),
    }

@router.post("/{profile_id}/f4f/follow", response_model=dict[str, Any])
async def execute_f4f_follow(
    profile_id: uuid.UUID,
    req: F4FFollowRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live follow of a candidate and starts the 4-day reciprocity grace period."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import FollowUser
    from xbot.growth.f4f_engine import record_follow_action

    clean_handle = req.target_handle.lstrip("@")
    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Browser is currently busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = FollowUser()
        success = await action.execute(page, username=clean_handle)
        
        if success:
            await record_follow_action(
                profile_id=profile_id,
                target_handle=clean_handle,
                db=db,
                is_blue_tick=req.is_blue_tick,
                niche=req.niche,
            )

        return {
            "status": "success" if success else "failed",
            "message": f"Successfully followed @{clean_handle} on X!" if success else f"Failed to follow @{clean_handle}.",
            "target_handle": clean_handle,
        }
    except Exception as e:
        logger.error(f"Error following candidate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass

@router.post("/{profile_id}/f4f/trigger-cycle", response_model=dict[str, Any])
async def trigger_growth_and_autofollowback_endpoint(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Triggers an immediate Auto Follow-Back & 500+ Verified Follower Growth Cycle."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.tasks import run_growth_and_autofollowback
    task = run_growth_and_autofollowback.delay()
    return {
        "status": "success",
        "message": "Auto Follow-Back & Growth Engine cycle triggered in background!",
        "task_id": task.id,
    }

@router.get("/{profile_id}/f4f/stats", response_model=dict[str, Any])
async def get_f4f_stats(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Returns analytics for the 1,000 Blue Tick Follower Milestone."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.growth.f4f_engine import get_f4f_milestone_analytics
    return await get_f4f_milestone_analytics(profile_id=profile_id, db=db)

@router.get("/{profile_id}/f4f/growth-posts", response_model=list[dict[str, Any]])
async def get_active_growth_posts(
    profile_id: uuid.UUID,
    niche: str = "all",
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Hunts active follow-for-follow and mutuals posts across Twitter/X."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.growth.community_harvester import discover_active_growth_posts
    posts = discover_active_growth_posts(niche=niche)
    return [p.model_dump() for p in posts]

@router.post("/{profile_id}/f4f/batch-follow", response_model=dict[str, Any])
async def execute_f4f_batch_follow(
    profile_id: uuid.UUID,
    count: int = 3,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes sequential live follows for the top N high-reciprocity Blue Tick candidates."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.models.follow_growth import FollowCandidate
    from xbot.growth.f4f_engine import record_follow_action
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import FollowUser
    from xbot.browser.timing import sleep_with_jitter

    c_stmt = (
        select(FollowCandidate)
        .where(FollowCandidate.profile_id == profile_id)
        .where(FollowCandidate.status == "discovered")
        .order_by(FollowCandidate.reciprocity_score.desc())
        .limit(min(10, max(1, count)))
    )
    c_res = await db.execute(c_stmt)
    candidates = c_res.scalars().all()

    if not candidates:
        return {"status": "no_op", "message": "No un-followed candidates in queue.", "followed_count": 0}

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Browser is currently busy. Please retry.")

    context = None
    followed: list[str] = []
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = FollowUser()
        for cand in candidates:
            clean = cand.handle.lstrip("@")
            success = await action.execute(page, username=clean)
            if success:
                followed.append(clean)
                await record_follow_action(
                    profile_id=profile_id,
                    target_handle=clean,
                    db=db,
                    is_blue_tick=cand.is_blue_tick,
                    niche=cand.niche,
                )
                await sleep_with_jitter(2000)

        return {
            "status": "success",
            "message": f"Successfully followed {len(followed)} Blue Tick candidates live on X!",
            "followed_handles": followed,
            "followed_count": len(followed),
        }
    except Exception as e:
        logger.error(f"Error in batch follow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass
        try:
            manager.release_lock(db_profile.profile_slug)
        except Exception:
            pass

