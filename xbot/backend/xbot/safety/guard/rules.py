from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any
import redis

from xbot.persona import load_config

logger = logging.getLogger(__name__)

# Base Limits as defined in Section 9.2
# Action type -> (hourly_cap, daily_cap)
BASE_LIMITS: dict[str, tuple[int, int]] = {
    "post": (5, 30),
    "growth_post": (2, 24),
    "reply": (15, 60),
    "like": (25, 120),
    "retweet": (5, 25),
    "quote": (5, 20),
    "follow": (10, 50),
    "unfollow": (10, 50),
}


def calculate_warmup_multiplier(
    created_at: datetime.datetime, now_utc: datetime.datetime
) -> float:
    """Calculates account age and returns multiplier based on Section 9.5 Table."""
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


def calculate_adjusted_limits(
    base_profile_dir: Path,
    redis_client: redis.Redis,
    profile_slug: str,
    action_type: str,
    created_at: datetime.datetime,
    now_utc: datetime.datetime,
) -> tuple[int, int]:
    """Calculates limits from profile config (or base defaults), warm-up multiplier, and backoff."""
    base_hourly = 5
    base_daily = 20
    warmup_enabled = True

    try:
        cfg_path = base_profile_dir / profile_slug
        if (cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists():
            config = load_config(cfg_path)
            limits_cfg = getattr(config, "limits", None)
            if limits_cfg:
                warmup_enabled = getattr(limits_cfg, "warmup_enabled", False)
                if action_type == "post":
                    base_daily = getattr(limits_cfg, "max_posts_per_day", 15)
                    base_hourly = max(6, (base_daily + 2) // 3)
                elif action_type == "reply":
                    base_daily = getattr(limits_cfg, "max_replies_per_day", 40)
                    base_hourly = max(10, (base_daily + 2) // 3)
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
                base_hourly, base_daily = BASE_LIMITS.get(action_type, (5, 20))
        else:
            base_hourly, base_daily = BASE_LIMITS.get(action_type, (5, 20))
    except Exception:
        base_hourly, base_daily = BASE_LIMITS.get(action_type, (5, 20))

    multiplier = calculate_warmup_multiplier(created_at, now_utc) if warmup_enabled else 1.0

    backoff_key = f"backoff:{profile_slug}"
    if redis_client.exists(backoff_key):
        logger.info("Applying progressive backoff (50%% limit reduction) for profile %s.", profile_slug)
        multiplier *= 0.5

    hourly = max(1, round(base_hourly * multiplier))
    daily = max(1, round(base_daily * multiplier))

    return hourly, daily
