from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import random
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.analytics import AnalyticsSnapshot, FollowerSnapshot, FollowerChangeLog
from xbot.models.realgraph import RealGraphEdge
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter, sleep_think_time
from xbot.browser.actions.x_actions import *
from xbot.celery_app import celery_app
from xbot.ai.client import get_ai_client
from xbot.ai.planner import plan_session
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.ai.poll_generator import generate_poll
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.post_session import PostSessionProcessor
from xbot.growth.f4f_engine import populate_f4f_candidates, record_follow_action, record_unfollow_action

logger = logging.getLogger("xbot.tasks")

from .common import broadcast_session_log, extract_tweet_id_from_url

async def _auto_publish_pending_drafts_async() -> dict[str, Any]:
    """
    Automated continuous draft publisher:
    Periodically checks for profiles where `require_post_approval == False` or where drafts are APPROVED.
    Picks the next pending draft, acquires the browser lock, executes via Playwright,
    and marks Content.status = ContentStatus.POSTED!
    """
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ComposePost, ComposeThread, ReplyToTweet
    from xbot.browser.actions.poll_action import CreatePoll
    from xbot.models.content import Content, ContentStatus, ContentType
    from xbot.models.profile import Profile, ProfileStatus
    from xbot.safety.guard import SafetyGuard

    manager = BrowserManager()
    guard = SafetyGuard()
    published_count = 0
    errors = []

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile).where(Profile.status == ProfileStatus.ACTIVE))
            profiles = p_res.scalars().all()

            for prof in profiles:
                cfg_path = manager.base_profile_dir / prof.profile_slug
                config = load_config(cfg_path) if cfg_path.exists() else None
                require_approval = getattr(config, "require_post_approval", False) if config else False

                # Allow auto-publishing if require_post_approval is False or if draft status is explicitly APPROVED
                allowed_statuses = [ContentStatus.APPROVED, ContentStatus.DRAFT] if not require_approval else [ContentStatus.APPROVED]

                stmt_draft = (
                    select(Content)
                    .where(
                        Content.profile_id == prof.id,
                        Content.status.in_(allowed_statuses),
                    )
                    .order_by(Content.created_at.desc())
                    .limit(1)
                )
                d_res = await db.execute(stmt_draft)
                draft = d_res.scalar_one_or_none()
                if not draft:
                    continue

                # Check safety guard limits
                can_post = await guard.is_action_safe(db, prof.profile_slug, "post")
                if not can_post:
                    logger.info("Auto-publish postponed for %s: rate limits/cooldown active.", prof.profile_slug)
                    continue

                lock_acquired = False
                for _ in range(12):
                    if manager.acquire_lock(prof.profile_slug, timeout_seconds=120):
                        lock_acquired = True
                        break
                    import asyncio as _aio
                    await _aio.sleep(2.5)

                if not lock_acquired:
                    logger.info("Auto-publish postponed for %s: browser lock busy.", prof.profile_slug)
                    continue

                context = None
                success = False
                try:
                    logger.info("Auto-publishing staged %s draft %s for profile %s: '%s'", draft.content_type, draft.id, prof.profile_slug, draft.body[:50])
                    context = await manager.get_context(prof.profile_slug)
                    page = await context.new_page()

                    if draft.content_type == ContentType.POLL:
                        meta_poll = draft.ai_metadata.get("poll", {}) if draft.ai_metadata else {}
                        question = meta_poll.get("question") or draft.body.split("\n")[0]
                        options = meta_poll.get("options") or ["Yes", "No"]
                        duration_days = meta_poll.get("duration_days", 1)
                        screenshot_dir = str(Path(manager.base_profile_dir) / prof.profile_slug / "screenshots")
                        action = CreatePoll(screenshot_dir=screenshot_dir)
                        success = await action.execute(page, question=question, options=options, duration_days=duration_days)
                    elif draft.content_type in (ContentType.THREAD, "thread"):
                        tweets = []
                        if getattr(draft, "thread_items", None):
                            tweets = [item.text for item in draft.thread_items]
                        elif draft.ai_metadata and "thread_items" in draft.ai_metadata:
                            tweets = draft.ai_metadata["thread_items"]
                        elif draft.ai_metadata and "tweets" in draft.ai_metadata:
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
                        await guard.record_action_success(prof.profile_slug, "post")
                        published_count += 1
                        logger.info("Successfully auto-published draft %s to live X for profile %s!", draft.id, prof.profile_slug)

                        extracted_link = draft.ai_metadata.get("extracted_link") if draft.ai_metadata else None
                        if extracted_link:
                            try:
                                await sleep_with_jitter(2500)
                                first_reply_msg = f"Link / source breakdown: {extracted_link}"
                                reply_ok = await ReplyToTweet().execute(page, first_reply_msg)
                                if reply_ok:
                                    reply_rec = Content(
                                        profile_id=prof.id,
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
                    else:
                        meta = dict(draft.ai_metadata or {})
                        meta["publish_attempts"] = meta.get("publish_attempts", 0) + 1
                        draft.ai_metadata = meta
                        if meta["publish_attempts"] >= 2:
                            draft.status = ContentStatus.FAILED
                            logger.warning("Draft %s marked FAILED after %d attempts", draft.id, meta["publish_attempts"])
                        await db.commit()
                except Exception as ex:
                    logger.error("Error auto-publishing draft for %s: %s", prof.profile_slug, ex)
                    errors.append(f"{prof.profile_slug}: {ex}")
                    meta = dict(draft.ai_metadata or {})
                    meta["publish_attempts"] = meta.get("publish_attempts", 0) + 1
                    draft.ai_metadata = meta
                    if meta["publish_attempts"] >= 2:
                        draft.status = ContentStatus.FAILED
                    await db.commit()
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(prof.profile_slug)

        return {"status": "success", "published_count": published_count, "errors": errors if errors else None}
    except Exception as e:
        logger.error("Failed auto-publish cycle: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        await manager.stop()


@celery_app.task(name="xbot.tasks.auto_publish_pending_drafts")
def auto_publish_pending_drafts() -> dict[str, Any]:
    """Celery periodic task to automatically publish pending/approved drafts when require_post_approval is disabled."""
    logger.info("Starting auto-publish pending drafts Celery task...")
    return asyncio.run(_auto_publish_pending_drafts_async())
