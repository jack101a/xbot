from __future__ import annotations

import json
import logging
from pathlib import Path
import random
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.models.profile import Profile
from xbot.persona import load_config, load_learned_state, load_persona, load_relationships

from .heuristics import (
    EngagementDecision,
    EngagementResponse,
    TriageDecision,
    TriageResponse,
    apply_rate_budget_check,
    check_interest_area,
    check_relationship,
)
from .scorer import (
    build_reply_prompts,
    build_triage_prompts,
)

logger = logging.getLogger(__name__)


def _get_client_fallback() -> Any:
    import sys
    mod = sys.modules.get("xbot.ai.engagement")
    if mod and hasattr(mod, "get_ai_client"):
        return mod.get_ai_client()
    return get_ai_client()


class EngagementEvaluator:
    """
    Implements the Engagement Decision Flow.
    Checks relationships, interest keywords, calls the fast model (MODEL_LIKE_RETWEET) for triage,
    and applies database rate limit budget checks/downgrades.
    If the decision is reply/quote, it then uses MODEL_REPLY_ANALYSIS to generate the content.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def evaluate_engagement(
        self,
        db: AsyncSession,
        profile_slug: str,
        tweet: dict[str, Any],
    ) -> EngagementDecision:
        """
        Processes a single tweet and determines what action (like, retweet, reply, quote, skip)
        the persona should take towards it.
        """
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)
        config = load_config(profile_dir)
        relationships = load_relationships(profile_dir)
        learned_state = load_learned_state(profile_dir)

        profile_config = profile.config or {}
        job_overrides = profile_config.get("job_routing_overrides", {})

        triage_model = job_overrides.get("MODEL_LIKE_RETWEET") or settings.MODEL_LIKE_RETWEET
        triage_prompt = job_overrides.get("PROMPT_LIKE_RETWEET") or settings.PROMPT_LIKE_RETWEET
        triage_context = job_overrides.get("CONTEXT_LIKE_RETWEET") or settings.CONTEXT_LIKE_RETWEET
        triage_flags = set(triage_context.split(","))

        reply_model = job_overrides.get("MODEL_REPLY_ANALYSIS") or settings.MODEL_REPLY_ANALYSIS
        reply_prompt = job_overrides.get("PROMPT_REPLY_ANALYSIS") or settings.PROMPT_REPLY_ANALYSIS
        reply_context = job_overrides.get("CONTEXT_REPLY_ANALYSIS") or settings.CONTEXT_REPLY_ANALYSIS
        reply_flags = set(reply_context.split(","))

        author = tweet.get("author", "").strip().lstrip("@")
        tweet_text = tweet.get("text", "")

        is_relationship = check_relationship(author, relationships)
        in_interest_area = check_interest_area(tweet_text, persona)

        if not is_relationship and not in_interest_area:
            logger.info("Tweet is outside interests and relationships. Applying heuristics.")
            if random.random() < 0.8:
                return EngagementDecision(action="skip", confidence=0.8)
            else:
                decision = EngagementDecision(action="like", confidence=0.2)
                return await self._apply_rate_budget_check(db, profile.id, config, decision)

        client = _get_client_fallback()

        triage_system_prompt, triage_user_prompt = build_triage_prompts(
            persona=persona,
            learned_state=learned_state,
            triage_prompt=triage_prompt,
            triage_flags=triage_flags,
            author=author,
            tweet_text=tweet_text,
            is_relationship=is_relationship,
        )

        try:
            try:
                completion = await client.beta.chat.completions.parse(
                    model=triage_model,
                    messages=[
                        {"role": "system", "content": triage_system_prompt},
                        {"role": "user", "content": triage_user_prompt},
                    ],
                    response_format=TriageResponse,
                )
                parsed = completion.choices[0].message.parsed
                if parsed and parsed.decision:
                    action = parsed.decision.action
                    confidence = parsed.decision.confidence
                else:
                    raise ValueError("No triage decision parsed.")
            except Exception as e:
                logger.warning("Beta chat parse for triage failed, falling back: %s", e)
                completion = await client.chat.completions.create(
                    model=triage_model,
                    messages=[
                        {"role": "system", "content": triage_system_prompt},
                        {"role": "user", "content": triage_user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion.choices[0].message.content or ""
                cleaned_text = raw_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                data = json.loads(cleaned_text.strip())
                parsed_obj = TriageResponse.model_validate(data)
                action = parsed_obj.decision.action
                confidence = parsed_obj.decision.confidence
        except Exception as e:
            logger.error("Fast triage evaluation failed: %s. Defaulting to skip.", e)
            action = "skip"
            confidence = 1.0

        impressions = int(tweet.get("impressions", 0) or tweet.get("views", 0) or 0)
        if action == "quote":
            if 0 < impressions < 50_000:
                logger.info(
                    "Downgrading quote to reply: tweet has %d views (< 50k minimum for quote-tweets)",
                    impressions,
                )
                action = "reply"

        decision = EngagementDecision(action=action, confidence=confidence, content=None)
        decision = await self._apply_rate_budget_check(db, profile.id, config, decision)

        if decision.action in ("reply", "quote"):
            reply_system_prompt, reply_user_prompt = build_reply_prompts(
                persona=persona,
                learned_state=learned_state,
                relationships=relationships,
                reply_prompt=reply_prompt,
                reply_flags=reply_flags,
                author=author,
                tweet_text=tweet_text,
                is_relationship=is_relationship,
            )

            try:
                try:
                    completion = await client.beta.chat.completions.parse(
                        model=reply_model,
                        messages=[
                            {"role": "system", "content": reply_system_prompt},
                            {"role": "user", "content": reply_user_prompt},
                        ],
                        response_format=EngagementResponse,
                    )
                    parsed = completion.choices[0].message.parsed
                    if parsed and parsed.decision and parsed.decision.content:
                        decision.content = parsed.decision.content
                    else:
                        raise ValueError("No reply content parsed.")
                except Exception as e:
                    completion = await client.chat.completions.create(
                        model=reply_model,
                        messages=[
                            {"role": "system", "content": reply_system_prompt},
                            {"role": "user", "content": reply_user_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                    raw_text = completion.choices[0].message.content or ""
                    cleaned_text = raw_text.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[7:]
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-3]
                    data = json.loads(cleaned_text.strip())
                    parsed_obj = EngagementResponse.model_validate(data)
                    decision.content = parsed_obj.decision.content
            except Exception as e:
                logger.error("Heavy reply generation failed: %s. Downgrading to like.", e)
                decision.action = "like"
                decision.content = None

        return decision

    async def _apply_rate_budget_check(
        self,
        db: AsyncSession,
        profile_id: Any,
        config: Any,
        decision: EngagementDecision,
    ) -> EngagementDecision:
        """Enforces limits by downgrading quote->reply->like->skip based on remaining rate limits."""
        return await apply_rate_budget_check(db, profile_id, config, decision)
