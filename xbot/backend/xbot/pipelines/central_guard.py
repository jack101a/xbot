"""
Central Guard & Rate Limiter for XBot Pipelines.

Enforces:
1. Active Hours window (6:00 AM to 2:00 AM IST for live X interactions; 24/7 for research/generation).
2. Action deduplication (48-hour window on target IDs).
3. Underlying SafetyGuard rate limits & sliding window checks.
4. Daily action metrics tracking.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

import redis
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.safety.guard import SafetyGuard

logger = logging.getLogger(__name__)

# IST offset: UTC + 5:30
IST_OFFSET = datetime.timedelta(hours=5, minutes=30)


def get_current_ist_time(now_utc: datetime.datetime | None = None) -> datetime.datetime:
    """Returns current time in Indian Standard Time (IST)."""
    if now_utc is None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=datetime.timezone.utc)
    return now_utc.astimezone(datetime.timezone(IST_OFFSET))


def is_within_active_hours(
    now_utc: datetime.datetime | None = None,
    start_hour: int = 6,
    end_hour: int = 2,
) -> bool:
    """
    Checks if current time is within active operational hours (in IST).
    Default: 6:00 AM IST to 2:00 AM IST next day (sleep window is 2:00 AM to 6:00 AM IST).
    """
    ist = get_current_ist_time(now_utc)
    current_hour = ist.hour
    
    # If end_hour < start_hour, active window wraps around midnight (e.g. 6am to 2am)
    if start_hour > end_hour:
        # Active if hour >= 6 OR hour < 2
        return current_hour >= start_hour or current_hour < end_hour
    else:
        return start_hour <= current_hour < end_hour


class CentralGuard:
    """
    Unified gatekeeper for all independent pipelines.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        safety_guard: SafetyGuard | None = None,
    ) -> None:
        self.redis_url = redis_url or settings.REDIS_URL
        self.r = redis.from_url(self.redis_url, decode_responses=True)
        self.safety_guard = safety_guard or SafetyGuard(redis_url=self.redis_url)

    def is_action_24_7(self, action_type: str) -> bool:
        """Returns True if action is allowed to run 24/7 without active hours restrictions."""
        return action_type in (
            "trend_researcher",
            "trend_generator",
            "research",
            "generate",
            "status",
        )

    def is_target_acted_upon(self, profile_slug: str, action_type: str, target_id: str) -> bool:
        """Checks if a target has been acted upon within the 48-hour deduplication window."""
        if not target_id:
            return False
        try:
            key = f"xbot:action_done:{profile_slug}:{action_type}:{target_id}"
            return bool(self.r.exists(key))
        except Exception as e:
            logger.warning("Redis dedup check error for target %s: %s", target_id, e)
            return False

    def mark_target_acted(
        self,
        profile_slug: str,
        action_type: str,
        target_id: str,
        ttl_seconds: int = 172800,  # 48 hours
    ) -> None:
        """Records target action in Redis with 48h TTL."""
        if not target_id:
            return
        try:
            key = f"xbot:action_done:{profile_slug}:{action_type}:{target_id}"
            self.r.set(key, "1", ex=ttl_seconds)
        except Exception as e:
            logger.warning("Failed to record target dedup in Redis: %s", e)

    async def can_act(
        self,
        db: AsyncSession,
        profile_slug: str,
        action_type: str,
        target_id: str | None = None,
        now_utc: datetime.datetime | None = None,
        bypass_active_hours: bool = False,
    ) -> bool:
        """
        Master decision check for any pipeline before attempting an action.
        Evaluates:
        1. Active hours (6am to 2am IST for live X interactions, 24/7 for research/generation)
        2. Deduplication check on target_id (48 hours)
        3. Underlying SafetyGuard limits & sliding window
        """
        # 1. Active hours check
        if not bypass_active_hours and not self.is_action_24_7(action_type):
            if not is_within_active_hours(now_utc):
                logger.info(
                    "CentralGuard: Action '%s' skipped outside active hours (6am-2am IST) for %s",
                    action_type,
                    profile_slug,
                )
                return False

        # 2. Target deduplication check
        if target_id and self.is_target_acted_upon(profile_slug, action_type, target_id):
            logger.info(
                "CentralGuard: Target '%s' already acted on with action '%s' for %s (48h dedup)",
                target_id,
                action_type,
                profile_slug,
            )
            return False

        # 3. SafetyGuard check
        # Map pipeline actions to SafetyGuard recognized actions
        sg_action_map = {
            "like": "like",
            "reply": "reply",
            "quote": "quote",
            "post": "post",
            "follow": "follow",
            "unfollow": "follow",  # Uses follow sliding window/limits
            "trend_researcher": "post",
            "trend_generator": "post",
        }
        mapped_action = sg_action_map.get(action_type, action_type)

        try:
            is_safe = await self.safety_guard.is_action_safe(
                db=db,
                profile_slug=profile_slug,
                action_type=mapped_action,
                now_utc=now_utc,
            )
            if not is_safe:
                logger.info(
                    "CentralGuard: SafetyGuard rejected action '%s' for %s",
                    action_type,
                    profile_slug,
                )
                return False
        except Exception as e:
            logger.error("CentralGuard: SafetyGuard error: %s", e)
            return False

        return True

    async def record_action(
        self,
        db: AsyncSession,
        profile_slug: str,
        action_type: str,
        target_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        now_utc: datetime.datetime | None = None,
    ) -> None:
        """
        Records action success across SafetyGuard, Redis dedup, and daily counters.
        """
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        # 1. Mark target dedup
        if target_id:
            self.mark_target_acted(profile_slug, action_type, target_id)

        # 2. Record daily counter in Redis
        try:
            today_str = get_current_ist_time(now_utc).strftime("%Y-%m-%d")
            counter_key = f"xbot:daily_stats:{profile_slug}:{today_str}:{action_type}"
            self.r.incr(counter_key)
            self.r.expire(counter_key, 86400 * 7)  # Retain for 7 days
        except Exception as e:
            logger.warning("CentralGuard: Failed to increment daily counter: %s", e)

        # 3. Record in SafetyGuard
        sg_action_map = {
            "like": "like",
            "reply": "reply",
            "quote": "quote",
            "post": "post",
            "follow": "follow",
            "unfollow": "follow",
        }
        mapped_action = sg_action_map.get(action_type, action_type)
        try:
            await self.safety_guard.record_action_success(
                profile_slug=profile_slug,
                action_type=mapped_action,
                now_utc=now_utc,
            )
        except Exception as e:
            logger.error("CentralGuard: Failed to record action success in SafetyGuard: %s", e)

    def get_daily_stats(self, profile_slug: str, date_str: str | None = None) -> dict[str, int]:
        """Returns action counts for the given profile and date (defaults to today in IST)."""
        if date_str is None:
            date_str = get_current_ist_time().strftime("%Y-%m-%d")

        stats = {
            "likes": 0,
            "replies": 0,
            "quotes": 0,
            "posts": 0,
            "follows": 0,
            "unfollows": 0,
        }

        action_to_key = {
            "like": "likes",
            "reply": "replies",
            "quote": "quotes",
            "post": "posts",
            "follow": "follows",
            "unfollow": "unfollows",
        }

        try:
            for action, stat_key in action_to_key.items():
                counter_key = f"xbot:daily_stats:{profile_slug}:{date_str}:{action}"
                val = self.r.get(counter_key)
                if val:
                    stats[stat_key] = int(val)
        except Exception as e:
            logger.warning("CentralGuard: Error fetching daily stats: %s", e)

        return stats

