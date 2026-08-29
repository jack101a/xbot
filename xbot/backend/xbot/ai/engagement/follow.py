from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.models.profile import Profile
from xbot.persona import load_persona

from .heuristics import FollowDecision, FollowResponse
from .scorer import build_follow_prompts

logger = logging.getLogger(__name__)


def _get_client_fallback() -> Any:
    import sys
    mod = sys.modules.get("xbot.ai.engagement")
    if mod and hasattr(mod, "get_ai_client"):
        return mod.get_ai_client()
    return get_ai_client()


class FollowEvaluator:
    """
    Evaluates whether a target profile is worth following using MODEL_FOLLOW.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def evaluate_follow(
        self,
        db: AsyncSession,
        profile_slug: str,
        target_username: str,
        target_bio: str,
        recent_tweets: list[str],
    ) -> bool:
        """
        Determines if the persona should follow the target user.
        """
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)

        client = _get_client_fallback()

        system_prompt, user_prompt = build_follow_prompts(
            persona=persona,
            target_username=target_username,
            target_bio=target_bio,
            recent_tweets=recent_tweets,
        )

        try:
            try:
                completion = await client.beta.chat.completions.parse(
                    model=settings.MODEL_FOLLOW,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=FollowResponse,
                )
                parsed = completion.choices[0].message.parsed
                if parsed and parsed.decision:
                    return parsed.decision.should_follow
                else:
                    return False
            except Exception as e:
                completion = await client.chat.completions.create(
                    model=settings.MODEL_FOLLOW,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
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
                parsed_obj = FollowResponse.model_validate(data)
                return parsed_obj.decision.should_follow
        except Exception as e:
            logger.error("Follow evaluation failed: %s. Defaulting to false.", e)
            return False
