from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from .calculator import OpportunityScore, compute_composite_opportunity_score
from .signals import (
    _parse_created_at,
    calculate_bookmark_potential,
    calculate_engagement_velocity,
    calculate_reply_loop_multiplier,
    detect_external_link,
    is_f4f_or_engagement_growth_post,
)

logger = logging.getLogger(__name__)


def score_tweet_opportunity(
    tweet_data: dict[str, Any],
    author_history: dict[str, Any] | None = None,
    reference_time: datetime | None = None,
) -> OpportunityScore:
    """
    Evaluates tweet opportunity based on modern X (Phoenix / Grok Recommender) algorithm weights:
    - Author reply-back probability (+150x boost)
    - Bookmark potential (+50x boost)
    - Engagement velocity with 6h half-life decay
    - External link suppression (-70% penalty)
    - Creator verification status (2.5x - 4.0x boost)
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    created_at_utc = _parse_created_at(tweet_data, reference_time)
    impressions = int(tweet_data.get("impressions", 0) or 0)
    likes = int(tweet_data.get("likes", 0) or tweet_data.get("like_count", 0) or 0)
    replies = int(tweet_data.get("replies", 0) or tweet_data.get("reply_count", 0) or 0)
    text = tweet_data.get("text", "") or tweet_data.get("content", "")

    # 1. Velocity
    velocity = calculate_engagement_velocity(
        impressions=impressions,
        likes=likes,
        replies=replies,
        created_at_utc=created_at_utc,
        reference_time=reference_time,
    )

    # 2. Bookmark Potential
    bookmark_potential = calculate_bookmark_potential(text)

    # 3. Author Reply Multiplier
    reply_loop_multiplier = calculate_reply_loop_multiplier(author_history)

    # 4. Verified Status
    author_is_verified = bool(
        tweet_data.get("is_verified")
        or tweet_data.get("author_is_verified")
        or tweet_data.get("verified")
        or (author_history and (author_history.get("is_verified") or author_history.get("verified")))
    )

    # 5. External Link Penalty
    has_link_penalty = detect_external_link(tweet_data)

    delta_hours = max(0.0, (reference_time - created_at_utc).total_seconds() / 3600.0)

    # 6. Composite scoring
    final_score, is_bot = compute_composite_opportunity_score(
        velocity=velocity,
        reply_loop_multiplier=reply_loop_multiplier,
        bookmark_potential=bookmark_potential,
        author_is_verified=author_is_verified,
        has_link_penalty=has_link_penalty,
        delta_hours=delta_hours,
        replies=replies,
        author_history=author_history,
    )

    # 7. Action recommendation and reasoning
    reasoning_parts = []
    if author_is_verified:
        reasoning_parts.append("Verified creator authority boost (+15pts)")
    if reply_loop_multiplier > 50.0:
        reasoning_parts.append(f"High author reply-back probability ({reply_loop_multiplier:.1f}x multiplier)")
    elif is_bot or reply_loop_multiplier <= 1.0:
        reasoning_parts.append("Broadcast/bot account with low reply probability (penalized)")

    if bookmark_potential >= 25.0:
        reasoning_parts.append(f"High bookmarkable utility ({bookmark_potential:.1f}x potential: lists/frameworks/data)")

    if has_link_penalty:
        reasoning_parts.append("External link detected (-70% algorithmic penalty)")

    if delta_hours > 12.0:
        reasoning_parts.append(f"Aged tweet ({delta_hours:.1f}h old), decayed opportunity window")
    else:
        reasoning_parts.append(f"Engagement velocity: {velocity:.1f}/h (age: {delta_hours:.1f}h)")

    is_f4f = is_f4f_or_engagement_growth_post(text)
    if is_f4f:
        reasoning_parts.append("Growth/F4F train detected (quoting forbidden; engage via reply/follow or create original post)")

    # Determine recommended action:
    if is_bot or delta_hours > 12.0 or (has_link_penalty and final_score < 25.0):
        recommended_action = "skip"
    elif bookmark_potential >= 25.0 and final_score >= 50.0:
        recommended_action = "bookmark_reference"
    elif impressions >= 50_000 and final_score >= 40.0 and not is_f4f:
        recommended_action = "quote_tweet"
    elif final_score >= 35.0:
        recommended_action = "sniper_reply"
    else:
        recommended_action = "sniper_reply"

    reasoning = ". ".join(reasoning_parts) + "."

    return OpportunityScore(
        score=final_score,
        reply_loop_multiplier=reply_loop_multiplier,
        bookmark_potential=bookmark_potential,
        velocity=velocity,
        has_link_penalty=has_link_penalty,
        author_is_verified=author_is_verified,
        recommended_action=recommended_action,
        reasoning=reasoning,
    )
