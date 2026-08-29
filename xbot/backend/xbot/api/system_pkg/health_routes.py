from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

from typing import Any

import redis
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, RateLimit

router = APIRouter(tags=["System"])


@router.get("/health", response_model=dict[str, Any])
async def get_system_health() -> dict[str, Any]:
    """Retrieves full system diagnostic status."""
    r = redis.from_url(settings.REDIS_URL)
    redis_ok = False
    system_paused = False
    try:
        r.ping()
        redis_ok = True
        system_paused = r.get("system:paused") == b"1"
    except Exception:
        pass

    return {
        "status": "healthy" if redis_ok else "unhealthy",
        "service": "xbot-api",
        "redis_connected": redis_ok,
        "system_paused": system_paused,
        "database_url": settings.DATABASE_URL.split("@")[-1],  # hide credentials
    }


@router.get("/rate-limits", response_model=list[dict[str, Any]])
async def get_all_rate_limits(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """Gets all current rate limit values from the database."""
    stmt = select(RateLimit)
    result = await db.execute(stmt)
    limits = result.scalars().all()

    # Query profiles slugs to add context
    stmt_profiles = select(Profile)
    res_profiles = await db.execute(stmt_profiles)
    profiles = {p.id: p.profile_slug for p in res_profiles.scalars().all()}

    return [
        {
            "id": lim.id,
            "profile_id": lim.profile_id,
            "profile_slug": profiles.get(lim.profile_id, "unknown"),
            "action_type": lim.action_type,
            "count_today": lim.count_today,
            "count_this_hour": lim.count_this_hour,
            "window_start": lim.window_start,
            "last_action_at": lim.last_action_at,
            "cooldown_until": lim.cooldown_until,
        }
        for lim in limits
    ]


@router.post("/system/pause", response_model=dict[str, Any])
async def pause_entire_system() -> dict[str, Any]:
    """Suspends scheduling operations system-wide."""
    r = redis.from_url(settings.REDIS_URL)
    r.set("system:paused", "1")
    return {"status": "success", "message": "System scheduler paused successfully."}


@router.post("/system/resume", response_model=dict[str, Any])
async def resume_entire_system() -> dict[str, Any]:
    """Resumes scheduling operations system-wide."""
    r = redis.from_url(settings.REDIS_URL)
    r.delete("system:paused")
    return {"status": "success", "message": "System scheduler resumed successfully."}


@router.get("/system/config", response_model=dict[str, Any])
async def get_system_config() -> dict[str, Any]:
    """Gets primary backend settings configuration details."""
    return {
        "DATABASE_URL": settings.DATABASE_URL.split("@")[-1],
        "REDIS_URL": settings.REDIS_URL,
        "LITELLM_BASE_URL": settings.LITELLM_BASE_URL,
        "LITELLM_API_KEY": settings.LITELLM_API_KEY,
        "LITELLM_PRIMARY_MODEL": settings.LITELLM_PRIMARY_MODEL,
        "LITELLM_FAST_MODEL": settings.LITELLM_FAST_MODEL,
        "MODEL_POST_CREATION": settings.MODEL_POST_CREATION,
        "MODEL_REPLY_ANALYSIS": settings.MODEL_REPLY_ANALYSIS,
        "MODEL_HOOK_OPTIMIZER": settings.MODEL_HOOK_OPTIMIZER,
        "MODEL_POLL_GENERATOR": settings.MODEL_POLL_GENERATOR,
        "MODEL_TREND_ANALYSIS": settings.MODEL_TREND_ANALYSIS,
        "MODEL_LIKE_RETWEET": settings.MODEL_LIKE_RETWEET,
        "MODEL_FOLLOW": settings.MODEL_FOLLOW,
        "MODEL_REFLECTION": settings.MODEL_REFLECTION,
        "MODEL_PLANNER": settings.MODEL_PLANNER,
        "PROMPT_POST_CREATION": settings.PROMPT_POST_CREATION,
        "PROMPT_REPLY_ANALYSIS": settings.PROMPT_REPLY_ANALYSIS,
        "PROMPT_TREND_ANALYSIS": settings.PROMPT_TREND_ANALYSIS,
        "PROMPT_LIKE_RETWEET": settings.PROMPT_LIKE_RETWEET,
        "PROMPT_FOLLOW": settings.PROMPT_FOLLOW,
        "CONTEXT_POST_CREATION": settings.CONTEXT_POST_CREATION,
        "CONTEXT_REPLY_ANALYSIS": settings.CONTEXT_REPLY_ANALYSIS,
        "CONTEXT_TREND_ANALYSIS": settings.CONTEXT_TREND_ANALYSIS,
        "CONTEXT_LIKE_RETWEET": settings.CONTEXT_LIKE_RETWEET,
        "CONTEXT_FOLLOW": settings.CONTEXT_FOLLOW,
        "MISTRAL_API_KEY": settings.MISTRAL_API_KEY,
        "GEMINI_API_KEY": settings.GEMINI_API_KEY,
        "DEEPSEEK_API_KEY": settings.DEEPSEEK_API_KEY,
        "OPENROUTER_API_KEY": settings.OPENROUTER_API_KEY,
        "API_PORT": settings.API_PORT,
    }


from pydantic import BaseModel

