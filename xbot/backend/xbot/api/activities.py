from __future__ import annotations

import datetime
import logging
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.database import get_db
from xbot.models.profile import Profile
from xbot.models.session import Action, ActionStatus, ActionType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["Activities"])


class ActivityItem(BaseModel):
    id: str
    action_type: str
    status: str
    target_url: str | None = None
    target_author: str | None = None
    target_tweet_id: str | None = None
    content: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0
    executed_at: datetime.datetime | None = None
    time_ago: str = ""
    session_id: str | None = None


class ActivitySummaryCounts(BaseModel):
    total: int = 0
    completed: int = 0
    skipped: int = 0
    failed: int = 0
    replies: int = 0
    likes: int = 0
    posts: int = 0
    quotes: int = 0
    follows: int = 0
    unfollows: int = 0


class ActivityListResponse(BaseModel):
    items: list[ActivityItem]
    total: int
    limit: int
    offset: int
    time_range: str
    summary_counts: ActivitySummaryCounts


def _format_time_ago(dt: datetime.datetime | None, now: datetime.datetime) -> str:
    if not dt:
        return ""
    dt_naive = dt.replace(tzinfo=None) if dt.tzinfo else dt
    now_naive = now.replace(tzinfo=None) if now.tzinfo else now
    diff_sec = max(0, int((now_naive - dt_naive).total_seconds()))
    if diff_sec < 60:
        return f"{diff_sec}s ago"
    diff_min = diff_sec // 60
    if diff_min < 60:
        return f"{diff_min}m ago"
    diff_hours = diff_min // 60
    if diff_hours < 24:
        return f"{diff_hours}h ago"
    diff_days = diff_hours // 24
    return f"{diff_days}d ago"


def _extract_target_author_and_id(target_url: str | None) -> tuple[str | None, str | None]:
    if not target_url:
        return None, None
    
    author = None
    tweet_id = None
    
    # Status url: https://x.com/username/status/123456789
    status_match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)/status/(\d+)", target_url)
    if status_match:
        author = f"@{status_match.group(1)}"
        tweet_id = status_match.group(2)
    else:
        # Profile url: https://x.com/username
        user_match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)/?", target_url)
        if user_match:
            author = f"@{user_match.group(1)}"
        elif target_url.startswith("@"):
            author = target_url
        elif not target_url.startswith("http"):
            author = f"@{target_url}"
            
    return author, tweet_id


@router.get("/{profile_id}/activities", response_model=ActivityListResponse)
async def get_profile_activities(
    profile_id: uuid.UUID,
    time_range: str = Query("24h", pattern="^(3h|6h|12h|24h|3d|7d|all)$"),
    action_type: str = Query("all"),
    status_filter: str = Query("all", alias="status"),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ActivityListResponse:
    """
    Retrieves a paginated list of actions executed for a profile with rolling time filters,
    target author extraction, actual post previews, and action summary counts.
    """
    prof_res = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = prof_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile with ID {profile_id} not found.",
        )

    now_utc = datetime.datetime.utcnow()
    
    cutoff: datetime.datetime | None = None
    if time_range == "3h":
        cutoff = now_utc - datetime.timedelta(hours=3)
    elif time_range == "6h":
        cutoff = now_utc - datetime.timedelta(hours=6)
    elif time_range == "12h":
        cutoff = now_utc - datetime.timedelta(hours=12)
    elif time_range == "24h":
        cutoff = now_utc - datetime.timedelta(hours=24)
    elif time_range == "3d":
        cutoff = now_utc - datetime.timedelta(days=3)
    elif time_range == "7d":
        cutoff = now_utc - datetime.timedelta(days=7)

    base_conditions = [Action.profile_id == profile_id]
    if cutoff:
        base_conditions.append(Action.executed_at >= cutoff)

    # 1. Summary Counts across the time window
    stmt_all = select(Action.action_type, Action.status).where(*base_conditions)
    res_all = await db.execute(stmt_all)
    all_rows = res_all.all()

    summary_counts = ActivitySummaryCounts(
        total=len(all_rows),
        completed=sum(1 for _, s in all_rows if s == ActionStatus.COMPLETED),
        skipped=sum(1 for _, s in all_rows if s == ActionStatus.SKIPPED),
        failed=sum(1 for _, s in all_rows if s == ActionStatus.FAILED),
        replies=sum(1 for t, _ in all_rows if t == ActionType.REPLY),
        likes=sum(1 for t, _ in all_rows if t == ActionType.LIKE),
        posts=sum(1 for t, _ in all_rows if t in (ActionType.POST, ActionType.POLL)),
        quotes=sum(1 for t, _ in all_rows if t == ActionType.QUOTE),
        follows=sum(1 for t, _ in all_rows if t in (ActionType.FOLLOW, ActionType.FOLLOW_ENGAGERS)),
        unfollows=sum(1 for t, _ in all_rows if t in (ActionType.UNFOLLOW, ActionType.UNFOLLOW_NON_FOLLOWERS)),
    )

    # 2. Apply action_type filter
    query_conditions = list(base_conditions)
    if action_type != "all":
        if action_type == "post":
            query_conditions.append(Action.action_type.in_([ActionType.POST, ActionType.POLL]))
        elif action_type == "follow":
            query_conditions.append(Action.action_type.in_([ActionType.FOLLOW, ActionType.FOLLOW_ENGAGERS]))
        elif action_type == "unfollow":
            query_conditions.append(Action.action_type.in_([ActionType.UNFOLLOW, ActionType.UNFOLLOW_NON_FOLLOWERS]))
        else:
            try:
                act_enum = ActionType(action_type)
                query_conditions.append(Action.action_type == act_enum)
            except ValueError:
                pass

    # 3. Apply status filter
    if status_filter != "all":
        try:
            stat_enum = ActionStatus(status_filter)
            query_conditions.append(Action.status == stat_enum)
        except ValueError:
            pass

    # 4. Apply search query
    if search and search.strip():
        term = f"%{search.strip()}%"
        query_conditions.append(
            or_(
                Action.content.ilike(term),
                Action.target_url.ilike(term),
                Action.error.ilike(term),
            )
        )

    count_stmt = select(func.count(Action.id)).where(*query_conditions)
    count_res = await db.execute(count_stmt)
    total_matching = count_res.scalar() or 0

    items_stmt = (
        select(Action)
        .where(*query_conditions)
        .order_by(desc(Action.executed_at))
        .offset(offset)
        .limit(limit)
    )
    items_res = await db.execute(items_stmt)
    db_actions = items_res.scalars().all()

    items: list[ActivityItem] = []
    for act in db_actions:
        author, tweet_id = _extract_target_author_and_id(act.target_url)
        exec_dt = act.executed_at
        if exec_dt and not exec_dt.tzinfo:
            exec_dt = exec_dt.replace(tzinfo=datetime.timezone.utc)
        items.append(
            ActivityItem(
                id=str(act.id),
                action_type=act.action_type.value if hasattr(act.action_type, "value") else str(act.action_type),
                status=act.status.value if hasattr(act.status, "value") else str(act.status),
                target_url=act.target_url,
                target_author=author,
                target_tweet_id=tweet_id,
                content=act.content,
                result=act.result,
                error=act.error,
                duration_ms=act.duration_ms,
                executed_at=exec_dt,
                time_ago=_format_time_ago(act.executed_at, now_utc),
                session_id=str(act.session_id) if act.session_id else None,
            )
        )

    return ActivityListResponse(
        items=items,
        total=total_matching,
        limit=limit,
        offset=offset,
        time_range=time_range,
        summary_counts=summary_counts,
    )
