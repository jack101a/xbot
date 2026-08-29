from __future__ import annotations
import xbot.api.profiles as profiles_api

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import yaml

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona.loader import load_persona, save_persona, load_character_card, save_character_card, load_strategy, save_strategy, load_relationships, save_relationships, load_learned_state, save_learned_state, load_config, save_config
from xbot.persona.diary import DiaryManager
from xbot.persona.memory import MemoryManager
from .constants import BASE_PROFILE_DIR

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()

@router.get("/{profile_id}/diary", response_model=list[dict[str, Any]])
async def get_profile_diary_logs(
    profile_id: uuid.UUID,
    limit: int = 15,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves recent daily inner-monologue diary entry summaries."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    diary_mgr = DiaryManager(profile_dir)
    return diary_mgr.get_recent_entries(limit=limit)


@router.get("/{profile_id}/memories", response_model=list[dict[str, Any]])
async def get_profile_memories(
    profile_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Gets extracted long-term memories for a profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    memory_mgr = MemoryManager(profile_dir)
    return memory_mgr.retrieve_memories(recency_limit=limit, min_importance=0.0)


@router.get("/{profile_id}/relationships", response_model=dict[str, Any])
async def get_profile_relationships(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves priority accounts and sentiment relationship tracking logs."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    relationships = load_relationships(profile_dir)
    return relationships.model_dump()


@router.get("/{profile_id}/strategy", response_model=dict[str, Any])
async def get_profile_strategy(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves current weekly strategy details."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    strategy = load_strategy(profile_dir)
    return strategy.model_dump()


@router.put("/{profile_id}/strategy", response_model=dict[str, Any])
async def update_profile_strategy(
    profile_id: uuid.UUID,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates strategy configuration (keywords, competitor accounts, topics) on disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    strategy = load_strategy(profile_dir)

    if "content_strategy" in payload and isinstance(payload["content_strategy"], dict):
        cs = payload["content_strategy"]
        if "top_performing_topics" in cs and isinstance(cs["top_performing_topics"], list):
            strategy.content_strategy.top_performing_topics = cs["top_performing_topics"]
        if "underperforming_topics" in cs and isinstance(cs["underperforming_topics"], list):
            strategy.content_strategy.underperforming_topics = cs["underperforming_topics"]
        if "posting_frequency" in cs:
            strategy.content_strategy.posting_frequency = str(cs["posting_frequency"])

    if "engagement_strategy" in payload and isinstance(payload["engagement_strategy"], dict):
        es = payload["engagement_strategy"]
        if "priority_accounts" in es and isinstance(es["priority_accounts"], list):
            strategy.engagement_strategy.priority_accounts = es["priority_accounts"]
        if "daily_targets" in es and isinstance(es["daily_targets"], dict):
            for k, v in es["daily_targets"].items():
                strategy.engagement_strategy.daily_targets[k] = str(v)

    if "current_focus" in payload and isinstance(payload["current_focus"], dict):
        cf = payload["current_focus"]
        if "primary" in cf:
            strategy.current_focus.primary = str(cf["primary"])
        if "secondary" in cf:
            strategy.current_focus.secondary = str(cf["secondary"])


@router.get("/{profile_id}/learned-state", response_model=dict[str, Any])
async def get_profile_learned_state(profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Retrieves dynamic learned state configuration."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    learned = load_learned_state(profile_dir)
    return learned.model_dump()


@router.put("/{profile_id}/learned-state", response_model=dict[str, Any])
async def update_profile_learned_state(
    profile_id: uuid.UUID,
    state_in: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Updates learned_state.yaml on disk."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    learned = LearnedState.model_validate(state_in)
    save_learned_state(profile_dir, learned)
    return {"status": "success", "message": "Learned state updated successfully."}


@router.post("/{profile_id}/reflect", response_model=dict[str, Any])
async def trigger_profile_reflection(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually triggers the auto-learning reflection Celery task."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    from xbot.tasks import run_persona_reflection
    run_persona_reflection.delay(str(profile_id))
    return {"status": "accepted", "message": "Auto-learning reflection triggered in background."}
