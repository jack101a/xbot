from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import get_db
from xbot.models.profile import Profile
import datetime
from pydantic import BaseModel, Field

from xbot.container import get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.models.content import Content, ContentStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.pipelines.browser_queue.queue import get_redis_client
from xbot.pipelines.post_pruner_pipeline import (
    PrunerFilterCriteria,
    run_post_pruner_for_profile,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class DeleteSpecificPostsRequest(BaseModel):
    tweet_ids: list[str] = Field(default_factory=list, description="List of tweet IDs to delete")


@router.post("/{profile_id}/pruner/run")
async def run_profile_post_pruner(
    profile_id: uuid.UUID,
    criteria: PrunerFilterCriteria,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    On-demand endpoint to run the Post Pruner for a profile.
    Scans the profile's main timeline, filters for underperforming original posts,
    and enqueues deletion jobs. Supports dry_run preview if criteria.dry_run is True.
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


@router.post("/{profile_id}/pruner/preview")
async def preview_profile_post_pruner(
    profile_id: uuid.UUID,
    criteria: PrunerFilterCriteria,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Dry-run preview endpoint to scan the profile and return candidate posts and diagnostics
    without deleting anything.
    """
    criteria.dry_run = True
    return await run_profile_post_pruner(profile_id=profile_id, criteria=criteria, db=db)


@router.post("/{profile_id}/pruner/delete-specific")
async def delete_specific_profile_posts(
    profile_id: uuid.UUID,
    payload: DeleteSpecificPostsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Directly deletes a specific list of tweet IDs from the user's profile.
    """
    stmt = select(Profile).where(Profile.id == profile_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    username = (profile.x_handle or profile.profile_slug or "").lstrip("@")
    profile_slug = profile.profile_slug
    container = get_container()

    session = Session(
        profile_id=profile_id,
        started_at=datetime.datetime.utcnow(),
        ended_at=datetime.datetime.utcnow(),
        status=SessionStatus.COMPLETED,
        actions_planned=len(payload.tweet_ids),
        actions_completed=0,
        actions_failed=0,
    )
    db.add(session)
    await db.flush()

    deleted_results = []
    for tw_id in payload.tweet_ids:
        tw_id_clean = tw_id.strip()
        if not tw_id_clean:
            continue
        tw_url = f"https://x.com/{username}/status/{tw_id_clean}"
        del_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.DELETE_TWEET,
            params={"tweet_url": tw_url, "tweet_id": tw_id_clean, "username": username},
            timeout_seconds=45,
        )
        del_res = await container.browser.execute(del_req)
        is_success = (
            del_res.status in ("success", "deleted")
            or (del_res.action_result and del_res.action_result.status == "success")
        )

        if is_success:
            deleted_results.append({"tweet_id": tw_id_clean, "tweet_url": tw_url, "status": "deleted"})
            session.actions_completed += 1
            act = Action(
                session_id=session.id,
                profile_id=profile_id,
                action_type=ActionType.DELETE,
                target_url=tw_url,
                content=f"Deleted post {tw_id_clean} via targeted selection",
                status=ActionStatus.SUCCESS,
                result={"tweet_id": tw_id_clean, "reason": "targeted_selection"},
                executed_at=datetime.datetime.utcnow(),
            )
            db.add(act)

            c_stmt = select(Content).where(Content.tweet_id == tw_id_clean)
            c_res = await db.execute(c_stmt)
            c_record = c_res.scalar_one_or_none()
            if c_record and isinstance(c_record, Content):
                c_record.status = ContentStatus.DELETED
                meta = c_record.ai_metadata or {}
                meta["pruned_at"] = datetime.datetime.utcnow().isoformat()
                meta["prune_reason"] = "targeted_selection"
                c_record.ai_metadata = meta
        else:
            deleted_results.append({
                "tweet_id": tw_id_clean,
                "tweet_url": tw_url,
                "status": "failed",
                "error": del_res.error,
            })

    await db.commit()
    return {
        "status": "success",
        "profile_id": str(profile_id),
        "deleted_count": sum(1 for r in deleted_results if r.get("status") == "deleted"),
        "results": deleted_results,
    }


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
