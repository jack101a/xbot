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


@router.post("/{profile_id}/upload-media", response_model=dict[str, Any])
async def upload_profile_media(
    profile_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Uploads an image or media file to the profile's media library."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    media_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    clean_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    target_path = media_dir / clean_name

    contents = await file.read()
    with open(target_path, "wb") as f:
        f.write(contents)

    return {
        "status": "success",
        "filename": clean_name,
        "file_path": str(target_path),
        "size_bytes": len(contents),
    }

@router.get("/{profile_id}/media", response_model=list[dict[str, Any]])
async def list_profile_media(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists all available images/media files for this profile."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    media_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug / "media"
    if not media_dir.exists():
        return []

    files = []
    for p in media_dir.glob("*.*"):
        if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4"]:
            files.append({
                "filename": p.name,
                "file_path": str(p),
                "size_bytes": p.stat().st_size,
                "modified_at": datetime.datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            })
    return sorted(files, key=lambda x: x["modified_at"], reverse=True)
