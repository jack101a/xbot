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
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus
from xbot.models.analytics import FollowerChangeLog
from xbot.models.session import Action, Session
from xbot.persona.loader import load_persona
from xbot.browser.manager import BrowserManager

logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()
@router.get("/{profile_id}/deep-analytics", response_model=dict[str, Any])
async def get_deep_analytics(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns full deep analytics:
    - Official Creator Studio Milestones (500 Verified Followers & 500K 90d Verified Impressions)
    - 28-Day Rolling Impressions & Engagement Rate
    - Top Performing Posts Ranking
    - Historical Snapshots
    """
    from datetime import datetime, timedelta
    from xbot.models.content import Content, ContentStatus
    from xbot.models.analytics import AnalyticsSnapshot

    prof_res = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = prof_res.scalar_one_or_none()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Fetch latest analytics snapshot
    snap_res = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    latest_snap = snap_res.scalar_one_or_none()

    verified_followers = latest_snap.verified_followers if latest_snap else 0
    verified_imp_90d = latest_snap.verified_impressions_90d if latest_snap else 0

    # 28-day window aggregation
    cutoff_28d = datetime.utcnow() - timedelta(days=28)
    content_res = await db.execute(
        select(Content)
        .where(Content.profile_id == profile_id)
        .where(Content.status == ContentStatus.POSTED)
        .where(Content.created_at >= cutoff_28d)
        .order_by(Content.created_at.desc())
    )
    posts_28d = content_res.scalars().all()

    total_posts = latest_snap.total_tweets if (latest_snap and latest_snap.total_tweets > 0) else (getattr(db_profile, "posts_count", 0) or len(posts_28d))
    total_impressions_28d = latest_snap.impressions_24h if latest_snap else 0
    total_engagements_28d = latest_snap.engagements_24h if latest_snap else 0
    top_posts_list = []

    # 1. Add live scraped profile tweets if available in snapshot
    scraped_recent = (latest_snap.top_tweets or {}).get("recent_tweets", []) if latest_snap else []
    for idx, st in enumerate(scraped_recent):
        views = int(st.get("views") or 0)
        likes = int(st.get("likes") or 0)
        retweets = int(st.get("retweets") or 0)
        replies = int(st.get("replies") or 0)
        engagements = int(st.get("engagement_score") or (likes + retweets + replies))
        top_posts_list.append({
            "id": f"live_tweet_{idx}",
            "body": st.get("text", ""),
            "created_at": latest_snap.captured_at.isoformat() if latest_snap and latest_snap.captured_at else None,
            "views": views,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "engagements": engagements,
            "media_paths": [],
            "visual_spec": None,
            "gif_query": None,
        })

    # 2. Add DB Content records if not already in list
    for p in posts_28d:
        meta = p.ai_metadata or {}
        views = int(meta.get("views_count") or meta.get("views") or meta.get("impressions") or 0)
        likes = int(meta.get("likes_count") or meta.get("likes") or 0)
        retweets = int(meta.get("retweets_count") or meta.get("retweets") or 0)
        replies = int(meta.get("replies_count") or meta.get("replies") or 0)
        engagements = likes + retweets + replies

        if not any(t["body"] == p.body for t in top_posts_list):
            top_posts_list.append({
                "id": str(p.id),
                "body": p.body,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "views": views,
                "likes": likes,
                "retweets": retweets,
                "replies": replies,
                "engagements": engagements,
                "media_paths": meta.get("media_paths", []),
                "visual_spec": meta.get("visual_spec"),
                "gif_query": meta.get("gif_query"),
            })

    # Calculate overall impressions and engagements across top posts if snapshot totals were 0
    if total_impressions_28d == 0 and top_posts_list:
        total_impressions_28d = sum(t["views"] for t in top_posts_list)
        total_engagements_28d = sum(t["engagements"] for t in top_posts_list)

    # Sort top posts by views / engagements
    top_posts_list.sort(key=lambda x: (x["views"], x["engagements"]), reverse=True)

    engagement_rate_28d = (
        round((total_engagements_28d / total_impressions_28d) * 100, 2)
        if total_impressions_28d > 0
        else (latest_snap.engagement_rate if latest_snap else 0.0)
    )

    # Fetch last 7 snapshots for sparklines
    hist_res = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(7)
    )
    history_snaps = hist_res.scalars().all()
    history_data = [
        {
            "date": s.snapshot_date.isoformat() if s.snapshot_date else s.captured_at.strftime("%Y-%m-%d"),
            "followers": s.followers,
            "verified_followers": s.verified_followers,
            "impressions": s.impressions_24h,
            "engagement_rate": s.engagement_rate,
        }
        for s in reversed(history_snaps)
    ]

    return {
        "status": "success",
        "profile_id": str(profile_id),
        "handle": db_profile.x_handle,
        "monetization_milestones": {
            "verified_followers": {
                "current": verified_followers,
                "target": 500,
                "percentage": round(min(100.0, (verified_followers / 500.0) * 100.0), 1),
                "remaining": max(0, 500 - verified_followers),
            },
            "verified_impressions_90d": {
                "current": verified_imp_90d,
                "target": 500000,
                "percentage": round(min(100.0, (verified_imp_90d / 500000.0) * 100.0), 2),
                "remaining": max(0, 500000 - verified_imp_90d),
            },
        },
        "rolling_28d": {
            "total_posts": total_posts,
            "total_impressions": total_impressions_28d,
            "total_engagements": total_engagements_28d,
            "engagement_rate": engagement_rate_28d,
        },
        "top_performing_posts": top_posts_list[:5],
        "history": history_data,
        "last_synced_at": latest_snap.captured_at.isoformat() if latest_snap else None,
    }

