from .constants import *
import asyncio
import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from ruamel.yaml import YAML
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.auth import (
    format_storage_state,
    inspect_profile_auth_status,
    parse_cookie_string,
)
from xbot.browser.manager import BrowserManager
from xbot.database import get_db
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import (
    DiaryManager,
    MemoryManager,
    load_config,
    save_config,
    Config,
    LimitsConfig,
    ScheduleConfig,
    load_persona,
    load_relationships,
    load_strategy,
    save_strategy,
    load_learned_state,
    save_learned_state,
    LearnedState,
)
from pydantic import BaseModel, Field
from xbot.persona.card_parser import load_raw_card, map_card_to_persona
from xbot.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

from fastapi import APIRouter
router = APIRouter()

@router.get("/{profile_id}/config", response_model=dict[str, Any])
async def get_profile_config(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves current automation limits and execution schedule configuration."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    config = load_config(profile_dir)
    return config.model_dump()

@router.put("/{profile_id}/config", response_model=dict[str, Any])
async def update_profile_config(
    profile_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates automation limits and execution schedule configuration on disk and clears Redis cache."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    config = load_config(profile_dir)

    if "mock_mode" in payload:
        config.mock_mode = bool(payload["mock_mode"])

    if "limits" in payload and isinstance(payload["limits"], dict):
        for k, v in payload["limits"].items():
            if hasattr(config.limits, k):
                try:
                    setattr(config.limits, k, int(v))
                except (ValueError, TypeError):
                    pass

    if "schedule" in payload and isinstance(payload["schedule"], dict):
        for k, v in payload["schedule"].items():
            if hasattr(config.schedule, k):
                if k in ("min_sessions_per_day", "max_sessions_per_day", "interval_minutes"):
                    try:
                        setattr(config.schedule, k, int(v))
                    except (ValueError, TypeError):
                        pass
                else:
                    setattr(config.schedule, k, str(v))

    save_config(profile_dir, config)

    try:
        import redis, datetime
        from xbot.config import settings
        r = redis.from_url(settings.REDIS_URL)
        today_str = datetime.date.today().isoformat()
        redis_key = f"schedule:{db_profile.profile_slug}:{today_str}"
        r.delete(redis_key)
    except Exception as e:
        logger.warning("Could not clear Redis schedule cache for %s: %s", db_profile.profile_slug, e)

    return {"status": "success", "message": "Automation limits and schedule updated successfully.", "config": config.model_dump()}

