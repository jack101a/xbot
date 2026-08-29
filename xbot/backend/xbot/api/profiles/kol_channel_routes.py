from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile
from xbot.persona import load_persona
from xbot.persona.loader import yaml

logger = logging.getLogger("xbot.api.profiles")
router = APIRouter()


class KOLChannelCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, description="Channel slug identifier")
    display_title: str = Field(..., min_length=2, description="Display title")
    description: str = Field("", description="Channel description")
    is_active: bool = Field(True, description="Active status")
    priority_weight: float = Field(1.0, ge=0.1, le=5.0, description="Priority weight multiplier")
    preferred_angle: str = Field("insight", description="Preferred response angle")


class AddKOLTargetRequest(BaseModel):
    handle: str = Field(..., min_length=1, description="KOL X handle")
    priority: str = Field("medium", description="Priority tier: high, medium, low")
    preferred_angle: str = Field("insight", description="Preferred response angle")


@router.get("/{profile_id}/kol-channels", response_model=dict[str, Any])
async def get_profile_kol_channels(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves all categorized KOL Sniper channels and their assigned target accounts."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_slug = db_profile.profile_slug
    profile_dir = Path(settings.BASE_PROFILE_DIR) / profile_slug
    persona_yaml = profile_dir / "persona.yaml"

    if not persona_yaml.exists():
        return {"channels": [], "targets": []}

    try:
        persona = load_persona(profile_dir)
        channels = [ch.model_dump() for ch in persona.kol_channels] if persona.kol_channels else []
        targets = [t.model_dump() for t in persona.target_kols] if persona.target_kols else []

        # Default standard channels if none declared in YAML
        if not channels:
            channels = [
                {"name": "anime_manga", "display_title": "Anime & Manga Radar", "description": "Animation, manga & theory debates", "is_active": True, "priority_weight": 1.2, "preferred_angle": "insight"},
                {"name": "movies_cinema", "display_title": "Cinema & Pop Culture", "description": "Box office, directors, Nolan & trailers", "is_active": True, "priority_weight": 1.1, "preferred_angle": "contrarian"},
                {"name": "consumer_tech", "display_title": "Consumer Tech & Hardware", "description": "Smartphones, cameras, hardware & Apple events", "is_active": True, "priority_weight": 1.0, "preferred_angle": "witty"},
                {"name": "ai_ecosystem", "display_title": "AI & Developer Frontier", "description": "Claude, OpenAI, Gemini, open source models", "is_active": True, "priority_weight": 1.3, "preferred_angle": "framework"},
                {"name": "growth_f4f", "display_title": "Creator Growth & Blue Tick Peers", "description": "Active verified creator accounts", "is_active": True, "priority_weight": 0.9, "preferred_angle": "debate_catalyst"},
            ]

        # Calculate target counts per channel
        for ch in channels:
            ch_name = ch.get("name")
            ch["target_count"] = sum(1 for t in targets if t.get("category") == ch_name)

        return {
            "status": "success",
            "profile_id": str(profile_id),
            "channels": channels,
            "targets": targets,
            "total_channels": len(channels),
            "total_targets": len(targets),
        }
    except Exception as e:
        logger.error("Failed to load KOL channels for %s: %s", profile_slug, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{profile_id}/kol-channels/{channel_name}/toggle", response_model=dict[str, Any])
async def toggle_kol_channel_status(
    profile_id: uuid.UUID,
    channel_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Toggles active/inactive state of a specific KOL Sniper Channel."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_dir = Path(settings.BASE_PROFILE_DIR) / db_profile.profile_slug
    persona_yaml = profile_dir / "persona.yaml"
    if not persona_yaml.exists():
        raise HTTPException(status_code=404, detail="Persona file not found")

    with open(persona_yaml, "r", encoding="utf-8") as f:
        data = yaml.load(f) or {}

    channels = data.get("kol_channels", [])
    found = False
    new_state = True

    for ch in channels:
        if ch.get("name") == channel_name:
            ch["is_active"] = not ch.get("is_active", True)
            new_state = ch["is_active"]
            found = True
            break

    if not found:
        # Create channel entry if it did not exist yet
        channels.append({
            "name": channel_name,
            "display_title": channel_name.replace("_", " ").title(),
            "description": "",
            "is_active": False,
            "priority_weight": 1.0,
            "preferred_angle": "insight",
        })
        new_state = False
        data["kol_channels"] = channels

    with open(persona_yaml, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return {
        "status": "success",
        "channel_name": channel_name,
        "is_active": new_state,
        "message": f"Channel '{channel_name}' is now {'active' if new_state else 'paused'}.",
    }
