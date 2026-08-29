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
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus
from xbot.models.analytics import FollowerChangeLog
from xbot.models.session import Action, Session
from xbot.persona.loader import load_persona
from xbot.browser.manager import BrowserManager

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()

from pydantic import BaseModel, Field
from xbot.persona.card_parser import load_raw_card, map_card_to_persona
from xbot.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

from fastapi import APIRouter
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

    from playwright.async_api import async_playwright
    import os

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    state_path = profile_dir / "storage_state.json"

    try:
        if not os.environ.get("DISPLAY"):
            os.environ["DISPLAY"] = ":0"

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--start-maximized"]
            )
            context = await browser.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto("https://x.com/i/flow/login")
            
            closed_event = asyncio.Event()
            page.on("close", lambda: closed_event.set())
            
            try:
                await asyncio.wait_for(closed_event.wait(), timeout=300.0)
            except asyncio.TimeoutError:
                pass
            
            await context.storage_state(path=str(state_path))
            await browser.close()

        if state_path.exists() and state_path.stat().st_size > 100:
            return {"status": "success", "message": "Login session captured and stored successfully."}
        else:
            return {"status": "cancelled", "message": "Browser closed without logging in."}

    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run login browser session: {str(ex)}"
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
    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
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

    profile_dir = Path(BASE_PROFILE_DIR) / db_profile.profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    storage_state = format_storage_state(
        auth_token=auth_token.strip(),
        ct0=ct0.strip(),
        twid=twid.strip() if twid else None,
    )
