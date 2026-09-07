from .constants import *
import asyncio
import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from ruamel.yaml import YAML
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.auth import (
    format_storage_state,
    inspect_profile_auth_status,
    parse_cookie_string,
)
from xbot.browser.manager import BrowserManager
from xbot.database import get_db
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import (
    DiaryManager,
    MemoryManager,
    load_config,
    save_config,
    Config,
    LimitsConfig,
    ScheduleConfig,
    load_persona,
    load_relationships,
    load_strategy,
    save_strategy,
    load_learned_state,
    save_learned_state,
    LearnedState,
)
from pydantic import BaseModel, Field
from xbot.persona.card_parser import load_raw_card, map_card_to_persona
from xbot.schemas.profile import ProfileCreate, ProfileResponse, ProfileUpdate

from fastapi import APIRouter
router = APIRouter()

async def _populate_profile_metrics(db: AsyncSession, p: Profile) -> Profile:
    from xbot.models.content import Content, ContentStatus
    from sqlalchemy import func

    stmt_snap = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == p.id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    snap = res_snap.scalar_one_or_none()
    p.followers_count = snap.followers if snap else 0
    p.following_count = snap.following if snap else 0
    p.posts_count = snap.total_tweets if (snap and snap.total_tweets > 0) else 0
    
    # Fallback to direct Content table count if snapshot not yet recorded
    if not p.posts_count:
        cnt_stmt = select(func.count(Content.id)).where(Content.profile_id == p.id, Content.status == ContentStatus.POSTED)
        cnt_res = await db.execute(cnt_stmt)
        p.posts_count = cnt_res.scalar() or 0

    p.impressions_24h = snap.impressions_24h if snap else 0
    p.engagements_24h = snap.engagements_24h if snap else 0
    p.engagement_rate = snap.engagement_rate if snap else 0.0
    p.likes_count = (snap.top_tweets or {}).get("likes_count", 0) if snap else 0
    p.retweets_count = (snap.top_tweets or {}).get("retweets_count", 0) if snap else 0
    p.recent_tweets = (snap.top_tweets or {}).get("recent_tweets", []) if snap else []
    return p

@router.get("/{profile_id}/analytics", response_model=list[dict[str, Any]])
async def get_profile_analytics_snapshots(
    profile_id: uuid.UUID,
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Gets analytics snapshots history for a profile."""
    stmt = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    snaps = result.scalars().all()

    return [
        {
            "id": s.id,
            "profile_id": s.profile_id,
            "snapshot_date": s.snapshot_date,
            "followers": s.followers,
            "following": s.following,
            "total_tweets": s.total_tweets,
            "impressions_24h": s.impressions_24h,
            "engagements_24h": s.engagements_24h,
            "engagement_rate": s.engagement_rate,
            "top_tweets": s.top_tweets,
            "captured_at": s.captured_at,
        }
        for s in snaps
    ]

@router.post("/{profile_id}/sync-analytics", response_model=dict[str, Any])
async def sync_live_analytics(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Triggers an instant live sync of official Creator Studio metrics and profile metrics via Playwright.
    """
    from datetime import date, datetime
    from xbot.models.analytics import AnalyticsSnapshot
    from xbot.browser.manager import BrowserManager
    from xbot.browser.actions.x_actions import ScrapeCreatorStudioMetrics, ScrapeProfileTweets

    prof_res = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = prof_res.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    manager = BrowserManager(base_profile_dir=BASE_PROFILE_DIR)
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=30):
        raise HTTPException(status_code=423, detail="Profile browser lock is busy. Please retry.")

    context = None
    try:
        await manager.start()
        context = await manager.get_context(db_profile.profile_slug)
        page = await context.new_page()

        # 1. Scrape Creator Studio official numbers
        studio_action = ScrapeCreatorStudioMetrics()
        studio_res = await studio_action.execute(page)

        verified_followers = int(studio_res.get("verified_followers") or 0)
        verified_imp_90d = int(studio_res.get("verified_impressions_90d") or 0)

        # 2. Scrape Profile stats and live tweets
        prof_action = ScrapeProfileTweets()
        prof_stats = await prof_action.execute(page, db_profile.x_handle.lstrip("@"), limit=15)

        followers = int(prof_stats.get("followers") or 0)
        following = int(prof_stats.get("following") or 0)
        scraped_tweets = prof_stats.get("tweets", [])

        # Calculate totals from live scraped tweets
        total_impressions = sum(int(t.get("views") or 0) for t in scraped_tweets)
        total_engagements = sum(int(t.get("engagement_score") or 0) for t in scraped_tweets)
        total_likes = sum(int(t.get("likes") or 0) for t in scraped_tweets)
        total_retweets = sum(int(t.get("retweets") or 0) for t in scraped_tweets)
        total_replies = sum(int(t.get("replies") or 0) for t in scraped_tweets)
        total_tweets_count = len(scraped_tweets)
        eng_rate = round((total_engagements / total_impressions * 100), 2) if total_impressions > 0 else 0.0

        # 3. Store snapshot
        snapshot = AnalyticsSnapshot(
            profile_id=profile_id,
            snapshot_date=date.today(),
            followers=followers if followers > 0 else getattr(db_profile, "followers_count", 0),
            following=following if following > 0 else getattr(db_profile, "following_count", 0),
            total_tweets=total_tweets_count if total_tweets_count > 0 else getattr(db_profile, "posts_count", 0),
            impressions_24h=total_impressions,
            engagements_24h=total_engagements,
            engagement_rate=eng_rate,
            verified_followers=verified_followers,
            verified_impressions_90d=verified_imp_90d,
            top_tweets={
                "likes_count": total_likes,
                "retweets_count": total_retweets,
                "replies_count": total_replies,
                "recent_tweets": scraped_tweets,
            },
            captured_at=datetime.utcnow(),
        )
        db.add(snapshot)
        await db.commit()

        return {
            "status": "success",
            "message": "Live analytics and Creator Studio metrics synced successfully!",
            "verified_followers": verified_followers,
            "verified_impressions_90d": verified_imp_90d,
            "followers": followers,
            "following": following,
            "total_posts": total_tweets_count,
            "total_impressions": total_impressions,
            "total_engagements": total_engagements,
            "engagement_rate": eng_rate,
            "synced_at": datetime.utcnow().isoformat(),
        }
    except Exception as ex:
        logger.error("Error during live analytics sync: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex))
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



from .monetization_routes import router as monetization_router, get_profile_monetization_status
router.include_router(monetization_router)

from .deep_analytics_routes import router as deep_router, get_deep_analytics
router.include_router(deep_router)
