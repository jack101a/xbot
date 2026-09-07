from __future__ import annotations

from .calculator import (
    OpportunityScore,
    compute_composite_opportunity_score,
)
from .scorer import score_tweet_opportunity
from .signals import (
    BOOKMARK_KEYWORDS,
    F4F_AND_GROWTH_KEYWORDS,
    calculate_bookmark_potential,
    calculate_engagement_velocity,
    calculate_reply_loop_multiplier,
    detect_external_link,
    is_f4f_or_engagement_growth_post,
)

__all__ = [
    "BOOKMARK_KEYWORDS",
    "F4F_AND_GROWTH_KEYWORDS",
    "OpportunityScore",
    "calculate_bookmark_potential",
    "calculate_engagement_velocity",
    "calculate_reply_loop_multiplier",
    "compute_composite_opportunity_score",
    "detect_external_link",
    "is_f4f_or_engagement_growth_post",
    "score_tweet_opportunity",
]
