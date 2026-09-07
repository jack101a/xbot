from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.ai.growth_scorer import (
    BOOKMARK_KEYWORDS,
    F4F_AND_GROWTH_KEYWORDS,
    OpportunityScore,
    calculate_bookmark_potential,
    calculate_engagement_velocity,
    calculate_reply_loop_multiplier,
    compute_composite_opportunity_score,
    detect_external_link,
    is_f4f_or_engagement_growth_post,
    score_tweet_opportunity,
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
