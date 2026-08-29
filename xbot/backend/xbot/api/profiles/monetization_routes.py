from __future__ import annotations

from pathlib import Path
from typing import Any
import asyncio
import datetime
import json
import logging
import uuid

import xbot.api.profiles as profiles_api

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.database import get_db
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus
from xbot.models.analytics import AnalyticsSnapshot, FollowerSnapshot, FollowerChangeLog
from xbot.models.session import Action, ActionStatus, ActionType, Session
from xbot.browser.manager import BrowserManager
from xbot.browser.actions.sync_profile_action import SyncProfileAction


logger = logging.getLogger('xbot.api.profiles')
router = APIRouter()

@router.get("/{profile_id}/monetization", response_model=dict[str, Any])
async def get_profile_monetization_status(
    profile_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Gets calculated progress toward X's monetization thresholds."""
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    db_profile = result.scalar_one_or_none()
    if db_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    # 1. Fetch latest snapshot
    stmt_snap = (
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.profile_id == profile_id)
        .order_by(AnalyticsSnapshot.captured_at.desc())
        .limit(1)
    )
    res_snap = await db.execute(stmt_snap)
    snap = res_snap.scalar_one_or_none()
    current_followers = snap.followers if snap else 0

    # 2. Get past 30 days snapshots for projections
    thirty_days_ago = datetime.date.today() - datetime.timedelta(days=30)
    stmt_snaps_30d = (
        select(AnalyticsSnapshot)
        .where(
            AnalyticsSnapshot.profile_id == profile_id,
            AnalyticsSnapshot.snapshot_date >= thirty_days_ago,
        )
        .order_by(AnalyticsSnapshot.snapshot_date.asc())
    )
    res_snaps_30d = await db.execute(stmt_snaps_30d)
    snaps_30d = res_snaps_30d.scalars().all()

    # Estimate 3-month impressions
    # Sum impressions over 30 days or extrapolate
    total_impressions_30d = sum(s.impressions_24h for s in snaps_30d)
    if len(snaps_30d) > 0:
        avg_daily_impressions = total_impressions_30d / len(snaps_30d)
        impressions_3mo = round(avg_daily_impressions * 90)
    else:
        impressions_3mo = snap.impressions_24h * 90 if snap else 0

    # Calculate growth rate
    growth_rate_per_day = 1.0  # default minimum
    if len(snaps_30d) >= 2:
        earliest_followers = snaps_30d[0].followers
        latest_followers = snaps_30d[-1].followers
        delta_days = (snaps_30d[-1].snapshot_date - snaps_30d[0].snapshot_date).days
        if delta_days > 0:
            growth_rate_per_day = max(
                0.1, (latest_followers - earliest_followers) / delta_days
            )

    # Project eligibility date
    days_until_eligible = max(0, (500 - current_followers) / growth_rate_per_day)
    projected_date = datetime.date.today() + datetime.timedelta(
        days=round(days_until_eligible)
    )

    # Pct calculations
    pct_followers_ads = min(100, round((current_followers / 500) * 100))
    pct_impressions_ads = min(100, round((impressions_3mo / 5000000) * 100))
    pct_followers_subs = min(100, round((current_followers / 2000) * 100))

    # Read active flags from profile config if available
    profile_dir = Path(profiles_api.BASE_PROFILE_DIR) / db_profile.profile_slug
    stripe_active = False
    premium_active = False
    if profile_dir.exists():
        try:
            config = load_config(profile_dir)
            premium_active = bool(config.credentials and config.credentials.password_encrypted)
        except Exception:
            pass

    return {
        "x_premium_active": premium_active,
        "stripe_connected": stripe_active,
        "ads_revenue_sharing": {
            "eligible": current_followers >= 500 and impressions_3mo >= 5000000,
            "progress": {
                "followers": {
                    "current": current_followers,
                    "required": 500,
                    "pct": pct_followers_ads,
                },
                "impressions_3mo": {
                    "current": impressions_3mo,
                    "required": 5000000,
                    "pct": pct_impressions_ads,
                },
            },
            "estimated_eligibility_date": projected_date.isoformat(),
        },
        "creator_subscriptions": {
            "eligible": current_followers >= 2000 and impressions_3mo >= 5000000,
            "progress": {
                "followers": {
                    "current": current_followers,
                    "required": 2000,
                    "pct": pct_followers_subs,
                },
                "impressions_3mo": {
                    "current": impressions_3mo,
                    "required": 5000000,
                    "pct": pct_impressions_ads,
                },
            },
        },
    }

