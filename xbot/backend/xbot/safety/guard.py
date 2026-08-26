from __future__ import annotations

import datetime
import logging
import random
import re
from pathlib import Path
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import load_config
from xbot.safety.limiter import SlidingWindowLimiter

logger = logging.getLogger(__name__)


class SafetyGuard:
    """
    Implements Phase 3.3 (cooldowns, warm-ups, variance),
    Phase 3.4 (circuit breaker, backoff), and Phase 3.5 (health signal detection).
    Orchestrates SlidingWindowLimiter to safeguard profile accounts from detection and bans.
    """

    # Base Limits as defined in Section 9.2
    # Action type -> (hourly_cap, daily_cap)
    BASE_LIMITS = {
        "post": (3, 15),
        "reply": (5, 30),
        "like": (10, 50),
        "retweet": (3, 15),
        "quote": (2, 10),
        "follow": (3, 15),
    }

    def __init__(
        self,
        redis_url: str | None = None,
        base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles",
    ) -> None:
        self.r = redis.from_url(redis_url or settings.REDIS_URL)
        self.limiter = SlidingWindowLimiter(redis_url)
        self.base_profile_dir = Path(base_profile_dir)

    def get_warmup_multiplier(self, created_at: datetime.datetime, now_utc: datetime.datetime) -> float:
        """Calculates account age and returns multiplier based on Section 9.5 Table."""
        # Convert created_at to naive UTC if aware
        c_at = created_at.replace(tzinfo=None)
        n_utc = now_utc.replace(tzinfo=None)
        age_days = (n_utc - c_at).days

        if age_days < 7:
            return 0.25  # Week 1
        elif age_days < 14:
            return 0.50  # Week 2
        elif age_days < 21:
            return 0.75  # Week 3
        elif age_days < 30:
            return 0.50  # Under 30 days (new account limit multiplier)
        elif age_days < 90:
            return 0.75  # Growing account limit multiplier
        else:
            return 1.0  # Established (>90 days)

    def get_adjusted_limits(
        self,
        profile_slug: str,
        action_type: str,
        created_at: datetime.datetime,
        now_utc: datetime.datetime,
    ) -> tuple[int, int]:
        """Calculates limits from profile config (or base defaults), warm-up multiplier, and backoff."""
        base_hourly = 5
        base_daily = 20
        warmup_enabled = True

        # 1. Load profile config limits if available
        try:
            cfg_path = self.base_profile_dir / profile_slug
            if (cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists():
                config = load_config(cfg_path)
                limits_cfg = getattr(config, "limits", None)
                if limits_cfg:
                    warmup_enabled = getattr(limits_cfg, "warmup_enabled", False)
                    if action_type == "post":
                        base_daily = getattr(limits_cfg, "max_posts_per_day", 5)
                        base_hourly = max(2, (base_daily + 5) // 6)
                    elif action_type == "reply":
                        base_daily = getattr(limits_cfg, "max_replies_per_day", 15)
                        base_hourly = max(5, (base_daily + 5) // 6)
                    elif action_type == "like":
                        base_daily = getattr(limits_cfg, "max_likes_per_day", 50)
                        base_hourly = max(10, (base_daily + 5) // 6)
                    elif action_type == "follow":
                        base_daily = getattr(limits_cfg, "max_follows_per_day", 10)
                        base_hourly = max(3, (base_daily + 5) // 6)
                    elif action_type == "retweet":
                        posts = getattr(limits_cfg, "max_posts_per_day", 5)
                        base_daily = max(15, round(posts * 2))
                        base_hourly = max(3, (base_daily + 5) // 6)
                    elif action_type == "quote":
                        posts = getattr(limits_cfg, "max_posts_per_day", 5)
                        base_daily = max(10, posts)
                        base_hourly = max(2, (base_daily + 5) // 6)
                else:
                    base_hourly, base_daily = self.BASE_LIMITS.get(action_type, (5, 20))
            else:
                base_hourly, base_daily = self.BASE_LIMITS.get(action_type, (5, 20))
        except Exception:
            base_hourly, base_daily = self.BASE_LIMITS.get(action_type, (5, 20))

        # 2. Warm-up multiplier (only if enabled)
        multiplier = self.get_warmup_multiplier(created_at, now_utc) if warmup_enabled else 1.0

        # 3. Backoff reduction: check if backoff_until key is active
        backoff_key = f"backoff:{profile_slug}"
        if self.r.exists(backoff_key):
            logger.info("Applying progressive backoff (50%% limit reduction) for profile %s.", profile_slug)
            multiplier *= 0.5

        # 4. Calculate limits
        hourly = max(1, round(base_hourly * multiplier))
        daily = max(1, round(base_daily * multiplier))

        return hourly, daily

    async def is_action_safe(
        self,
        db: AsyncSession,
        profile_slug: str,
        action_type: str,
        now_utc: datetime.datetime | None = None,
    ) -> bool:
        """Runs safety check pipeline: DB status, active cooldowns, and sliding window rate limit checks."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        # Check if mock mode or safety disabled in config
        config = None
        try:
            cfg_path = self.base_profile_dir / profile_slug
            if (cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists():
                config = load_config(cfg_path)
                if getattr(config, "mock_mode", False):
                    logger.info("Bypassing safety guard checks for mock profile: %s", profile_slug)
                    return True
                limits_cfg = getattr(config, "limits", None)
                if limits_cfg and getattr(limits_cfg, "safety_mode", "normal") == "disabled":
                    logger.info("Bypassing safety guard checks (safety_mode=disabled) for profile: %s", profile_slug)
                    return True
        except Exception:
            pass

        # A. Query Profile Status in DB
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            logger.error("Limiter check failed: profile slug %s not found in DB.", profile_slug)
            return False

        if profile.status in (ProfileStatus.LOCKED, ProfileStatus.SUSPENDED):
            logger.warning("Rejecting action: profile %s is currently %s.", profile_slug, profile.status)
            return False

        # B. Check Action Cooldown
        limits_cfg = getattr(config, "limits", None) if config else None
        cooldown_cfg = getattr(limits_cfg, "cooldown_seconds", None) if limits_cfg else None
        if cooldown_cfg != 0:
            if self.limiter.is_cooldown_active(profile_slug, action_type, now_utc):
                logger.info("Rejecting action: Cooldown active for action '%s' on profile %s.", action_type, profile_slug)
                return False

        # C. Retrieve Adjusted limits (Warm-up + Backoff + User Config)
        limit_hourly, limit_daily = self.get_adjusted_limits(
            profile_slug=profile_slug,
            action_type=action_type,
            created_at=profile.created_at,
            now_utc=now_utc,
        )

        # D. Sliding Window count check
        is_limited = self.limiter.is_rate_limited(
            profile_slug=profile_slug,
            action_type=action_type,
            limit_hourly=limit_hourly,
            limit_daily=limit_daily,
            now_utc=now_utc,
        )

        return not is_limited

    async def record_action_success(
        self,
        profile_slug: str,
        action_type: str,
        now_utc: datetime.datetime | None = None,
    ) -> None:
        """Records the action success in rate limits and applies configured cooldowns."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

        # 1. Clear consecutive failures
        failure_key = f"failures:{profile_slug}"
        self.r.delete(failure_key)

        # 2. Record action execution time in sliding window
        self.limiter.record_action(profile_slug, action_type, now_utc)

        # 3. Check custom cooldown configuration
        try:
            cfg_path = self.base_profile_dir / profile_slug
            config = load_config(cfg_path) if ((cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists()) else None
            limits_cfg = getattr(config, "limits", None) if config else None
        except Exception:
            limits_cfg = None

        if limits_cfg and getattr(limits_cfg, "safety_mode", "normal") == "disabled":
            return

        custom_cooldown = getattr(limits_cfg, "cooldown_seconds", None) if limits_cfg else None
        if custom_cooldown is not None:
            cooldown_seconds = custom_cooldown
        else:
            # Natural intra-session human pacing
            if action_type == "like":
                cooldown_seconds = random.randint(10, 30)
            elif action_type == "reply":
                cooldown_seconds = random.randint(20, 60)
            elif action_type == "post":
                cooldown_seconds = random.randint(30, 90)
            elif action_type in ("retweet", "quote"):
                cooldown_seconds = random.randint(20, 60)
            elif action_type == "follow":
                cooldown_seconds = random.randint(15, 45)
            else:
                cooldown_seconds = 15

        if cooldown_seconds > 0:
            self.limiter.set_cooldown(profile_slug, action_type, cooldown_seconds, now_utc)

        # Reset consecutive failure counter on success
        try:
            failure_key = f"failures:{profile_slug}"
            self.r.delete(failure_key)
        except Exception:
            pass

    def _send_webhook_alert(self, title: str, message: str, level: str = "warning") -> None:
        """Sends a synchronous JSON POST webhook payload to external alerts handler (Discord/Telegram)."""
        url = settings.WEBHOOK_URL
        if not url:
            return

        import json
        import urllib.request

        payload = {
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

        # If it looks like a Discord webhook URL, format with embeds
        if "discord.com" in url:
            color = 16711680 if level == "critical" else 16776960  # red or yellow
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

    async def record_action_failure(
        self,
        db: AsyncSession,
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

        # Ignore internal lock / concurrency errors from triggering health signal account locks
        if any(ignore in err_lower for ignore in ("redis", "browser lock", "database is locked", "mutex", "lock:browser", "lock collision", "lock error", "lock failed")):
            logger.info("Internal lock/concurrency collision for %s; bypassing health signal lock.", profile_slug)
            return

        # A. Health Signal Detection: Locked account on X
        if any(w in err_lower for w in ("your account has been locked", "account has been locked", "account suspended", "your account is suspended", "unusual activity detected on your account", "account is temporarily locked")):
            logger.critical("Health Signal Alert: Account %s detected as LOCKED on X.", profile_slug)
            profile.status = ProfileStatus.LOCKED
            await db.commit()
            self._send_webhook_alert(
                title=f"CRITICAL: Account Locked - {profile_slug}",
                message=f"XBot detected that account @{profile.x_handle} ({profile_slug}) has been locked or suspended on X. Action details: {error_message}",
                level="critical"
            )
            return

        # B. Health Signal Detection: CAPTCHA / verify pages
        if any(w in err_lower for w in ("arkoselabs", "funcaptcha", "recaptcha", "solve this puzzle", "prove you are human")):
            logger.critical("Health Signal Alert: CAPTCHA challenge encountered for profile %s. Pausing.", profile_slug)
            profile.status = ProfileStatus.PAUSED
            await db.commit()
            self._send_webhook_alert(
                title=f"ALERT: CAPTCHA Challenge - {profile_slug}",
                message=f"XBot encountered a CAPTCHA or verification challenge for @{profile.x_handle} ({profile_slug}). The profile scheduler has been PAUSED.",
                level="warning"
            )
            return

        # C. Progressive Backoff: 429 rate limits
        if any(w in err_lower for w in ("429", "rate limit", "too many requests", "shadowban")):
            logger.warning("Progressive Backoff: Rate limit / shadowban signal detected for %s.", profile_slug)
            backoff_key = f"backoff:{profile_slug}"
            self.r.set(backoff_key, "1", ex=86400)  # 24h limit reduction
            return

        # D. Circuit Breaker: consecutive fatal system-level auth crashes (ignore transient single DOM misses)
        if any(w in err_lower for w in ("session invalidated", "cookie expired", "unauthorized", "login required", "generic connection error")):
            failure_key = f"failures:{profile_slug}"
            failures = self.r.incr(failure_key)
            self.r.expire(failure_key, 3600)

            if failures >= 3:
                logger.critical("Circuit Breaker Triggered: %d consecutive auth crashes for profile %s. Pausing.", failures, profile_slug)
                profile.status = ProfileStatus.PAUSED
                await db.commit()
                self.r.delete(failure_key)
                self._send_webhook_alert(
                    title=f"CRITICAL: Circuit Breaker Triggered - {profile_slug}",
                    message=f"XBot triggered the circuit breaker for @{profile.x_handle} ({profile_slug}) after {failures} consecutive auth crashes. Profile PAUSED.",
                    level="critical"
                )
