"""
Drain lock manager for tracking X (Twitter) daily post limit exhaustion.
Prevents infinite retry loops, browser churn, and draft thrashing when
X restricts an account's daily publishing capacity.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any
import redis

logger = logging.getLogger(__name__)

DRAIN_KEY_PREFIX = "xbot:limits:daily_post_limit_drained:"


def get_drain_key(profile_slug: str) -> str:
    return f"{DRAIN_KEY_PREFIX}{profile_slug}"


def is_daily_post_limit_drained(redis_client: redis.Redis | None, profile_slug: str) -> bool:
    """Checks if an active daily post limit drain lock exists in Redis."""
    if redis_client is None:
        return False
    try:
        return bool(redis_client.exists(get_drain_key(profile_slug)))
    except Exception as e:
        logger.error("Failed to check daily post limit drain lock: %s", e)
        return False


def set_daily_post_limit_drained(
    redis_client: redis.Redis | None,
    profile_slug: str,
    reason: str = "Hit X daily post limit",
) -> int:
    """
    Sets the daily post limit drain lock for a profile.
    Calculates TTL until midnight UTC of the next day (minimum 6h, up to 24h).
    Returns the TTL in seconds.
    """
    if redis_client is None:
        return 0

    now_utc = datetime.datetime.utcnow()
    # Target 00:05 UTC next day for safety buffer
    next_day_utc = (now_utc + datetime.timedelta(days=1)).replace(
        hour=0, minute=5, second=0, microsecond=0
    )
    seconds_until_reset = int((next_day_utc - now_utc).total_seconds())
    # Ensure at least 6 hours (21600s) and at most 24 hours (86400s)
    ttl = max(21600, min(86400, seconds_until_reset))

    try:
        key = get_drain_key(profile_slug)
        redis_client.set(key, reason, ex=ttl)
        logger.critical(
            "X DAILY POST LIMIT DRAIN LOCK SET for profile '%s' (TTL: %ds / ~%.1f hours). Reason: %s",
            profile_slug,
            ttl,
            ttl / 3600.0,
            reason,
        )
        return ttl
    except Exception as e:
        logger.error("Failed to set daily post limit drain lock: %s", e)
        return 0


def get_daily_post_limit_status(
    redis_client: redis.Redis | None,
    profile_slug: str,
) -> dict[str, Any]:
    """Retrieves full status and remaining TTL for the daily post limit drain lock."""
    if redis_client is None:
        return {"drained": False, "reason": None, "resets_in_seconds": 0}

    key = get_drain_key(profile_slug)
    try:
        raw_reason = redis_client.get(key)
        if not raw_reason:
            return {"drained": False, "reason": None, "resets_in_seconds": 0}

        ttl = redis_client.ttl(key)
        reason_str = raw_reason.decode("utf-8") if isinstance(raw_reason, bytes) else str(raw_reason)
        return {
            "drained": True,
            "reason": reason_str,
            "resets_in_seconds": max(0, ttl),
        }
    except Exception as e:
        logger.error("Failed to get daily post limit status: %s", e)
        return {"drained": False, "reason": None, "resets_in_seconds": 0}


def clear_daily_post_limit_drained(
    redis_client: redis.Redis | None,
    profile_slug: str,
) -> bool:
    """Manually clears the daily post limit drain lock (e.g. from dashboard)."""
    if redis_client is None:
        return False
    try:
        key = get_drain_key(profile_slug)
        res = bool(redis_client.delete(key))
        if res:
            logger.info("Cleared daily post limit drain lock for profile '%s'", profile_slug)
        return res
    except Exception as e:
        logger.error("Failed to clear daily post limit drain lock: %s", e)
        return False
