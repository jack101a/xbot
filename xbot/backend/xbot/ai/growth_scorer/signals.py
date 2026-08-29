from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import math
import re
from typing import Any

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
        try:
            cleaned = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            pass

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
