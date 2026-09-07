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

async def _sync_all_profiles_creator_studio_async() -> dict[str, Any]:
    """
    Periodic task (every 12 hours):
    Visits https://x.com/i/jf/creators/studio in 1 gentle single browser visit per profile,
    extracts official verified followers and 90-day verified home timeline impressions,
    and saves an AnalyticsSnapshot.
    """
    from datetime import date, datetime
    from xbot.models.analytics import AnalyticsSnapshot
    from xbot.browser.actions.x_actions import ScrapeCreatorStudioMetrics

    logger.info("Starting 12-hour Creator Studio official metric sync...")
    results = []
    manager = BrowserManager()

    try:
        await manager.start()
        async with AsyncSessionLocal() as db:
            p_res = await db.execute(select(Profile))
            profiles = p_res.scalars().all()

            for prof in profiles:
                if not manager.acquire_lock(prof.profile_slug, timeout_seconds=15):
                    logger.info("Skipping sync for %s; browser lock busy.", prof.profile_slug)
                    continue

                context = None
                try:
                    context = await manager.get_context(prof.profile_slug)
                    page = await context.new_page()

                    studio_action = ScrapeCreatorStudioMetrics()
                    data = await studio_action.execute(page)

                    if data.get("status") == "success":
                        vf = data.get("verified_followers", 0)
                        imp = data.get("verified_impressions_90d", 0)

                        snapshot = AnalyticsSnapshot(
                            profile_id=prof.id,
                            snapshot_date=date.today(),
                            verified_followers=vf,
                            verified_impressions_90d=imp,
                            captured_at=datetime.utcnow(),
                        )
                        db.add(snapshot)
                        await db.commit()
                        logger.info("Successfully updated Creator Studio metrics for %s: %d verified followers, %d 90d impressions", prof.x_handle, vf, imp)
                        results.append({"handle": prof.x_handle, "verified_followers": vf, "verified_impressions_90d": imp})
                except Exception as ex:
                    logger.warning("Error syncing Creator Studio for %s: %s", prof.x_handle, ex)
                finally:
                    if context:
                        await context.close()
                    manager.release_lock(prof.profile_slug)

        return {"status": "success", "synced_profiles": results}
    except Exception as e:
        logger.error("Failed 12-hour Creator Studio sync: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        await manager.stop()


@celery_app.task(name="xbot.tasks.sync_all_profiles_creator_studio")
def sync_all_profiles_creator_studio() -> dict[str, Any]:
    """Celery periodic task syncing official Creator Studio metrics every 12 hours."""
    return asyncio.run(_sync_all_profiles_creator_studio_async())
