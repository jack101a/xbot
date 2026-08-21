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
        "MODEL_TREND_ANALYSIS": settings.MODEL_TREND_ANALYSIS,
        "MODEL_LIKE_RETWEET": settings.MODEL_LIKE_RETWEET,
        "MODEL_FOLLOW": settings.MODEL_FOLLOW,
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

class SystemConfigUpdate(BaseModel):
    LITELLM_BASE_URL: str | None = None
    LITELLM_API_KEY: str | None = None
    LITELLM_PRIMARY_MODEL: str | None = None
    LITELLM_FAST_MODEL: str | None = None
    MODEL_POST_CREATION: str | None = None
    MODEL_REPLY_ANALYSIS: str | None = None
    MODEL_TREND_ANALYSIS: str | None = None
    MODEL_LIKE_RETWEET: str | None = None
    MODEL_FOLLOW: str | None = None
    PROMPT_POST_CREATION: str | None = None
    PROMPT_REPLY_ANALYSIS: str | None = None
    PROMPT_TREND_ANALYSIS: str | None = None
    PROMPT_LIKE_RETWEET: str | None = None
    PROMPT_FOLLOW: str | None = None
    CONTEXT_POST_CREATION: str | None = None
    CONTEXT_REPLY_ANALYSIS: str | None = None
    CONTEXT_TREND_ANALYSIS: str | None = None
    CONTEXT_LIKE_RETWEET: str | None = None
    CONTEXT_FOLLOW: str | None = None
    MISTRAL_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None

