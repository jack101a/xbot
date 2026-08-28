from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

BOOKMARK_KEYWORDS = [
    "framework",
    "cheatsheet",
    "cheat sheet",
    "guide",
    "roadmap",
    "curated",
    "breakdown",
    "playbook",
    "system design",
    "checklist",
    "templates",
    "template",
    "mental model",
    "resources",
    "architecture",
    "step-by-step",
    "tutorial",
    "best practices",
    "deep dive",
]

F4F_AND_GROWTH_KEYWORDS = [
    "f4f",
    "follow for follow",
    "follow-for-follow",
    "follow back",
    "drop your handle",
    "looking for mutuals",
    "gain mutuals",
    "follow train",
    "growth mutuals",
    "engagement growth",
    "follow back everyone",
    "verified mutuals",
    "connect with mutuals",
    "drop your @",
    "mutuals train",
    "follow-back",
]


def is_f4f_or_engagement_growth_post(text: str) -> bool:
    """Detects if a post is a follow-for-follow train, mutuals party, or engagement growth thread."""
    if not text:
        return False
    lower = text.lower()
    return any(k in lower for k in F4F_AND_GROWTH_KEYWORDS)


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


def calculate_engagement_velocity(
    impressions: int,
    likes: int,
    replies: int,
    created_at_utc: datetime,
    reference_time: datetime | None = None,
) -> float:
    """
    Calculates engagement velocity with 6-hour half-life exponential decay.
    Formula: Velocity = (Engagements / effective_hours) * exp(-lambda * delta_t)
    where lambda = ln(2) / 6.
    """
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    if created_at_utc.tzinfo is None:
        created_at_utc = created_at_utc.replace(tzinfo=timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    delta_seconds = max(0.0, (reference_time - created_at_utc).total_seconds())
    delta_hours = delta_seconds / 3600.0

    # 6-hour half-life decay factor
    lambda_decay = math.log(2) / 6.0
    decay_factor = math.exp(-lambda_decay * delta_hours)

    # Prevent division by zero with a minimum effective window (3 minutes = 0.05h)
    effective_hours = max(0.05, delta_hours)

    # Phoenix weighted engagement signal (replies have high weight, views baseline)
    weighted_engagements = float(likes) + (3.0 * float(replies)) + (0.01 * float(impressions))
    raw_rate = weighted_engagements / effective_hours

    velocity = raw_rate * decay_factor
    return round(max(0.0, velocity), 2)


def calculate_bookmark_potential(text: str) -> float:
    """
    Evaluates bookmarkability based on Phoenix algorithmic weights (+50x).
    Detects high-signal keywords, numbered lists, code blocks, and quantitative frameworks.
    Returns a multiplier from 1.0x to 50.0x.
    """
    if not text:
        return 1.0

    score = 1.0
    text_lower = text.lower()

    # 1. High-value keyword patterns
    matched_keywords = sum(1 for kw in BOOKMARK_KEYWORDS if kw in text_lower)
    score += min(20.0, matched_keywords * 6.0)

    # 2. Numbered or bulleted checklists
    has_list = bool(re.search(r'(?:^|\n)\s*(?:\d+[\.\)]|[-*•]|\[[\sxX]?\]|\d+\/\d+)\s+', text))
    if has_list:
        score += 15.0

    # 3. Code snippets or code-related syntax
    has_code = bool(
        re.search(
            r'(```|def\s+\w+|import\s+\w+|class\s+\w+|const\s+\w+|function\s+\w+|curl\s+|npm\s+|git\s+)',
            text,
        )
    )
    if has_code:
        score += 12.0

    # 4. Quantitative data, metrics, rules count
    has_metrics = bool(
        re.search(
            r'(\d+%\b|\$\d+|\d+x\b|\bp\d+\b|\b\d+\s+(?:rules|steps|tips|tools|lessons|metrics|insights|patterns|practices|principles)\b)',
            text,
            re.IGNORECASE,
        )
    )
    if has_metrics:
        score += 10.0

    return round(min(50.0, max(1.0, score)), 2)


def calculate_reply_loop_multiplier(author_history: dict[str, Any] | None = None) -> float:
    """
    Computes author reply loop multiplier (up to 150.0x) based on Phoenix weights.
    Penalizes broadcast bots and rewards conversational creators.
    """
    if not author_history:
        return 25.0

    if author_history.get("is_broadcast_bot") or author_history.get("is_bot"):
        return 0.1

    reply_rate = author_history.get("reply_rate")
    if reply_rate is None:
        reply_rate = author_history.get("reply_probability")

    if reply_rate is None:
        return 25.0

    if float(reply_rate) <= 0.0:
        return 0.1

    multiplier = 1.0 + (min(1.0, max(0.0, float(reply_rate))) * 149.0)
    return round(multiplier, 2)


def detect_external_link(tweet_data: dict[str, Any]) -> bool:
    """
    Detects if the tweet contains external links that trigger algorithmic suppression (-70%).
    """
    text = tweet_data.get("text", "") or tweet_data.get("content", "")
    urls = tweet_data.get("urls") or tweet_data.get("entities", {}).get("urls", [])
    if urls:
        return True

    if tweet_data.get("has_link") or tweet_data.get("has_external_link"):
        return True

    found_urls = re.findall(r'https?://[^\s]+', text)
    tweet_url = tweet_data.get("url", "")
    for u in found_urls:
        if tweet_url and u == tweet_url:
            continue
        return True

    return False


def _parse_created_at(
    tweet_data: dict[str, Any], reference_time: datetime
) -> datetime:
    """Helper to parse created_at into a UTC datetime."""
    raw = tweet_data.get("created_at_utc") or tweet_data.get("created_at")
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)

    if isinstance(raw, str):
        # Try ISO format
        try:
            cleaned = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pass

        # Try relative format e.g. "5m", "2h", "1d"
        rel_match = re.match(r'^(\d+)\s*([smhd])$', raw.strip().lower())
        if rel_match:
            val = int(rel_match.group(1))
            unit = rel_match.group(2)
            if unit == "s":
                return reference_time - timedelta(seconds=val)
            elif unit == "m":
                return reference_time - timedelta(minutes=val)
            elif unit == "h":
                return reference_time - timedelta(hours=val)
            elif unit == "d":
                return reference_time - timedelta(days=val)

    if "age_minutes" in tweet_data:
        return reference_time - timedelta(minutes=float(tweet_data["age_minutes"]))
    if "age_hours" in tweet_data:
        return reference_time - timedelta(hours=float(tweet_data["age_hours"]))

    return reference_time - timedelta(minutes=5)


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

    # 6. Composite scoring
    # Velocity Signal (0 to 35 pts)
    vel_signal = min(35.0, 35.0 * (velocity / (velocity + 40.0))) if velocity > 0 else 0.0

    # Freshness golden window: tweets under 4 hours are prime sniper opportunities even before viral metrics accumulate
    delta_hours = max(0.0, (reference_time - created_at_utc).total_seconds() / 3600.0)
    if delta_hours <= 4.0:
        fresh_bonus = 28.0 * math.exp(-0.25 * delta_hours)
        vel_signal = max(vel_signal, fresh_bonus)
    elif delta_hours <= 12.0 and replies >= 2:
        vel_signal = max(vel_signal, 18.0)

    # Reply Loop Signal (0 to 35 pts)
    if author_history is not None:
        reply_signal = 35.0 * (reply_loop_multiplier / 150.0)
    else:
        # Healthy creator baseline when author history is not yet populated
        reply_signal = 22.0

    # Bookmark Signal (0 to 25 pts)
    bookmark_signal = 25.0 * (bookmark_potential / 50.0)

    # Verified Bonus (0 to 15 pts)
    verified_signal = 15.0 if author_is_verified else 5.0

    # Raw score summation (0 to 100)
    raw_score = vel_signal + reply_signal + bookmark_signal + verified_signal

    # Age Decay Multiplier
    lambda_decay = math.log(2) / 6.0
    age_decay = math.exp(-lambda_decay * delta_hours)
    # Strongly decay stale tweets (>12h)
    decayed_score = raw_score * (age_decay ** 0.75)

    # Broadcast Bot Penalty
    is_bot = bool(author_history and (author_history.get("is_broadcast_bot") or author_history.get("reply_rate") == 0.0))
    if is_bot:
        decayed_score = min(decayed_score, 20.0) * 0.2

    # External Link Penalty (0.3x multiplier / -70% suppression)
    if has_link_penalty:
        final_score = decayed_score * 0.3
    else:
        final_score = decayed_score

    final_score = round(max(0.0, min(100.0, final_score)), 2)

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
    # 1. Skip stale tweets (>12h), explicit bots, or dead link spam (score < 25)
    if is_bot or delta_hours > 12.0 or (has_link_penalty and final_score < 25.0):
        recommended_action = "skip"
    elif bookmark_potential >= 25.0 and final_score >= 50.0:
        recommended_action = "bookmark_reference"
    elif impressions >= 50_000 and final_score >= 40.0 and not is_f4f:
        # Strictly reserve quote-tweets for viral posts with >=50k impressions (NEVER quote F4F/growth trains)
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
