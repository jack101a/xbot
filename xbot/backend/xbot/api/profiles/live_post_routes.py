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
from xbot.safety.guard import SafetyGuard

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()

class LivePostRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=280)
    media_paths: list[str] | None = None
    gif_query: str | None = None

class LiveReplyRequest(BaseModel):
    tweet_url: str = Field(..., min_length=5)
    reply_text: str = Field(..., min_length=1, max_length=280)

class LivePollRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=200)
    options: list[str] = Field(..., min_length=2, max_length=4)
    duration_days: int = Field(default=1, ge=1, le=7)

class LiveThreadRequest(BaseModel):
    tweets: list[str] = Field(..., min_length=2, max_length=10)

class LiveFollowRequest(BaseModel):
    username: str = Field(..., min_length=1)

class LiveLikeRequest(BaseModel):
    tweet_url: str = Field(..., min_length=5)

@router.post("/{profile_id}/publish-post", response_model=dict[str, Any])
async def publish_live_post(
    profile_id: uuid.UUID,
    req: LivePostRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live post directly to the user's X timeline using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposePost
    from xbot.models.content import Content, ContentStatus

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is currently busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = ComposePost()
        success = await action.execute(
            page,
            text=req.text,
            media_paths=req.media_paths,
            gif_query=req.gif_query,
        )
        
        # Record in DB
        content_row = Content(
            profile_id=db_profile.id,
            body=req.text,
            content_type="post",
            status=ContentStatus.POSTED if success else ContentStatus.FAILED,
            ai_metadata={
                "media_paths": req.media_paths,
                "gif_query": req.gif_query,
            }
        )
        db.add(content_row)
        await db.commit()

        return {
            "status": "success" if success else "failed",
            "message": "Post published to X timeline successfully!" if success else "Failed to publish post to X.",
            "post_text": req.text,
            "media_paths": req.media_paths,
        }
    except Exception as e:
        logger.error(f"Error publishing live post: {e}", exc_info=True)
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

@router.post("/{profile_id}/publish-reply", response_model=dict[str, Any])
async def publish_live_reply(
    profile_id: uuid.UUID,
    req: LiveReplyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live reply directly to a target tweet on X using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ReplyToTweet

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = ReplyToTweet()
        success = await action.execute(page, reply_text=req.reply_text, tweet_url=req.tweet_url)

        return {
            "status": "success" if success else "failed",
            "message": "Reply published to X thread successfully!" if success else "Failed to publish reply to X.",
            "reply_text": req.reply_text,
            "target_tweet": req.tweet_url,
        }
    except Exception as e:
        logger.error(f"Error publishing live reply: {e}", exc_info=True)
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

@router.post("/{profile_id}/publish-poll", response_model=dict[str, Any])
async def publish_live_poll(
    profile_id: uuid.UUID,
    req: LivePollRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live interactive poll directly to X using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.poll_action import CreatePoll

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        action = CreatePoll()
        clean_opts = [opt[:25].strip() for opt in req.options if opt.strip()]
        success = await action.execute(
            page,
            question=req.question,
            options=clean_opts,
            duration_days=req.duration_days,
        )

        return {
            "status": "success" if success else "failed",
            "message": "Poll published to X successfully!" if success else "Failed to create poll on X.",
            "question": req.question,
            "options": clean_opts,
        }
    except Exception as e:
        logger.error(f"Error publishing live poll: {e}", exc_info=True)
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

@router.post("/{profile_id}/publish-thread", response_model=dict[str, Any])
async def publish_live_thread(
    profile_id: uuid.UUID,
    req: LiveThreadRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publishes a live multi-tweet thread directly to X using Playwright."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposeThread

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()
        page.set_default_timeout(35000)

        action = ComposeThread()
        res = await action.execute(page, tweets=req.tweets)
        success = res.get("status") == "success"

        return {
            "status": "success" if success else "failed",
            "message": "Thread published to X successfully!" if success else f"Failed to publish thread: {res.get('error')}",
            "total_tweets": len(req.tweets),
            "root_tweet_id": res.get("root_tweet_id"),
        }
    except Exception as e:
        logger.error(f"Error publishing live thread: {e}", exc_info=True)
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
