from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.safety.guard import (
    BASE_LIMITS,
    SafetyGuard,
    calculate_adjusted_limits,
    calculate_warmup_multiplier,
    handle_action_failure,
    send_webhook_alert,
)

__all__ = [
    "BASE_LIMITS",
    "SafetyGuard",
    "calculate_adjusted_limits",
    "calculate_warmup_multiplier",
    "handle_action_failure",
    "send_webhook_alert",
]
