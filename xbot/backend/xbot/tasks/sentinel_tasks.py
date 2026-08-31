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

from .common import extract_tweet_id_from_url

async def _fast_response_sentinel_async(base_profile_dir: Path | str | None = None) -> dict[str, Any]:
    """
    Periodically scans active conversation threads and mentions for all active profiles,
    prioritizes verified authors and accounts nearing the 15-minute response deadline,
    generates in-character debate catalyst replies, and posts them via browser.
    Captures the open-source X algorithm's +150x reply_engaged_by_author multiplier.
    """
    import xbot.tasks as tasks
    r = getattr(tasks, "redis", redis).from_url(settings.REDIS_URL)
    base_dir = Path(base_profile_dir) if base_profile_dir else Path("/home/ubuntu/projects/xbot/data/profiles")
    manager = BrowserManager()
    await manager.start()

    total_threads_checked = 0
    replies_posted = 0
    errors: list[str] = []

    try:
        from xbot.models.realgraph import ConversationThread, RealGraphEdge
        session_factory = getattr(tasks, "AsyncSessionLocal", AsyncSessionLocal)
        async with session_factory() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            active_profiles = res.scalars().all()

            if not active_profiles:
                return {
                    "status": "success",
                    "profiles_processed": 0,
                    "threads_checked": 0,
                    "replies_posted": 0,
                }

            now = datetime.datetime.utcnow()

            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = base_dir / profile_slug

                try:
                    load_persona_fn = getattr(tasks, "load_persona", load_persona)
                    persona = load_persona_fn(profile_dir)
                    load_config_fn = getattr(tasks, "load_config", load_config)
                    config = load_config_fn(profile_dir)
                    is_mock = getattr(config, "mock_mode", False)
                except Exception as ex:
                    logger.warning("Failed loading persona/config for %s: %s", profile_slug, ex)
                    continue

                guard = SafetyGuard(redis_url=settings.REDIS_URL, base_profile_dir=str(manager.base_profile_dir))

                # 1. Fetch active conversation threads nearing deadline (<15m window)
                th_stmt = (
                    select(ConversationThread)
                    .where(
                        ConversationThread.profile_id == profile_id,
                        ConversationThread.status.in_(["active", "awaiting_reply"]),
                        ConversationThread.deadline_15m >= now - datetime.timedelta(minutes=30),
                        ConversationThread.turn_count < ConversationThread.max_turns,
                    )
                    .order_by(
                        ConversationThread.target_is_verified.desc(),
                        ConversationThread.deadline_15m.asc(),
                    )
                    .limit(3)
                )
                th_res = await db.execute(th_stmt)
                active_threads = list(th_res.scalars().all())
                total_threads_checked += len(active_threads)

                if not active_threads:
                    continue

                for thread in active_threads:
                    # Check safety rate limits
                    if not await guard.is_action_safe(db, profile_slug, "reply"):
                        logger.info("Rate limit active for %s; halting fast response loop.", profile_slug)
                        break

                    # Check distributed lock
                    lock_key = f"xbot:lock:fast_reply:{thread.id}"
                    if not r.set(lock_key, "1", nx=True, ex=300):
                        continue

                    if not manager.acquire_lock(profile_slug, timeout_seconds=300):
                        continue

                    context = None
                    try:
                        if not is_mock:
                            timezone_str = config.schedule.timezone or "America/New_York"
                            context = await manager.get_context(
                                profile_slug=profile_slug,
                                timezone=timezone_str,
                                proxy_url=config.proxy_url,
                            )
                            page = await context.new_page()
                        else:
                            page = None

                        # Synthesize fast conversational counter-take (Value Hook -> Trade-off -> Debate Catalyst '?')
                        target_tweet_url = f"https://x.com/{thread.target_handle}/status/{thread.parent_tweet_id}"
                        
                        system_prompt = (
                            f"You are {persona.display_name} (@{persona.x_handle.lstrip('@')}). You are executing a fast-response "
                            f"conversational counter-reply on X to an active discussion turn.\n"
                            f"Tone: {persona.writing_style.tone}\n"
                            f"Traits: {', '.join(persona.personality.traits[:4])}\n"
                            f"Rules:\n"
                            f"- Concise, sharp, and natural (50-200 chars).\n"
                            f"- No forced questions or filler. No hashtags (#).\n"
                            f"- Zero AI fluff (no 'delve', 'supercharge', 'tapestry', 'testament'). Clean sentence case.\n"
                        )
                        user_prompt = (
                            f"Conversation so far with @{thread.target_handle}:\n"
                            f"{json.dumps(thread.conversation_history, indent=2)}\n\n"
                            f"Write an insightful, authentic in-character reply that advances the discussion naturally."
                        )

                        client_fn = getattr(tasks, "get_ai_client", get_ai_client)
                        client = client_fn()
                        completion = await client.chat.completions.create(
                            model=settings.MODEL_REPLY_ANALYSIS,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        )
                        reply_text = (completion.choices[0].message.content or "").strip()

                        # Execute reply via browser
                        success = False
                        if is_mock:
                            await asyncio.sleep(0.3)
                            success = True
                        else:
                            success = await ReplyToTweet().execute(
                                page,
                                reply_text,
                                tweet_url=target_tweet_url,
                            )

                        if success:
                            t_now = datetime.datetime.utcnow()
                            await guard.record_action_success(profile_slug, "reply", t_now)

                            # Advance thread state
                            thread.turn_count += 1
                            thread.last_action_at = t_now
                            history = list(thread.conversation_history or [])
                            history.append({"turn": thread.turn_count, "sender": "bot", "text": reply_text})
                            thread.conversation_history = history
                            if thread.turn_count >= thread.max_turns:
                                thread.status = "closed"
                            else:
                                thread.status = "awaiting_reply"
                                thread.deadline_15m = t_now + datetime.timedelta(minutes=15)

                            # Update or create RealGraphEdge
                            rg_stmt = select(RealGraphEdge).where(
                                RealGraphEdge.profile_id == profile_id,
                                RealGraphEdge.target_handle == thread.target_handle,
                            )
                            rg_res = await db.execute(rg_stmt)
                            edge = rg_res.scalar_one_or_none()
                            if not edge:
                                edge = RealGraphEdge(
                                    profile_id=profile_id,
                                    target_handle=thread.target_handle,
                                    is_verified=thread.target_is_verified,
                                    outbound_replies_count=1,
                                    inbound_author_replies_count=1,
                                    reciprocal_score=25.0 if thread.target_is_verified else 10.0,
                                    author_reply_rate=1.0,
                                    first_interacted_at=t_now,
                                    last_outbound_at=t_now,
                                    last_inbound_at=t_now,
                                )
                                db.add(edge)
                            else:
                                edge.outbound_replies_count += 1
                                edge.reciprocal_score = min(150.0, edge.reciprocal_score + 15.0)
                                edge.last_outbound_at = t_now

                            # Record action
                            act = Action(
                                profile_id=profile_id,
                                action_type=ActionType.REPLY,
                                target_url=target_tweet_url,
                                content=reply_text,
                                status=ActionStatus.COMPLETED,
                                result={
                                    "mode": "fast_response_sentinel",
                                    "target_handle": thread.target_handle,
                                    "turn": thread.turn_count,
                                    "thread_id": str(thread.id),
                                    "realgraph_score": edge.reciprocal_score if edge else 1.0,
                                },
                                executed_at=t_now,
                            )
                            db.add(act)
                            await db.commit()

                            replies_posted += 1
                            logger.info(
                                "Fast-Response reply posted for profile %s -> @%s (turn %d/%d)",
                                profile_slug,
                                thread.target_handle,
                                thread.turn_count,
                                thread.max_turns,
                            )
                    except Exception as th_ex:
                        logger.error("Error processing thread %s: %s", thread.id, th_ex)
                        errors.append(f"Thread {thread.id}: {th_ex}")
                    finally:
                        if context:
                            await context.close()
                        manager.release_lock(profile_slug)

        return {
            "status": "success" if not errors else "partial_success",
            "threads_checked": total_threads_checked,
            "replies_posted": replies_posted,
            "errors": errors if errors else None,
        }

    except Exception as overall_ex:
        logger.error("Fast response sentinel encountered critical error: %s", overall_ex)
        return {"status": "failed", "error": str(overall_ex)}
    finally:
        await manager.stop()


def fast_response_sentinel() -> dict[str, Any]:
    """Celery periodic task executing sub-15 minute conversational fast responses to capture +150x reply multipliers."""
    logger.info("Starting Celery fast-response sentinel task.")
    return asyncio.run(_fast_response_sentinel_async())
