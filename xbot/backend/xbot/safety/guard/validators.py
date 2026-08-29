from __future__ import annotations

import datetime
import json
import logging
import urllib.request
from typing import Any
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.models.profile import Profile, ProfileStatus

logger = logging.getLogger(__name__)


def send_webhook_alert(title: str, message: str, level: str = "warning") -> None:
    """Sends a synchronous JSON POST webhook payload to external alerts handler (Discord/Telegram)."""
    url = settings.WEBHOOK_URL
    if not url:
        return

    payload = {
        "title": title,
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    if "discord.com" in url:
        color = 16711680 if level == "critical" else 16776960
        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                }
            ]
        }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "xbot-alerts"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except Exception as ex:
        logger.error("Failed to dispatch webhook alert: %s", ex)


async def handle_action_failure(
    db: AsyncSession,
    redis_client: redis.Redis,
    profile_slug: str,
    error_message: str,
) -> None:
    """
    Processes failures. Checks for CAPTCHAs, account locking (health signals),
    429 status code (progressive backoff), or consecutive errors (circuit breaker).
    """
    stmt = select(Profile).where(Profile.profile_slug == profile_slug)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        return

    err_lower = error_message.lower()

    if any(ignore in err_lower for ignore in ("redis", "browser lock", "database is locked", "mutex", "lock:browser", "lock collision", "lock error", "lock failed")):
        logger.info("Internal lock/concurrency collision for %s; bypassing health signal lock.", profile_slug)
        return

    # A. Health Signal Detection: Locked account on X
    if any(w in err_lower for w in ("your account has been locked", "account has been locked", "account suspended", "your account is suspended", "unusual activity detected on your account", "account is temporarily locked")):
        logger.critical("Health Signal Alert: Account %s detected as LOCKED on X.", profile_slug)
        profile.status = ProfileStatus.LOCKED
        await db.commit()
        send_webhook_alert(
            title=f"CRITICAL: Account Locked - {profile_slug}",
            message=f"XBot detected that account @{profile.x_handle} ({profile_slug}) has been locked or suspended on X. Action details: {error_message}",
            level="critical",
        )
        return

    # B. Health Signal Detection: CAPTCHA / verify pages
    if any(w in err_lower for w in ("arkoselabs", "funcaptcha", "recaptcha", "solve this puzzle", "prove you are human")):
        logger.critical("Health Signal Alert: CAPTCHA challenge encountered for profile %s. Pausing.", profile_slug)
        profile.status = ProfileStatus.PAUSED
        await db.commit()
        send_webhook_alert(
            title=f"ALERT: CAPTCHA Challenge - {profile_slug}",
            message=f"XBot encountered a CAPTCHA or verification challenge for @{profile.x_handle} ({profile_slug}). The profile scheduler has been PAUSED.",
            level="warning",
        )
        return

    # C. Progressive Backoff: 429 rate limits
    if any(w in err_lower for w in ("429", "rate limit", "too many requests", "shadowban")):
        logger.warning("Progressive Backoff: Rate limit / shadowban signal detected for %s.", profile_slug)
        backoff_key = f"backoff:{profile_slug}"
        redis_client.set(backoff_key, "1", ex=86400)
        return

    # D. Circuit Breaker: consecutive fatal system-level auth crashes
    if any(w in err_lower for w in ("session invalidated", "cookie expired", "unauthorized", "login required", "generic connection error")):
        failure_key = f"failures:{profile_slug}"
        failures = redis_client.incr(failure_key)
        redis_client.expire(failure_key, 3600)

        if failures >= 3:
            logger.critical("Circuit Breaker Triggered: %d consecutive auth crashes for profile %s. Pausing.", failures, profile_slug)
            profile.status = ProfileStatus.PAUSED
            await db.commit()
            redis_client.delete(failure_key)
            send_webhook_alert(
                title=f"CRITICAL: Circuit Breaker Triggered - {profile_slug}",
                message=f"XBot triggered the circuit breaker for @{profile.x_handle} ({profile_slug}) after {failures} consecutive auth crashes. Profile PAUSED.",
                level="critical",
            )