@router.put("/system/config", response_model=dict[str, Any])
async def update_system_config(payload: SystemConfigUpdate) -> dict[str, Any]:
    """Updates primary backend settings configuration details dynamically and persists them in .env."""
    from pathlib import Path
    
    # Update settings object in-memory
    if payload.LITELLM_BASE_URL is not None:
        settings.LITELLM_BASE_URL = payload.LITELLM_BASE_URL
    if payload.LITELLM_API_KEY is not None:
        settings.LITELLM_API_KEY = payload.LITELLM_API_KEY
    if payload.LITELLM_PRIMARY_MODEL is not None:
        settings.LITELLM_PRIMARY_MODEL = payload.LITELLM_PRIMARY_MODEL
    if payload.LITELLM_FAST_MODEL is not None:
        settings.LITELLM_FAST_MODEL = payload.LITELLM_FAST_MODEL
    if payload.MODEL_POST_CREATION is not None:
        settings.MODEL_POST_CREATION = payload.MODEL_POST_CREATION
    if payload.MODEL_REPLY_ANALYSIS is not None:
        settings.MODEL_REPLY_ANALYSIS = payload.MODEL_REPLY_ANALYSIS
    if payload.MODEL_TREND_ANALYSIS is not None:
        settings.MODEL_TREND_ANALYSIS = payload.MODEL_TREND_ANALYSIS
    if payload.MODEL_LIKE_RETWEET is not None:
        settings.MODEL_LIKE_RETWEET = payload.MODEL_LIKE_RETWEET
    if payload.MODEL_FOLLOW is not None:
        settings.MODEL_FOLLOW = payload.MODEL_FOLLOW
    if payload.PROMPT_POST_CREATION is not None:
        settings.PROMPT_POST_CREATION = payload.PROMPT_POST_CREATION
    if payload.PROMPT_REPLY_ANALYSIS is not None:
        settings.PROMPT_REPLY_ANALYSIS = payload.PROMPT_REPLY_ANALYSIS
    if payload.PROMPT_TREND_ANALYSIS is not None:
        settings.PROMPT_TREND_ANALYSIS = payload.PROMPT_TREND_ANALYSIS
    if payload.PROMPT_LIKE_RETWEET is not None:
        settings.PROMPT_LIKE_RETWEET = payload.PROMPT_LIKE_RETWEET
    if payload.PROMPT_FOLLOW is not None:
        settings.PROMPT_FOLLOW = payload.PROMPT_FOLLOW
    if payload.CONTEXT_POST_CREATION is not None:
        settings.CONTEXT_POST_CREATION = payload.CONTEXT_POST_CREATION
    if payload.CONTEXT_REPLY_ANALYSIS is not None:
        settings.CONTEXT_REPLY_ANALYSIS = payload.CONTEXT_REPLY_ANALYSIS
    if payload.CONTEXT_TREND_ANALYSIS is not None:
        settings.CONTEXT_TREND_ANALYSIS = payload.CONTEXT_TREND_ANALYSIS
    if payload.CONTEXT_LIKE_RETWEET is not None:
        settings.CONTEXT_LIKE_RETWEET = payload.CONTEXT_LIKE_RETWEET
    if payload.CONTEXT_FOLLOW is not None:
        settings.CONTEXT_FOLLOW = payload.CONTEXT_FOLLOW
    if payload.MISTRAL_API_KEY is not None:
        settings.MISTRAL_API_KEY = payload.MISTRAL_API_KEY
    if payload.GEMINI_API_KEY is not None:
        settings.GEMINI_API_KEY = payload.GEMINI_API_KEY
    if payload.DEEPSEEK_API_KEY is not None:
        settings.DEEPSEEK_API_KEY = payload.DEEPSEEK_API_KEY
    if payload.OPENROUTER_API_KEY is not None:
        settings.OPENROUTER_API_KEY = payload.OPENROUTER_API_KEY

    # Persist back to .env
    env_path = Path("/home/ubuntu/projects/xbot/backend/.env")
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updated = {
        "LITELLM_BASE_URL": settings.LITELLM_BASE_URL,
        "LITELLM_API_KEY": settings.LITELLM_API_KEY,
        "LITELLM_PRIMARY_MODEL": settings.LITELLM_PRIMARY_MODEL,
        "LITELLM_FAST_MODEL": settings.LITELLM_FAST_MODEL,
        "MODEL_POST_CREATION": settings.MODEL_POST_CREATION,
        "MODEL_REPLY_ANALYSIS": settings.MODEL_REPLY_ANALYSIS,
        "MODEL_TREND_ANALYSIS": settings.MODEL_TREND_ANALYSIS,
        "MODEL_LIKE_RETWEET": settings.MODEL_LIKE_RETWEET,
        "MODEL_FOLLOW": settings.MODEL_FOLLOW,
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
        "OPENROUTER_API_KEY": settings.OPENROUTER_API_KEY
    }

    new_lines = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            parts = stripped.split("=", 1)
            k = parts[0].strip()
            if k in updated:
                new_lines.append(f"{k}={updated[k]}")
                seen.add(k)
                continue
        new_lines.append(line)

    for k, v in updated.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return {
        "status": "success",
        "message": "System configuration updated and saved successfully.",
        "config": {
            "DATABASE_URL": settings.DATABASE_URL.split("@")[-1],
            "REDIS_URL": settings.REDIS_URL,
            "LITELLM_BASE_URL": settings.LITELLM_BASE_URL,
            "LITELLM_API_KEY": settings.LITELLM_API_KEY,
            "LITELLM_PRIMARY_MODEL": settings.LITELLM_PRIMARY_MODEL,
            "LITELLM_FAST_MODEL": settings.LITELLM_FAST_MODEL,
            "MODEL_POST_CREATION": settings.MODEL_POST_CREATION,
            "MODEL_REPLY_ANALYSIS": settings.MODEL_REPLY_ANALYSIS,
            "MODEL_TREND_ANALYSIS": settings.MODEL_TREND_ANALYSIS,
            "MODEL_LIKE_RETWEET": settings.MODEL_LIKE_RETWEET,
            "MODEL_FOLLOW": settings.MODEL_FOLLOW,
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
    }

import httpx

@router.get("/system/models")
async def get_system_models(provider: str) -> dict[str, Any]:
    """Fetches the actual model list from the specified provider's API."""
    url = ""
    api_key = ""
    if provider == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/openai/models"
        api_key = settings.GEMINI_API_KEY
    elif provider == "mistral":
        url = "https://api.mistral.ai/v1/models"
        api_key = settings.MISTRAL_API_KEY
    elif provider == "openrouter":
        url = "https://openrouter.ai/api/v1/models"
        api_key = settings.OPENROUTER_API_KEY
    elif provider == "deepseek":
        url = "https://api.deepseek.com/models"
        api_key = settings.DEEPSEEK_API_KEY
    elif provider == "litellm":
        if not settings.LITELLM_BASE_URL:
            return {"models": []}
        url = f"{settings.LITELLM_BASE_URL.rstrip('/')}/models"
        api_key = settings.LITELLM_API_KEY
    else:
        return {"models": []}
        
    if not api_key:
        return {"models": []}
        
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            if resp.status_code != 200:
                logger.error(f"Failed to fetch models for {provider}: {resp.status_code} {resp.text}")
                return {"models": []}
            data = resp.json()
            models = [m.get("id") for m in data.get("data", []) if "id" in m]
            return {"models": models}
    except Exception as e:
        logger.error(f"Exception fetching models for {provider}: {e}")
        return {"models": []}
