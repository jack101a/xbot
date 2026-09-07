from __future__ import annotations
import xbot.api.profiles as profiles_api
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

async def _populate_profile_metrics(db: AsyncSession, p: Profile) -> Profile:
    from xbot.models.content import Content, ContentStatus
    from sqlalchemy import func

    stmt_snap = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == p.id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    snap = res_snap.scalar_one_or_none()
    p.followers_count = snap.followers if snap else 0
    p.following_count = snap.following if snap else 0
    p.posts_count = snap.total_tweets if (snap and snap.total_tweets > 0) else 0
    
    # Fallback to direct Content table count if snapshot not yet recorded
    if not p.posts_count:
        cnt_stmt = select(func.count(Content.id)).where(Content.profile_id == p.id, Content.status == ContentStatus.POSTED)
        cnt_res = await db.execute(cnt_stmt)
        p.posts_count = cnt_res.scalar() or 0

    p.impressions_24h = snap.impressions_24h if snap else 0
    p.engagements_24h = snap.engagements_24h if snap else 0
    p.engagement_rate = snap.engagement_rate if snap else 0.0
    p.likes_count = (snap.top_tweets or {}).get("likes_count", 0) if snap else 0
    p.retweets_count = (snap.top_tweets or {}).get("retweets_count", 0) if snap else 0
    p.recent_tweets = (snap.top_tweets or {}).get("recent_tweets", []) if snap else []
    return p

router = APIRouter()

@router.get("/", response_model=list[ProfileResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)) -> list[Profile]:
    """
    List all profiles in the system.
    """
    result = await db.execute(select(Profile))
    profiles = list(result.scalars().all())
    for p in profiles:
        await _populate_profile_metrics(db, p)
    return profiles

@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_in: ProfileCreate, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Create a new profile.
    """
    # Check if profile slug already exists
    existing = await db.execute(
        select(Profile).where(Profile.profile_slug == profile_in.profile_slug)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile with this slug already exists",
        )

    db_profile = Profile(**profile_in.model_dump())
    db.add(db_profile)
    await db.commit()
    await db.refresh(db_profile)
    await _populate_profile_metrics(db, db_profile)

    # Automatically create profile directory and initial persona.yaml if missing
    try:
        import yaml
        profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
        profile_dir.mkdir(parents=True, exist_ok=True)
        persona_path = profile_dir / "persona.yaml"
        if not persona_path.exists():
            default_persona = {
                "id": db_profile.profile_slug,
                "display_name": db_profile.display_name or db_profile.profile_slug,
                "x_handle": db_profile.x_handle,
                "identity": {
                    "background": "Autonomous AI creator and domain specialist."
                },
                "personality": {
                    "traits": ["analytical", "sharp", "witty", "curious"],
                    "values": ["high_signal", "transparency"],
                    "communication_style": "punchy_and_insightful"
                },
                "interests": {
                    "primary": ["AI", "technology", "growth", "automation"],
                    "secondary": ["coding", "systems"],
                    "will_not_discuss": ["spam", "generic buzzwords"]
                },
                "writing_style": {
                    "tone": "authoritative_yet_accessible",
                    "typical_length": "concise",
                    "formatting": ["micro_spacing", "punchy_lines"]
                },
                "goals": {
                    "short_term": ["grow to 10k followers organically"],
                    "long_term": ["establish authority in target niche"],
                    "content_pillars": ["Industry Trends", "Analysis", "Best Practices"]
                },
                "rules": {
                    "always": ["add value", "cite specific data or clear logic"],
                    "never": ["generic praise", "hashtag spam"]
                },
                "target_kols": [
                    {"handle": "elonmusk", "category": "tech", "priority": "high", "preferred_angle": "witty"},
                    {"handle": "sama", "category": "ai", "priority": "high", "preferred_angle": "contrarian"}
                ]
            }
            with open(persona_path, "w") as f:
                yaml.safe_dump(default_persona, f, sort_keys=False)
    except Exception as ex:
        logger.warning("Could not auto-generate persona.yaml for %s: %s", db_profile.profile_slug, ex)

    return db_profile

@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Get a profile by UUID.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    await _populate_profile_metrics(db, db_profile)
    return db_profile

@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    profile_in: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """
    Update a profile.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    update_data = profile_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)

    await db.commit()
    await db.refresh(db_profile)
    return db_profile

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete a profile.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    await db.delete(db_profile)
    await db.commit()

@router.post("/{profile_id}/pause", response_model=ProfileResponse)
async def pause_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Pause a profile's active scheduling.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    db_profile.status = ProfileStatus.PAUSED
    await db.commit()
    await db.refresh(db_profile)
    return db_profile

@router.post("/{profile_id}/resume", response_model=ProfileResponse)
async def resume_profile(
    profile_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Profile:
    """
    Resume a profile's active scheduling.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    db_profile.status = ProfileStatus.ACTIVE
    await db.commit()
    await db.refresh(db_profile)
    return db_profile



@router.post("/{profile_id}/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_profile_session(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Triggers an on-demand browser session for the given profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    if db_profile.status != ProfileStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile is {db_profile.status.value}, not active",
        )
    from xbot.tasks import run_session
    task = run_session.delay(str(db_profile.id))
    return {
        "status": "accepted",
        "task_id": task.id,
        "message": f"Session triggered for {db_profile.profile_slug}",
    }