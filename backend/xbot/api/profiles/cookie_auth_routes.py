from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import xbot.api.profiles as profiles_api
from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, Session
from xbot.models.analytics import AnalyticsSnapshot
from xbot.browser.manager import BrowserManager
from xbot.browser.actions.sync_profile_action import SyncProfileFromX, SyncProfileAction
from xbot.browser.auth import inspect_profile_auth_status, parse_cookie_string, format_storage_state
from .analytics_routes import _populate_profile_metrics
from .constants import BASE_PROFILE_DIR

logger = logging.getLogger("xbot.api.profiles")
router = APIRouter()


@router.post("/{profile_id}/login-session", response_model=dict[str, Any])
async def launch_login_session(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Launches a headed Playwright browser on the host display pointing to X.com login.
    Captures cookies/storage state upon browser window close and saves it for persistent session.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    from xbot.infra.browser.interactive_login import run_interactive_login_session

    try:
        res = await run_interactive_login_session(db_profile.profile_slug)
        return res
    except Exception as e:
        logger.error("Interactive login failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interactive login failed: {e}",
        )


@router.get("/{profile_id}/auth-status", response_model=dict[str, Any])
async def get_profile_auth_status(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Inspects storage_state.json cookies and returns session health and profile stats."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    await _populate_profile_metrics(db, db_profile)
    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    auth_status = inspect_profile_auth_status(profile_dir)
    auth_status["avatar_url"] = db_profile.avatar_url
    auth_status["followers_count"] = getattr(db_profile, "followers_count", 0)
    auth_status["following_count"] = getattr(db_profile, "following_count", 0)
    return auth_status


class ImportCookiesRequest(BaseModel):
    auth_token: str | None = None
    ct0: str | None = None
    raw_cookies: str | None = None
    twid: str | None = None


@router.post("/{profile_id}/import-cookies", response_model=dict[str, Any])
async def import_profile_cookies(
    profile_id: uuid.UUID,
    req: ImportCookiesRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Imports auth cookies directly or from a raw cookie header/JSON string."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    auth_token = req.auth_token
    ct0 = req.ct0
    twid = req.twid

    if req.raw_cookies:
        parsed = parse_cookie_string(req.raw_cookies)
        auth_token = auth_token or parsed.get("auth_token")
        ct0 = ct0 or parsed.get("ct0")
        twid = twid or parsed.get("twid")

    if not auth_token or not ct0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both auth_token and ct0 cookies are required to import session.",
        )

    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state = format_storage_state(
        auth_token=auth_token.strip(),
        ct0=ct0.strip(),
        twid=twid.strip() if twid else None,
    )
    state_path = profile_dir / "storage_state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(storage_state, f, indent=2)

    logger.info("Imported session cookies for profile %s into %s", db_profile.profile_slug, state_path)

    return {
        "status": "success",
        "message": "Cookies imported successfully and storage_state.json updated.",
        "auth_status": inspect_profile_auth_status(profile_dir),
    }


from .sync_routes import sync_profile_from_x_endpoint, router as sync_router
router.include_router(sync_router)
