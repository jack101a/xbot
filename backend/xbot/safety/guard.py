from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.safety.guard import (
    BASE_LIMITS,
    SafetyGuard,
    calculate_adjusted_limits,
    calculate_warmup_multiplier,
    clear_daily_post_limit_drained,
    get_daily_post_limit_status,
    handle_action_failure,
    is_daily_post_limit_drained,
    send_webhook_alert,
    set_daily_post_limit_drained,
)

__all__ = [
    "BASE_LIMITS",
    "SafetyGuard",
    "calculate_adjusted_limits",
    "calculate_warmup_multiplier",
    "clear_daily_post_limit_drained",
    "get_daily_post_limit_status",
    "handle_action_failure",
    "is_daily_post_limit_drained",
    "send_webhook_alert",
    "set_daily_post_limit_drained",
]
