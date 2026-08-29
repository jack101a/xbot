from __future__ import annotations
import datetime
import logging
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import xbot.api.profiles as profiles_api
from xbot.database import get_db
from xbot.models.profile import Profile
from xbot.models.analytics import AnalyticsSnapshot
from xbot.browser.manager import BrowserManager
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from .crud import _populate_profile_metrics
from .constants import BASE_PROFILE_DIR

logger = logging.getLogger("xbot.api.profiles")
router = APIRouter()

@router.post("/{profile_id}/sync-from-x", response_model=dict[str, Any])
async def sync_profile_from_x_endpoint(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Launches headless browser session to sync follower/following counts, avatar,
    display name, and verify live auth state from X.com.
    """
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    BM = getattr(profiles_api, "BrowserManager", BrowserManager)
    manager = BM(base_profile_dir=str(profiles_api.BASE_PROFILE_DIR))
    if not manager.acquire_lock(db_profile.profile_slug, timeout_seconds=120):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Profile {db_profile.profile_slug} is currently locked or in use.",
        )

    context = None
    try:
        await manager.start()
        context = await manager.get_context(profile_slug=db_profile.profile_slug)
        page = await context.new_page()
        SyncAction = getattr(profiles_api, "SyncProfileFromX", SyncProfileFromX)
        sync_action = SyncAction()
        sync_data = await sync_action.execute(page, db_profile.x_handle)
    except Exception as e:
        logger.error("Error during sync from X for profile %s: %s", db_profile.profile_slug, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync profile from X: {str(e)}",
        )
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        manager.release_lock(db_profile.profile_slug)
        await manager.stop()

    if sync_data.get("avatar_url"):
        db_profile.avatar_url = sync_data["avatar_url"]
    if sync_data.get("display_name"):
        db_profile.display_name = sync_data["display_name"]

    followers = sync_data.get("followers_count", 0)
    following = sync_data.get("following_count", 0)
    posts = sync_data.get("posts_count", 0)
    impressions = sync_data.get("impressions_24h", 0)
    engagements = sync_data.get("engagements_24h", 0)
    eng_rate = sync_data.get("engagement_rate", 0.0)

    from datetime import date, datetime
    today = date.today()
    snap_stmt = select(AnalyticsSnapshot).where(
        AnalyticsSnapshot.profile_id == db_profile.id,
        AnalyticsSnapshot.snapshot_date == today,
    )
    snap_res = await db.execute(snap_stmt)
    snap = snap_res.scalar_one_or_none()

    recent_tw = sync_data.get("recent_tweets", [])
    top_tw_payload = {
        "likes_count": sum(int(t.get("likes") or 0) for t in recent_tw),
        "retweets_count": sum(int(t.get("retweets") or 0) for t in recent_tw),
        "replies_count": sum(int(t.get("replies") or 0) for t in recent_tw),
        "recent_tweets": recent_tw,
    }

    if not snap:
        snap = AnalyticsSnapshot(
            profile_id=db_profile.id,
            snapshot_date=today,
            followers=followers if followers > 0 else getattr(db_profile, "followers_count", 0),
            following=following if following > 0 else getattr(db_profile, "following_count", 0),
            total_tweets=posts if posts > 0 else getattr(db_profile, "posts_count", 0),
            impressions_24h=impressions,
            engagements_24h=engagements,
            engagement_rate=eng_rate,
            top_tweets=top_tw_payload,
            captured_at=datetime.utcnow(),
        )
        db.add(snap)
    else:
        if followers > 0:
            snap.followers = followers
        if following > 0:
            snap.following = following
        if posts > 0:
            snap.total_tweets = posts
        snap.impressions_24h = impressions
        snap.engagements_24h = engagements
        snap.engagement_rate = eng_rate
        if recent_tw:
            snap.top_tweets = top_tw_payload
        snap.captured_at = datetime.utcnow()

    await db.commit()
    await db.refresh(db_profile)
    await _populate_profile_metrics(db, db_profile)

    return {
        "status": "success",
        "message": f"Profile {db_profile.profile_slug} synced successfully.",
        "profile": {
            "id": str(db_profile.id),
            "profile_slug": db_profile.profile_slug,
            "x_handle": db_profile.x_handle,
            "display_name": db_profile.display_name,
            "avatar_url": db_profile.avatar_url,
            "followers_count": followers if followers > 0 else getattr(db_profile, "followers_count", 0),
            "following_count": following if following > 0 else getattr(db_profile, "following_count", 0),
            "posts_count": posts if posts > 0 else getattr(db_profile, "posts_count", 0),
        },
        "sync_data": sync_data,
    }
