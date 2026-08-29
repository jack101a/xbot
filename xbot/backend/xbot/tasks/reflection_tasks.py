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

from .common import broadcast_session_log

async def _run_evergreen_recycling_async(profile_id_str: str) -> dict[str, Any]:
    """Background task to find a high-performing past tweet and recycle it."""
    profile_id = uuid.UUID(profile_id_str)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        profile_slug = profile.profile_slug
        
        # 1. Query posted content older than 7 days
        seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        stmt = select(Content).where(
            Content.profile_id == profile_id,
            Content.status == ContentStatus.POSTED,
            Content.posted_at < seven_days_ago
        )
        res = await db.execute(stmt)
        contents = res.scalars().all()
        
        if not contents:
            return {"status": "skipped", "reason": "No evergreen candidates found."}
            
        # 2. Score based on performance
        def score_content(c: Content) -> float:
            if not c.performance: return 0.0
            likes = c.performance.get("likes", 0)
            retweets = c.performance.get("retweets", 0)
            return likes * 1.0 + retweets * 2.0
            
        scored = sorted(contents, key=score_content, reverse=True)
        best = scored[0]
        
        if score_content(best) == 0 and len(scored) > 0:
            best = random.choice(scored)
            
        logger.info("Evergreen selected content %s for recycling (Profile: %s)", best.id, profile_slug)
        
        # 3. Post it using Playwright
        manager = BrowserManager()
        await manager.start()
        
        if not manager.acquire_lock(profile_slug):
            await manager.stop()
            return {"status": "failed", "error": "Redis browser lock collision."}
            
        context = None
        try:
            config = load_config(manager.base_profile_dir / profile_slug)
            is_mock = getattr(config, "mock_mode", False)
            recycled_text = f"🔄 Vault highlight:\n\n{best.body}"
            
            if is_mock:
                await asyncio.sleep(0.5)
                success = True
                logger.info("🧪 [MOCK / DEMO MODE] Simulated evergreen recycling post: %s", recycled_text)
            else:
                timezone_str = config.schedule.timezone or "America/New_York"
                
                context = await manager.get_context(
                    profile_slug=profile_slug,
                    timezone=timezone_str,
                    proxy_url=config.proxy_url,
                )
                page = await context.new_page()
                
                await page.goto("https://x.com/home")
                success = await ComposePost().execute(page, recycled_text)
            
            if success:
                new_c = Content(
                    profile_id=profile_id,
                    content_type=best.content_type,
                    body=recycled_text,
                    status=ContentStatus.POSTED,
                    posted_at=datetime.datetime.utcnow(),
                    ai_metadata={"evergreen_recycled_from": str(best.id)}
                )
                db.add(new_c)
                await db.commit()
                return {"status": "success", "recycled_id": str(best.id)}
            else:
                return {"status": "failed", "error": "ComposePost execution failed."}
                
        except Exception as ex:
            logger.error("Evergreen task crash: %s", ex)
            return {"status": "failed", "error": str(ex)}
            
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)
            await manager.stop()


def run_evergreen_recycling(profile_id: str) -> dict[str, Any]:
    """Celery task running the evergreen recycler."""
    logger.info("Starting Celery evergreen recycling for profile ID: %s", profile_id)
    return asyncio.run(_run_evergreen_recycling_async(profile_id))


async def _run_persona_reflection_async(profile_id_str: str) -> dict[str, Any]:
    try:
        profile_id = uuid.UUID(profile_id_str)
    except ValueError:
        return {"status": "failed", "error": "Invalid profile ID format."}
        
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        from xbot.ai.reflection import ReflectionEngine
        try:
            learned_state = await ReflectionEngine().reflect_and_update(db, profile.profile_slug)
            return {"status": "success", "reflection_count": learned_state.reflection_count}
        except Exception as ex:
            logger.error("Persona reflection task failed for '%s': %s", profile.profile_slug, ex)
            return {"status": "failed", "error": str(ex)}


def run_persona_reflection(profile_id: str) -> dict[str, Any]:
    """Celery task running the auto-learning persona reflection engine."""
    logger.info("Starting Celery persona reflection for profile ID: %s", profile_id)
    return asyncio.run(_run_persona_reflection_async(profile_id))
