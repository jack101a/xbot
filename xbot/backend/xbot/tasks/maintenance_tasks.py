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

from .common import _parse_x_counts

async def _collect_analytics_snapshot_async(profile_id_str: str) -> dict[str, Any]:
    profile_id = uuid.UUID(profile_id_str)
    
    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.id == profile_id)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found."}
            
        profile_slug = profile.profile_slug
        
        manager = BrowserManager()
        await manager.start()
        
        if not manager.acquire_lock(profile_slug):
            await manager.stop()
            return {"status": "failed", "error": "Redis browser lock collision."}
            
        context = None
        try:
            config = load_config(manager.base_profile_dir / profile_slug)
            is_mock = getattr(config, "mock_mode", False)
            followers_val = 0
            following_val = 0
            
            if is_mock:
                followers_val = profile.followers_count or 0
                following_val = profile.following_count or 0
                logger.info("🧪 [MOCK / DEMO MODE] Using existing actual counts for simulated analytics snapshot.")
            else:
                timezone_str = config.schedule.timezone or "America/New_York"
                
                context = await manager.get_context(
                    profile_slug=profile_slug,
                    timezone=timezone_str,
                    proxy_url=config.proxy_url,
                )
                page = await context.new_page()
                
                # Scrape Profile stats & live tweets
                prof_action = ScrapeProfileTweets()
                prof_stats = await prof_action.execute(page, profile.x_handle.lstrip("@"), limit=15)
                followers_val = prof_stats.get("followers") or profile.followers_count or 0
                following_val = prof_stats.get("following") or profile.following_count or 0
                scraped_tweets = prof_stats.get("tweets", [])

                # Scrape Creator Studio
                studio_action = ScrapeCreatorStudioMetrics()
                studio_res = await studio_action.execute(page)
                verified_followers_val = int(studio_res.get("verified_followers") or 0)
                verified_imp_90d_val = int(studio_res.get("verified_impressions_90d") or 0)

            total_impressions_val = sum(int(t.get("views") or 0) for t in scraped_tweets) if not is_mock else 0
            total_engagements_val = sum(int(t.get("engagement_score") or 0) for t in scraped_tweets) if not is_mock else 0
            total_likes_val = sum(int(t.get("likes") or 0) for t in scraped_tweets) if not is_mock else 0
            total_retweets_val = sum(int(t.get("retweets") or 0) for t in scraped_tweets) if not is_mock else 0
            total_replies_val = sum(int(t.get("replies") or 0) for t in scraped_tweets) if not is_mock else 0
            total_tweets_val = len(scraped_tweets) if scraped_tweets else (profile.posts_count or 0)
            eng_rate = round((total_engagements_val / total_impressions_val * 100), 2) if total_impressions_val > 0 else 0.0

            # Update Profile columns
            if followers_val > 0:
                profile.followers_count = followers_val
            if following_val > 0:
                profile.following_count = following_val
            if total_tweets_val > 0:
                profile.posts_count = total_tweets_val
            profile.impressions_24h = total_impressions_val
            profile.engagements_24h = total_engagements_val
            profile.engagement_rate = eng_rate

            # Store Analytics Snapshot with real data
            snapshot = AnalyticsSnapshot(
                profile_id=profile_id,
                snapshot_date=datetime.date.today(),
                followers=followers_val,
                following=following_val,
                total_tweets=total_tweets_val,
                impressions_24h=total_impressions_val,
                engagements_24h=total_engagements_val,
                engagement_rate=eng_rate,
                verified_followers=verified_followers_val if not is_mock else 0,
                verified_impressions_90d=verified_imp_90d_val if not is_mock else 0,
                top_tweets={
                    "likes_count": total_likes_val,
                    "retweets_count": total_retweets_val,
                    "replies_count": total_replies_val,
                    "recent_tweets": scraped_tweets if not is_mock else [],
                },
                captured_at=datetime.datetime.utcnow(),
            )
            db.add(snapshot)
            await db.commit()
            
            return {
                "status": "success",
                "profile_slug": profile_slug,
                "followers": followers_val,
                "following": following_val,
                "verified_followers": verified_followers_val if not is_mock else 0,
                "verified_impressions_90d": verified_imp_90d_val if not is_mock else 0,
            }
            
        except Exception as ex:
            return {"status": "failed", "error": str(ex)}
            
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)
            await manager.stop()


def collect_analytics_snapshot(profile_id: str) -> dict[str, Any]:
    """Celery task running daily analytics scrapes and storing snapshots."""
    logger.info("Starting Celery analytics snapshot collection for profile ID: %s", profile_id)
    return asyncio.run(_collect_analytics_snapshot_async(profile_id))
