from __future__ import annotations

import datetime
import logging
from pathlib import Path
import random
from typing import Any
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import load_config
from xbot.safety.limiter import SlidingWindowLimiter

from .rules import (
    BASE_LIMITS,
    calculate_adjusted_limits,
    calculate_warmup_multiplier,
)
from .validators import handle_action_failure, send_webhook_alert

logger = logging.getLogger(__name__)


class SafetyGuard:
    """
    Implements Phase 3.3 (cooldowns, warm-ups, variance),
    Phase 3.4 (circuit breaker, backoff), and Phase 3.5 (health signal detection).
    Orchestrates SlidingWindowLimiter to safeguard profile accounts from detection and bans.
    """

    BASE_LIMITS = BASE_LIMITS

    def __init__(
        self,
        redis_url: str | None = None,
        base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles",
    ) -> None:
        self.r = redis.from_url(redis_url or settings.REDIS_URL)
        self.limiter = SlidingWindowLimiter(redis_url)
        self.base_profile_dir = Path(base_profile_dir)

    def get_warmup_multiplier(
        self, created_at: datetime.datetime, now_utc: datetime.datetime
    ) -> float:
        return calculate_warmup_multiplier(created_at, now_utc)

    def get_adjusted_limits(
        self,
        profile_slug: str,
        action_type: str,
        created_at: datetime.datetime,
        now_utc: datetime.datetime,
    ) -> tuple[int, int]:
        return calculate_adjusted_limits(
            base_profile_dir=self.base_profile_dir,
            redis_client=self.r,
            profile_slug=profile_slug,
            action_type=action_type,
            created_at=created_at,
            now_utc=now_utc,
        )

    async def is_action_safe(
        self,
        db: AsyncSession,
        profile_slug: str,
        action_type: str,
        now_utc: datetime.datetime | None = None,
        bypass_cooldown: bool = False,
    ) -> bool:
        """Runs safety check pipeline: DB status, active cooldowns, and sliding window rate limit checks."""
        if now_utc is None:
            now_utc = datetime.datetime.utcnow()

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
        if not bypass_cooldown:
            limits_cfg = getattr(config, "limits", None) if config else None
            cooldown_cfg = getattr(limits_cfg, "cooldown_seconds", None) if limits_cfg else None
            if cooldown_cfg != 0:
                if self.limiter.is_cooldown_active(profile_slug, action_type, now_utc):
                    logger.info("Rejecting action: Cooldown active for action '%s' on profile %s.", action_type, profile_slug)
                    return False

        # C. Retrieve Adjusted limits
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

        failure_key = f"failures:{profile_slug}"
        self.r.delete(failure_key)

        self.limiter.record_action(profile_slug, action_type, now_utc)

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

        try:
            failure_key = f"failures:{profile_slug}"
            self.r.delete(failure_key)
        except Exception:
            pass

    def _send_webhook_alert(self, title: str, message: str, level: str = "warning") -> None:
        send_webhook_alert(title, message, level)

    async def record_action_failure(
        self,
        db: AsyncSession,
        profile_slug: str,
        error_message: str,
    ) -> None:
        await handle_action_failure(db, self.r, profile_slug, error_message)
