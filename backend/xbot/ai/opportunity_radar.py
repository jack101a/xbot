from __future__ import annotations

import logging
import math
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CandidateOpportunity(BaseModel):
    tweet_id: str = Field(..., description="Unique tweet ID or URL hash")
    author: str = Field(..., description="Author handle")
    text: str = Field(..., description="Tweet text")
    url: str = Field(..., description="Tweet URL")
    age_minutes: float = Field(default=5.0, description="Minutes since post published")
    reply_count: int = Field(default=0, description="Existing replies count")
    likes: int = Field(default=0, description="Existing likes count")
    impressions: int = Field(default=0, description="Approx impressions count")
    relevance_score: float = Field(default=80.0, description="0 to 100 domain relevance")
    author_factor: float = Field(default=75.0, description="0 to 100 author reply affinity")
    arbitrage_score: float = Field(default=0.0, description="Calculated arbitrage score")
    top_comments: list[str] = Field(default_factory=list, description="Scraped top replies")


def calculate_velocity_score(age_minutes: float, impressions: int = 0) -> float:
    """
    Computes velocity and freshness score (0.0 to 100.0).
    Tweets < 5m score near 100. Tweets > 30m decay significantly.
    """
    if age_minutes <= 0:
        base_freshness = 100.0
    elif age_minutes >= 30.0:
        base_freshness = max(5.0, 100.0 * (1.0 / (1.0 + (age_minutes - 30.0) / 10.0)) * 0.3)
    else:
        base_freshness = 100.0 * (1.0 - (age_minutes / 30.0) * 0.7)

    # Impression multiplier (if post is picking up fast views)
    if impressions > 0:
        mult = min(1.3, 1.0 + math.log10(1.0 + impressions / 1000.0) * 0.1)
        base_freshness = min(100.0, base_freshness * mult)

    return round(base_freshness, 2)


def calculate_saturation_penalty(reply_count: int, saturation_threshold: int = 20) -> float:
    """
    Computes reply competition density penalty (0.0 to 1.0).
    < 5 replies: low penalty (< 0.25).
    >= threshold: max penalty (1.0).
    """
    if reply_count <= 0:
        return 0.0
    if reply_count >= saturation_threshold:
        return 1.0
    return round(reply_count / float(saturation_threshold), 3)


def calculate_arbitrage_score(
    velocity: float,
    relevance: float,
    author_factor: float,
    saturation_penalty: float,
    w_v: float = 0.40,
    w_r: float = 0.35,
    w_a: float = 0.25,
    w_c: float = 0.60,
) -> float:
    """
    Calculates total Arbitrage Score (0.0 to 100.0) based on Phoenix ranking principles.
    """
    raw_signal = (w_v * velocity) + (w_r * relevance) + (w_a * author_factor)
    penalty_multiplier = max(0.1, 1.0 - (w_c * saturation_penalty))
    final_score = raw_signal * penalty_multiplier
    return round(max(0.0, min(100.0, final_score)), 2)


class OpportunityRadar:
    """
    Scans, filters, and ranks candidate tweet opportunities for sniper replies.
    """

    def __init__(self, min_arbitrage_threshold: float = 65.0) -> None:
        self.min_arbitrage_threshold = min_arbitrage_threshold

    def evaluate_candidate(self, candidate: CandidateOpportunity) -> CandidateOpportunity:
        vel = calculate_velocity_score(candidate.age_minutes, candidate.impressions)
        sat = calculate_saturation_penalty(candidate.reply_count)
        score = calculate_arbitrage_score(
            velocity=vel,
            relevance=candidate.relevance_score,
            author_factor=candidate.author_factor,
            saturation_penalty=sat,
        )
        candidate.arbitrage_score = score
        return candidate

    def rank_opportunities(
        self, candidates: list[CandidateOpportunity]
    ) -> list[CandidateOpportunity]:
        evaluated = [self.evaluate_candidate(c) for c in candidates]
        filtered = [c for c in evaluated if c.arbitrage_score >= self.min_arbitrage_threshold]
        filtered.sort(key=lambda x: x.arbitrage_score, reverse=True)
        return filtered
