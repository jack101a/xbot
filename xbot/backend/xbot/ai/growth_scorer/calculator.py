from __future__ import annotations

import logging
import math
from typing import Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OpportunityScore(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="Compound opportunity score (0.0 to 100.0)")
    reply_loop_multiplier: float = Field(..., description="Author reply loop multiplier (up to 150.0x)")
    bookmark_potential: float = Field(..., description="Bookmark value multiplier (up to 50.0x)")
    velocity: float = Field(..., description="Rate of engagements per hour")
    has_link_penalty: bool = Field(..., description="True if tweet contains external links (-70% suppression)")
    author_is_verified: bool = Field(..., description="True if tweet author has verified status")
    recommended_action: Literal["sniper_reply", "quote_tweet", "bookmark_reference", "skip"] | str = Field(
        ..., description="Recommended action: sniper_reply, quote_tweet, bookmark_reference, skip"
    )
    reasoning: str = Field(..., description="Algorithmic scoring reasoning breakdown")


def compute_composite_opportunity_score(
    velocity: float,
    reply_loop_multiplier: float,
    bookmark_potential: float,
    author_is_verified: bool,
    has_link_penalty: bool,
    delta_hours: float,
    replies: int,
    author_history: dict[str, Any] | None,
) -> tuple[float, bool]:
    """Computes the final 0-100 composite score, returning (final_score, is_bot)."""
    vel_signal = min(35.0, 35.0 * (velocity / (velocity + 40.0))) if velocity > 0 else 0.0

    if delta_hours <= 4.0:
        fresh_bonus = 28.0 * math.exp(-0.25 * delta_hours)
        vel_signal = max(vel_signal, fresh_bonus)
    elif delta_hours <= 12.0 and replies >= 2:
        vel_signal = max(vel_signal, 18.0)

    if author_history is not None:
        reply_signal = 35.0 * (reply_loop_multiplier / 150.0)
    else:
        reply_signal = 22.0

    bookmark_signal = 25.0 * (bookmark_potential / 50.0)
    verified_signal = 15.0 if author_is_verified else 5.0

    raw_score = vel_signal + reply_signal + bookmark_signal + verified_signal

    lambda_decay = math.log(2) / 6.0
    age_decay = math.exp(-lambda_decay * delta_hours)
    decayed_score = raw_score * (age_decay ** 0.75)

    is_bot = bool(
        author_history
        and (author_history.get("is_broadcast_bot") or author_history.get("reply_rate") == 0.0)
    )
    if is_bot:
        decayed_score = min(decayed_score, 20.0) * 0.2

    if has_link_penalty:
        final_score = decayed_score * 0.3
    else:
        final_score = decayed_score

    return round(max(0.0, min(100.0, final_score)), 2), is_bot
