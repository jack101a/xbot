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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.browser.manager import BrowserManager
from xbot.browser.actions.x_actions import ComposePost, ComposeThread, ReplyToTweet
from xbot.browser.timing import sleep_with_jitter
from xbot.browser.actions.poll_action import CreatePoll
from xbot.safety.guard import SafetyGuard

logger = logging.getLogger("xbot.api.profiles")
router = APIRouter()


@router.post("/{profile_id}/drafts/{content_id}/approve", response_model=dict[str, Any])
async def approve_and_publish_draft(
    profile_id: uuid.UUID,
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approves a staged draft post/poll/thread and publishes it to live X."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile_slug = db_profile.profile_slug
    profile_db_id = db_profile.id

    c_res = await db.execute(select(Content).where(Content.id == content_id).where(Content.profile_id == profile_id))
    draft = c_res.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft content not found")

    # Mark approved in DB immediately
    draft.status = ContentStatus.APPROVED
    await db.commit()

    manager = BrowserManager()
    guard = SafetyGuard()
    
    # Try acquiring lock with retry
    lock_acquired = False
    for _ in range(3):
        if manager.acquire_lock(profile_slug, timeout_seconds=60):
            lock_acquired = True
            break
        await asyncio.sleep(1.5)

    if not lock_acquired:
        from xbot.tasks import auto_publish_pending_drafts
        auto_publish_pending_drafts.delay()
        return {
            "status": "queued",
            "message": "Draft approved! Queued in background worker for immediate publishing once browser is ready.",
            "content_id": str(draft.id),
        }

    context = None
    success = False
    try:
        await manager.start()
        context = await manager.get_context(profile_slug)
        page = await context.new_page()
        page.set_default_timeout(35000)

        if draft.content_type == ContentType.POLL:
            meta_poll = draft.ai_metadata.get("poll", {}) if draft.ai_metadata else {}
            question = meta_poll.get("question") or draft.body.split("\n")[0]
            options = meta_poll.get("options") or ["Yes", "No"]
            duration_days = meta_poll.get("duration_days", 1)
            screenshot_dir = str(Path(manager.base_profile_dir) / profile_slug / "screenshots")
            action = CreatePoll(screenshot_dir=screenshot_dir)
            success = await action.execute(page, question=question, options=options, duration_days=duration_days)
        elif draft.content_type in (ContentType.THREAD, "thread"):
            tweets = []
            if getattr(draft, "thread_items", None) and len(draft.thread_items) > 0:
                tweets = [item.text for item in draft.thread_items]
            elif draft.ai_metadata and "thread_items" in draft.ai_metadata and isinstance(draft.ai_metadata["thread_items"], list):
                raw_items = draft.ai_metadata["thread_items"]
                tweets = [item if isinstance(item, str) else item.get("text", "") for item in raw_items]
            elif draft.ai_metadata and "tweets" in draft.ai_metadata and isinstance(draft.ai_metadata["tweets"], list):
                tweets = draft.ai_metadata["tweets"]
            else:
                tweets = [p.strip() for p in draft.body.split("\n\n") if p.strip()]
            action = ComposeThread()
            media_paths = draft.ai_metadata.get("media_paths") if draft.ai_metadata else None
            res = await action.execute(page, tweets=tweets, media_paths=media_paths)
            success = res.get("status") == "success"
            if success and res.get("root_tweet_id"):
                draft.tweet_id = res.get("root_tweet_id")
        else:
            action = ComposePost()
            gif_q = draft.ai_metadata.get("gif_query") if draft.ai_metadata else None
            media_paths = draft.ai_metadata.get("media_paths") if draft.ai_metadata else None
            success = await action.execute(page, text=draft.body, media_paths=media_paths, gif_query=gif_q)

        if success:
            draft.status = ContentStatus.POSTED
            draft.posted_at = datetime.datetime.utcnow()
            await db.commit()
            await guard.record_action_success(profile_slug, "post")

            # 1st-reply link injection if extracted_link exists
            extracted_link = draft.ai_metadata.get("extracted_link") if draft.ai_metadata else None
            if extracted_link:
                try:
                    await sleep_with_jitter(2500)
                    first_reply_msg = f"Link / source breakdown: {extracted_link}"
                    reply_ok = await ReplyToTweet().execute(page, first_reply_msg)
                    if reply_ok:
                        reply_rec = Content(
                            profile_id=profile_db_id,
                            content_type=ContentType.REPLY,
                            body=first_reply_msg,
                            status=ContentStatus.POSTED,
                            posted_at=datetime.datetime.utcnow(),
                            ai_metadata={"is_1st_reply_injection": True, "direct_publish": True}
                        )
                        db.add(reply_rec)
                        await db.commit()
                except Exception as link_e:
                    logger.warning("Failed to post 1st-reply link injection: %s", link_e)

        return {
            "status": "success" if success else "failed",
            "message": "Draft approved and published to live X!" if success else "Browser returned failure.",
            "content_id": str(draft.id),
        }
    except Exception as e:
        logger.error(f"Error publishing draft: {e}", exc_info=True)
        try:
            await db.rollback()
        except Exception:
            pass
        from xbot.tasks import auto_publish_pending_drafts
        auto_publish_pending_drafts.delay()
        return {
            "status": "queued",
            "message": "Draft approved! Queued in background worker for execution.",
            "content_id": str(content_id),
        }
    finally:
        manager.release_lock(profile_slug)
        if context:
            try:
                await context.close()
            except Exception:
                pass
        try:
            await manager.stop()
        except Exception:
            pass


@router.post("/{profile_id}/drafts/approve-all", response_model=dict[str, Any])
async def approve_all_pending_drafts(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approves all staged drafts for immediate autonomous sequential publishing."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    c_res = await db.execute(
        select(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status == ContentStatus.DRAFT)
    )
    drafts = c_res.scalars().all()
    count = len(drafts)
    if count == 0:
        return {"status": "success", "message": "No pending drafts to approve.", "count": 0}

    for d in drafts:
        d.status = ContentStatus.APPROVED
    await db.commit()

    try:
        from xbot.tasks import auto_publish_pending_drafts
        auto_publish_pending_drafts.delay()
    except Exception as t_err:
        logger.warning("Could not dispatch auto_publish_pending_drafts Celery task: %s", t_err)

    return {
        "status": "success",
        "message": f"Successfully approved {count} drafts for autonomous publishing!",
        "count": count,
    }
