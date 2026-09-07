from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any

import redis

from xbot.config import settings

logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    """
    Implements Phase 3.2 Redis-based Sliding Window Rate Limiter.
    Utilizes Redis sorted sets (ZADD, ZCOUNT, ZREMRANGEBYSCORE) for hourly and daily action caps.
    Manages cooldown timestamps with auto-expiry keys.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.REDIS_URL
        self.r = redis.from_url(url)

    def _get_keys(self, profile_slug: str, action_type: str) -> tuple[str, str, str]:
        hourly_key = f"rate:{profile_slug}:{action_type}:hourly"
        daily_key = f"rate:{profile_slug}:{action_type}:daily"
        cooldown_key = f"cooldown:{profile_slug}:{action_type}"
        return hourly_key, daily_key, cooldown_key

    def record_action(
        self,
        profile_slug: str,
        action_type: str,
        now_utc: datetime.datetime | None = None,
    ) -> None:
        """Records a new execution event in Redis sorted sets and updates TTL."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        now_ts = now_utc.timestamp()
        hourly_key, daily_key, _ = self._get_keys(profile_slug, action_type)

        # Unique member to avoid timestamp collisions
        member = f"{now_ts}:{uuid.uuid4()}"

        # 1. Add to hourly set
        self.r.zadd(hourly_key, {member: now_ts})
        self.r.expire(hourly_key, 3600)  # 1 hour expiration

        # 2. Add to daily set
        self.r.zadd(daily_key, {member: now_ts})
        self.r.expire(daily_key, 86400)  # 24 hours expiration

        # 3. Clean up expired scores in both sets
        self.r.zremrangebyscore(hourly_key, "-inf", now_ts - 3600)
        self.r.zremrangebyscore(daily_key, "-inf", now_ts - 86400)

        logger.info("Recorded action '%s' for profile %s in Redis limiter.", action_type, profile_slug)

    def is_rate_limited(
        self,
        profile_slug: str,
        action_type: str,
        limit_hourly: int,
        limit_daily: int,
        now_utc: datetime.datetime | None = None,
    ) -> bool:
        """
        Evaluates hourly and daily rates.
        Returns True if limit exceeded in either window, False otherwise.
        """
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        now_ts = now_utc.timestamp()
        hourly_key, daily_key, _ = self._get_keys(profile_slug, action_type)

        # 1. Clean up expired entries
        self.r.zremrangebyscore(hourly_key, "-inf", now_ts - 3600)
        self.r.zremrangebyscore(daily_key, "-inf", now_ts - 86400)

        # 2. Query sizes of the sets
        hourly_count = self.r.zcard(hourly_key) or 0
        daily_count = self.r.zcard(daily_key) or 0

        logger.debug(
            "Limiter check for slug %s action %s: Hourly %d/%d, Daily %d/%d",
            profile_slug,
            action_type,
            hourly_count,
            limit_hourly,
            daily_count,
            limit_daily,
        )

        if hourly_count >= limit_hourly:
            logger.warning("Profile %s is rate limited for %s: Hourly cap reached (%d >= %d)", profile_slug, action_type, hourly_count, limit_hourly)
            return True

        if daily_count >= limit_daily:
            logger.warning("Profile %s is rate limited for %s: Daily cap reached (%d >= %d)", profile_slug, action_type, daily_count, limit_daily)
            return True

        return False

    def set_cooldown(
        self,
        profile_slug: str,
        action_type: str,
        cooldown_seconds: int,
        now_utc: datetime.datetime | None = None,
    ) -> None:
        """Enforces a strict cooling period for this action type."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        _, _, cooldown_key = self._get_keys(profile_slug, action_type)
        expiry_ts = now_utc.timestamp() + cooldown_seconds

        self.r.set(cooldown_key, str(expiry_ts), ex=cooldown_seconds)
        logger.info("Enforced %ds cooldown on action '%s' for profile %s.", cooldown_seconds, action_type, profile_slug)

    def is_cooldown_active(
        self,
        profile_slug: str,
        action_type: str,
        now_utc: datetime.datetime | None = None,
    ) -> bool:
        """Checks if a cooldown key exists in Redis and has not yet expired."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        _, _, cooldown_key = self._get_keys(profile_slug, action_type)
        val = self.r.get(cooldown_key)

        if val is None:
            return False

        try:
            expiry_ts = float(val.decode("utf-8") if isinstance(val, bytes) else val)
            if expiry_ts > now_utc.timestamp():
                return True
        except Exception:
            pass

        return False
