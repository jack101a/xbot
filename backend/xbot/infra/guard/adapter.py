"""
xbot.infra.guard.adapter: Concrete implementation of GuardPort wrapping SafetyGuard.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from xbot.contracts.ports import GuardPort
from xbot.database import AsyncSessionLocal
from xbot.safety.guard import SafetyGuard

logger = logging.getLogger(__name__)


class CentralGuardAdapter(GuardPort):
    """Unified safety and rate-limiting adapter implementing GuardPort."""

    def __init__(self, guard: SafetyGuard | None = None) -> None:
        self._guard = guard or SafetyGuard()

    async def can_act(self, profile_slug: str, action: str, target_id: str | None = None) -> bool:
        try:
            async with AsyncSessionLocal() as db:
                is_safe = await self._guard.is_action_safe(
                    db=db,
                    profile_slug=profile_slug,
                    action_type=action,
                )
                return is_safe
        except Exception as exc:
            logger.error(f"[GuardAdapter] Error checking safety for '{profile_slug}'/'{action}': {exc}", exc_info=True)
            # Default to allowing in failure-tolerant mode if guard DB query fails
            return True

    async def record_action(self, profile_slug: str, action: str, target_id: str | None = None) -> None:
        try:
            self._guard.limiter.record_action(profile_slug=profile_slug, action_type=action)
        except Exception as exc:
            logger.warning(f"[GuardAdapter] Error recording action for '{profile_slug}'/'{action}': {exc}")

    async def record_failure(self, profile_slug: str, error: str) -> None:
        logger.warning(f"[GuardAdapter] Profile '{profile_slug}' recorded failure: {error}")
