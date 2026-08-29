from __future__ import annotations

import logging
from typing import Any

from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper, strip_surrounding_quotes

from .cleaner import (
    enforce_length_cadence,
    enforce_pacing_whitespace,
    strip_formulaic_trailing_emojis,
)
from .typography import PostFormattingArchetype, select_archetype

logger = logging.getLogger(__name__)


def post_process_formatted_content(
    raw_content: str,
    archetype: PostFormattingArchetype = PostFormattingArchetype.HOT_TAKE_PUNCH,
    max_hard_limit: int = 280,
) -> str:
    """
    Unified post-processing pipeline for synthesized content:
    1. Strips outer surrounding quotes.
    2. Typographical remediation (smart quotes, em-dashes, emoji bullets to clean hyphens).
    3. Pacing whitespace (\\n\\n).
    4. Strip formulaic trailing emojis.
    5. Length cadence enforcement.
    6. Strips any leftover outer quotes.
    """
    text = strip_surrounding_quotes(raw_content)
    gatekeeper = AntiAIGatekeeper()
    text = gatekeeper.remediate_minor_issues(text)
    text = enforce_pacing_whitespace(text, archetype)
    text = strip_formulaic_trailing_emojis(text)
    text = enforce_length_cadence(text, archetype, max_hard_limit)
    return strip_surrounding_quotes(text)


def format_content(
    raw_text: str,
    profile_slug: str = "default",
    content_type: str = "post",
    has_media: bool = False,
    topic: str = "",
    archetype: PostFormattingArchetype | None = None,
    max_hard_limit: int = 280,
    redis_client: Any | None = None,
) -> str:
    """
    Global entry-point for formatting any generated content across all pipelines:
    1. Selects or enforces archetype with anti-monotony rotation per profile.
    2. Runs typographical cleaning, spacing enforcement, and trailing emoji removal.
    3. Records chosen archetype in Redis for rotation history.
    """
    if archetype is None:
        recent_archetypes: list[str] = []
        try:
            if redis_client is not None:
                r = redis_client
            else:
                import redis
                from xbot.config import settings

                r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            recent_archetypes = r.lrange(f"xbot:formatting:recent_archetypes:{profile_slug}", 0, 4)
        except Exception:
            pass

        archetype = select_archetype(
            topic=topic or raw_text[:50],
            has_media=has_media,
            recent_archetypes=recent_archetypes,
            content_type=content_type,
        )

        try:
            if redis_client is not None:
                r = redis_client
            else:
                import redis
                from xbot.config import settings

                r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            key = f"xbot:formatting:recent_archetypes:{profile_slug}"
            r.lpush(key, archetype.value)
            r.ltrim(key, 0, 9)
            r.expire(key, 86400 * 3)
        except Exception:
            pass

    return post_process_formatted_content(raw_text, archetype=archetype, max_hard_limit=max_hard_limit)
