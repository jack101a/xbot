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
from xbot.utils.time import now_ist
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
    from xbot.contracts.browser import BrowserActionType, BrowserRequest
    from xbot.container import get_container
    from xbot.models.content import Content, ContentStatus, ContentType
    from xbot.models.profile import Profile, ProfileStatus
    from xbot.safety.guard import SafetyGuard

    container = get_container()
    guard = SafetyGuard()
    published_count = 0
    errors = []

    try:
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile).where(Profile.status == ProfileStatus.ACTIVE))
            profiles = p_res.scalars().all()

            for prof in profiles:
                cfg_path = Path(settings.BASE_PROFILE_DIR) / prof.profile_slug
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
                    .order_by(Content.created_at.asc())
                    .limit(10)
                )
                d_res = await db.execute(stmt_draft)
                candidates = d_res.scalars().all()
                draft = None
                now_curr = now_ist()
                for c in candidates:
                    sched_str = (c.ai_metadata or {}).get("scheduled_for")
                    if sched_str:
                        try:
                            sched_dt = datetime.datetime.fromisoformat(sched_str.replace("Z", "+00:00")).replace(tzinfo=None)
                            if sched_dt > now_curr:
                                continue
                        except Exception:
                            pass

                    # Topic cooldown check (120-180 min random gap for same topic)
                    topic_tag = (c.ai_metadata or {}).get("topic_tag") or (c.ai_metadata or {}).get("topic") or (c.ai_metadata or {}).get("trend_title")
                    if topic_tag:
                        from xbot.ai.topic_utils import extract_topic_tag
                        normalized_target = extract_topic_tag(str(topic_tag))
                        cooldown_minutes = random.randint(120, 180)
                        cooldown_cutoff = now_curr - datetime.timedelta(minutes=cooldown_minutes)

                        same_topic_stmt = (
                            select(Content)
                            .where(
                                Content.profile_id == prof.id,
                                Content.status == ContentStatus.POSTED,
                                Content.posted_at > cooldown_cutoff,
                            )
                            .order_by(Content.posted_at.desc())
                            .limit(20)
                        )
                        recent_posted = (await db.execute(same_topic_stmt)).scalars().all()
                        topic_too_recent = False
                        for rp in recent_posted:
                            rp_tag = (rp.ai_metadata or {}).get("topic_tag") or (rp.ai_metadata or {}).get("topic") or (rp.ai_metadata or {}).get("trend_title")
                            if rp_tag and extract_topic_tag(str(rp_tag)) == normalized_target:
                                elapsed_mins = int((now_curr - (rp.posted_at or now_curr)).total_seconds() / 60)
                                logger.info(
                                    "Topic cooldown active for profile %s: skipping draft %s ('%s'). Same topic '%s' posted %d min ago (< %d min cooldown)",
                                    prof.profile_slug,
                                    c.id,
                                    topic_tag,
                                    rp_tag,
                                    elapsed_mins,
                                    cooldown_minutes,
                                )
                                topic_too_recent = True
                                break
                        if topic_too_recent:
                            continue

                    draft = c
                    break

                if not draft:
                    continue

                # Check safety guard limits
                can_post = await guard.is_action_safe(db, prof.profile_slug, "post")
                if not can_post:
                    logger.info("Auto-publish postponed for %s: rate limits/cooldown active.", prof.profile_slug)
                    continue

                success = False
                try:
                    logger.info("Auto-publishing staged %s draft %s for profile %s: '%s'", draft.content_type, draft.id, prof.profile_slug, draft.body[:50])

                    if draft.content_type in (ContentType.POLL, "poll"):
                        meta_poll = (draft.ai_metadata or {}).get("poll", {})
                        q = meta_poll.get("question") or draft.body.split("\n")[0]
                        opts = meta_poll.get("options") or ["Yes", "No"]
                        duration_days = meta_poll.get("duration_days", 1)
                        req = BrowserRequest(
                            profile_slug=prof.profile_slug,
                            action=BrowserActionType.POLL,
                            params={"question": q, "options": opts, "duration_minutes": duration_days * 1440},
                            timeout_seconds=300,
                        )
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
                        media_paths = draft.ai_metadata.get("media_paths") if draft.ai_metadata else None

                        # Safety Invariant: Guarantee media & closer hashtags for threads
                        topic = (draft.ai_metadata or {}).get("topic") or (draft.ai_metadata or {}).get("trend_title") or (tweets[0] if tweets else "")
                        from xbot.ai.smart_media_director import resolve_post_media_waterfall, ensure_main_post_hashtags
                        if tweets:
                            tweets[-1] = ensure_main_post_hashtags(tweets[-1], topic)
                        if not media_paths and tweets:
                            logger.info("Auto-publish safety guard: thread %s has no media. Executing waterfall resolver...", draft.id)
                            res_m, _, tweets[0] = await resolve_post_media_waterfall(topic, tweets[0], prof.profile_slug, allow_gif=False)
                            if res_m:
                                media_paths = res_m
                                meta = dict(draft.ai_metadata or {})
                                meta["media_paths"] = res_m
                                draft.ai_metadata = meta
                                await db.commit()

                        req = BrowserRequest(
                            profile_slug=prof.profile_slug,
                            action=BrowserActionType.THREAD,
                            params={"tweets": tweets, "media_paths": media_paths},
                            timeout_seconds=360,
                        )
                    else:
                        gif_q = draft.ai_metadata.get("gif_query") if draft.ai_metadata else None
                        media_paths = None
                        if draft.ai_metadata:
                            if draft.ai_metadata.get("media_paths"):
                                media_paths = [p for p in draft.ai_metadata["media_paths"] if os.path.exists(p)]
                            elif draft.ai_metadata.get("image_path") and os.path.exists(draft.ai_metadata["image_path"]):
                                media_paths = [draft.ai_metadata["image_path"]]
                            elif draft.ai_metadata.get("media_urls"):
                                media_paths = [u for u in draft.ai_metadata["media_urls"] if os.path.exists(u)]

                        # Discard junk / generic gif_query
                        if gif_q:
                            from xbot.ai.smart_media_director import BLACK_LISTED_HASHTAGS
                            g_clean = gif_q.strip().lower()
                            if g_clean in BLACK_LISTED_HASHTAGS or any(j in g_clean for j in ("trending", "posts", "entertainment", "tech news", "news")):
                                logger.info("Auto-publish safety guard: Discarding junk gif_query '%s' for draft %s", gif_q, draft.id)
                                gif_q = None

                        # Safety Invariant: Guarantee media & hashtags for standalone main posts
                        topic = (draft.ai_metadata or {}).get("topic") or (draft.ai_metadata or {}).get("trend_title") or draft.body
                        from xbot.ai.smart_media_director import resolve_post_media_waterfall, ensure_main_post_hashtags
                        draft.body = ensure_main_post_hashtags(draft.body, topic)

                        if not media_paths and not gif_q:
                            logger.info("Auto-publish safety guard: standalone post %s has no valid media. Executing waterfall resolver...", draft.id)
                            resolved_media, resolved_gif, draft.body = await resolve_post_media_waterfall(
                                topic=topic,
                                post_text=draft.body,
                                profile_slug=prof.profile_slug,
                                allow_gif=True,
                            )
                            if resolved_media:
                                media_paths = resolved_media
                            elif resolved_gif:
                                gif_q = resolved_gif
                            meta = dict(draft.ai_metadata or {})
                            meta["media_paths"] = media_paths
                            meta["gif_query"] = gif_q
                            draft.ai_metadata = meta
                            await db.commit()

                        req = BrowserRequest(
                            profile_slug=prof.profile_slug,
                            action=BrowserActionType.POST,
                            params={"text": draft.body, "media_paths": media_paths, "gif_query": gif_q},
                            timeout_seconds=300,
                        )

                    resp = await container.browser.execute(req)
                    success = resp.status == "success" or (resp.action_result and resp.action_result.status == "success")

                    if success:
                        draft.status = ContentStatus.POSTED
                        draft.posted_at = now_ist()
                        if resp.action_result and resp.action_result.target_id:
                            draft.tweet_id = resp.action_result.target_id
                        await db.commit()
                        await guard.record_action_success(prof.profile_slug, "post")
                        published_count += 1
                        logger.info("Successfully auto-published draft %s to live X for profile %s!", draft.id, prof.profile_slug)

                        extracted_link = draft.ai_metadata.get("extracted_link") if draft.ai_metadata else None
                        if extracted_link:
                            try:
                                first_reply_msg = f"Link / source breakdown: {extracted_link}"
                                reply_req = BrowserRequest(
                                    profile_slug=prof.profile_slug,
                                    action=BrowserActionType.REPLY,
                                    params={"text": first_reply_msg, "tweet_url": getattr(resp.action_result, "url", None)},
                                    timeout_seconds=60,
                                )
                                reply_resp = await container.browser.execute(reply_req)
                                if reply_resp.status == "success":
                                    reply_rec = Content(
                                        profile_id=prof.id,
                                        content_type=ContentType.REPLY,
                                        body=first_reply_msg,
                                        status=ContentStatus.POSTED,
                                        posted_at=now_ist(),
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

        return {"status": "success", "published_count": published_count, "errors": errors if errors else None}
    except Exception as e:
        logger.error("Failed auto-publish cycle: %s", e)
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="xbot.tasks.auto_publish_pending_drafts")
def auto_publish_pending_drafts() -> dict[str, Any]:
    """Celery periodic task to automatically publish pending/approved drafts when require_post_approval is disabled."""
    logger.info("Starting auto-publish pending drafts Celery task...")
    return asyncio.run(_auto_publish_pending_drafts_async())
