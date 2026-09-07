from __future__ import annotations

import logging
import random
from typing import Tuple

from xbot.ai.growth_scorer import is_f4f_or_engagement_growth_post
from xbot.pipelines.instant_trend.types import TrendCandidateTweet

logger = logging.getLogger(__name__)


def evaluate_trend_candidates(
    candidates: list[TrendCandidateTweet],
    seen_tweet_ids: list[str],
    quote_percentage: int = 70,
) -> Tuple[str, TrendCandidateTweet | None]:
    """
    Evaluates discovered candidate tweets against the deduplication ledger
    and selects the optimal action: 'quote' (mostly, 70%) or 'post' (30%).
    Returns (action_type, selected_candidate).
    """
    seen_set = set(seen_tweet_ids)
    valid_candidates: list[TrendCandidateTweet] = []

    for c in candidates:
        # Strict deduplication: never interact with previously seen or quoted tweets
        if c.tweet_id in seen_set or c.url in seen_set:
            continue

        # Skip follow-trains, F4F spam, and low-quality threads
        if c.is_growth_thread or is_f4f_or_engagement_growth_post(c.text):
            continue

        # Reject extremely short spam
        if len(c.text) < 15:
            continue

        valid_candidates.append(c)

    if not valid_candidates:
        logger.info("InstantTrend: No un-seen candidates found. Defaulting to standalone post.")
        return ("post", None)

    # Score candidates: prioritize video trailers, media presence, official hashtags, and verified accounts
    def _score(t: TrendCandidateTweet) -> float:
        score = 1.0
        if t.has_video:
            score += 5.0  # Massive bonus for video trailers / teasers
        elif t.media_urls or t.media_alts:
            score += 3.5  # High bonus for photo / poster media
        if t.hashtags:
            score += 2.5  # Bonus for official hashtags
        if t.is_blue_tick:
            score += 2.0  # Bonus for verified / official studio accounts
        if 30 <= len(t.text) <= 280:
            score += 1.0
        return score

    sorted_candidates = sorted(valid_candidates, key=_score, reverse=True)
    best_candidate = sorted_candidates[0]

    # Quote-tweet dominance: always quote if media/video is present or if dice roll <= quote_percentage
    roll = random.randint(1, 100)
    should_quote = (best_candidate.has_video or bool(best_candidate.media_urls) or roll <= quote_percentage)
    if should_quote and best_candidate.url:
        logger.info("InstantTrend: Evaluator chose QUOTE for target: %s (author: @%s, has_video=%s, media=%d, hashtags=%s)",
                    best_candidate.url, best_candidate.author, best_candidate.has_video, len(best_candidate.media_urls), best_candidate.hashtags)
        return ("quote", best_candidate)
    else:
        logger.info("InstantTrend: Evaluator chose STANDALONE POST synthesizing trend around: @%s", best_candidate.author)
        return ("post", best_candidate)
