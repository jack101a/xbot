from __future__ import annotations

import logging
from typing import Any, Literal
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.models.profile import RateLimit
from xbot.persona import LearnedState, Persona, Relationships

logger = logging.getLogger(__name__)


class EngagementDecision(BaseModel):
    action: Literal["like", "retweet", "reply", "quote", "skip"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    content: str | None = Field(default=None, description="In-character text if reply/quote, null otherwise")


class TriageDecision(BaseModel):
    action: Literal["like", "retweet", "reply", "quote", "skip"]
    confidence: float = Field(..., ge=0.0, le=1.0)


class FollowDecision(BaseModel):
    should_follow: bool
    confidence: float = Field(..., ge=0.0, le=1.0)


class EngagementResponse(BaseModel):
    decision: EngagementDecision


class TriageResponse(BaseModel):
    decision: TriageDecision


class FollowResponse(BaseModel):
    decision: FollowDecision


def check_relationship(author: str, relationships: Relationships) -> bool:
    clean_author = author.strip().lstrip("@")
    return clean_author.lower() in {name.lower() for name in relationships.accounts.keys()}


def check_interest_area(tweet_text: str, persona: Persona) -> bool:
    interest_keywords = persona.interests.primary + persona.interests.secondary
    return any(kw.lower() in tweet_text.lower() for kw in interest_keywords)


async def apply_rate_budget_check(
    db: AsyncSession,
    profile_id: Any,
    config: Any,
    decision: EngagementDecision,
) -> EngagementDecision:
    """Enforces limits by downgrading quote->reply->like->skip based on remaining rate limits."""
    action = decision.action
    if action == "skip":
        return decision

    # Check reply limits (replies + quotes)
    if action in ("reply", "quote"):
        stmt = select(RateLimit).where(
            RateLimit.profile_id == profile_id,
            RateLimit.action_type == "reply",
        )
        res = await db.execute(stmt)
        lim_reply = res.scalar_one_or_none()
        used_replies = lim_reply.count_today if lim_reply else 0
        limit_replies = config.limits.max_replies_per_day

        if used_replies >= limit_replies:
            logger.info("Reply rate limit hit (%d/%d). Downgrading to like.", used_replies, limit_replies)
            action = "like"
            decision.action = "like"
            decision.content = None

    # Check like limits
    if action == "like":
        stmt = select(RateLimit).where(
            RateLimit.profile_id == profile_id,
            RateLimit.action_type == "like",
        )
        res = await db.execute(stmt)
        lim_like = res.scalar_one_or_none()
        used_likes = lim_like.count_today if lim_like else 0
        limit_likes = config.limits.max_likes_per_day

        if used_likes >= limit_likes:
            logger.info("Like rate limit hit (%d/%d). Downgrading to skip.", used_likes, limit_likes)
            action = "skip"
            decision.action = "skip"
            decision.content = None

    return decision
