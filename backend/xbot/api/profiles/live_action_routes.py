from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.session import Action, ActionStatus, ActionType
from xbot.browser.manager import BrowserManager
from xbot.browser.actions.x_actions import FollowUser, LikeTweet
from xbot.safety.guard import SafetyGuard

logger = logging.getLogger("xbot.api.profiles")
router = APIRouter()


class LiveFollowRequest(BaseModel):
    target_username: str = Field(..., description="Target username / handle to follow (e.g. @sama or sama)")


class LiveLikeRequest(BaseModel):
    tweet_url: str = Field(..., description="Full URL of the tweet to like")


@router.post("/{profile_id}/follow-user", response_model=dict[str, Any])
async def follow_user_live(
    profile_id: uuid.UUID,
    req: LiveFollowRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live follow action on X for the target username."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    manager = BrowserManager()
    guard = SafetyGuard()
    if not await guard.is_action_safe(db, db_profile.profile_slug, "follow"):
        raise HTTPException(status_code=429, detail="Safety guard rate limit or cooldown active for follow action.")

    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=409, detail="Browser is currently busy with another action.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()

        clean_user = req.target_username.lstrip("@").strip()
        action = FollowUser()
        success = await action.execute(page, username=clean_user)

        if success:
            await guard.record_action_success(db_profile.profile_slug, "follow")

        return {
            "status": "success" if success else "failed",
            "message": f"Successfully followed @{clean_user}" if success else f"Failed to follow @{clean_user}",
            "target_username": clean_user,
        }
    except Exception as e:
        logger.error(f"Error executing live follow: {e}", exc_info=True)
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


@router.post("/{profile_id}/like-tweet", response_model=dict[str, Any])
async def like_tweet_live(
    profile_id: uuid.UUID,
    req: LiveLikeRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Executes a live like action on X for the target tweet."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    manager = BrowserManager()
    guard = SafetyGuard()
    if not await guard.is_action_safe(db, db_profile.profile_slug, "like"):
        raise HTTPException(status_code=429, detail="Safety guard rate limit or cooldown active for like action.")

    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=409, detail="Browser is currently busy with another action.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()

        action = LikeTweet()
        success = await action.execute(page, tweet_url=req.tweet_url)

        if success:
            await guard.record_action_success(db_profile.profile_slug, "like")

        return {
            "status": "success" if success else "failed",
            "message": f"Successfully liked tweet {req.tweet_url}" if success else f"Failed to like tweet",
            "tweet_url": req.tweet_url,
        }
    except Exception as e:
        logger.error(f"Error executing live like: {e}", exc_info=True)
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
