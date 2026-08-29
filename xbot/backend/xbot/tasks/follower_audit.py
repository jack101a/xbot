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

async def _run_follower_audit_async(profile_id_str: str) -> dict[str, Any]:
    from xbot.models.analytics import FollowerSnapshot, FollowerChangeLog
    try:
        profile_id = uuid.UUID(profile_id_str)
    except ValueError:
        return {"status": "failed", "error": "Invalid profile ID format."}
        
    async with AsyncSessionLocal() as db:
        # Load profile
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()
        if not profile:
            return {"status": "failed", "error": "Profile not found"}
        
        profile_slug = profile.profile_slug
        x_handle = profile.x_handle
        
        # Check lock
        manager = BrowserManager()
        if not manager.acquire_lock(profile_slug, timeout_seconds=1200):
            return {"status": "failed", "error": "Profile lock active"}
            
        context = None
        try:
            # 1. Scrape followers & following lists
            context = await manager.get_context(profile_slug=profile_slug)
            page = await context.new_page()
            
            # Scrape current followers
            current_followers = await ScrapeFollowList().execute(page, username=x_handle, list_type="followers", limit=100)
            # Scrape current following
            current_following = await ScrapeFollowList().execute(page, username=x_handle, list_type="following", limit=100)
            
            # Close browser context to free memory
            await context.close()
            context = None
            
            # 2. Load last snapshots from DB
            last_followers_stmt = (
                select(FollowerSnapshot)
                .where(FollowerSnapshot.profile_id == profile_id, FollowerSnapshot.snapshot_type == "follower")
                .order_by(FollowerSnapshot.captured_at.desc())
                .limit(1)
            )
            res = await db.execute(last_followers_stmt)
            last_followers_snap = res.scalar_one_or_none()
            
            last_following_stmt = (
                select(FollowerSnapshot)
                .where(FollowerSnapshot.profile_id == profile_id, FollowerSnapshot.snapshot_type == "following")
                .order_by(FollowerSnapshot.captured_at.desc())
                .limit(1)
            )
            res = await db.execute(last_following_stmt)
            last_following_snap = res.scalar_one_or_none()
            
            # 3. Diff followers list
            new_changelogs = []
            if last_followers_snap:
                old_followers_set = set(last_followers_snap.handles)
                new_followers_set = set(current_followers)
                
                # People who unfollowed us
                unfollowers = old_followers_set - new_followers_set
                for u in unfollowers:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="unfollowed_us",
                            handle=u
                        )
                    )
                
                # New followers: record log and queue for immediate reciprocal follow-back
                new_followers = new_followers_set - old_followers_set
                from xbot.models.follow_growth import FollowCandidate
                for f in new_followers:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="new_follower",
                            handle=f
                        )
                    )
                    clean_f = f.lstrip("@")
                    if clean_f not in current_following:
                        chk_c = await db.execute(
                            select(FollowCandidate).where(
                                FollowCandidate.profile_id == profile_id,
                                FollowCandidate.handle == clean_f,
                            )
                        )
                        if not chk_c.scalar_one_or_none():
                            db.add(
                                FollowCandidate(
                                    profile_id=profile_id,
                                    handle=clean_f,
                                    display_name=clean_f,
                                    niche="incoming_follower",
                                    is_blue_tick=True,
                                    reciprocity_score=100.0,
                                    status="queued",
                                )
                            )
            
            # 4. Diff following list
            if last_following_snap:
                old_following_set = set(last_following_snap.handles)
                new_following_set = set(current_following)
                
                # People we unfollowed
                we_unfollowed = old_following_set - new_following_set
                for u in we_unfollowed:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="we_unfollowed",
                            handle=u
                        )
                    )
                
                # New people we followed
                we_followed = new_following_set - old_following_set
                for f in we_followed:
                    new_changelogs.append(
                        FollowerChangeLog(
                            profile_id=profile_id,
                            change_type="we_followed",
                            handle=f
                        )
                    )
            
            # 5. Save logs and snapshots
            for log in new_changelogs:
                db.add(log)
                
            # Create new snapshots
            db.add(FollowerSnapshot(profile_id=profile_id, snapshot_type="follower", handles=current_followers))
            db.add(FollowerSnapshot(profile_id=profile_id, snapshot_type="following", handles=current_following))
            
            await db.commit()
            
            return {
                "status": "success",
                "followers_count": len(current_followers),
                "following_count": len(current_following),
                "changelogs_recorded": len(new_changelogs)
            }
            
        except Exception as e:
            logger.error("Error in follower audit: %s", e)
            return {"status": "failed", "error": str(e)}
        finally:
            if context:
                await context.close()
            manager.release_lock(profile_slug)
