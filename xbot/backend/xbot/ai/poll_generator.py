from __future__ import annotations
import json
import logging
from typing import Any
from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.ai.poll_models import GeneratedPoll
from xbot.ai.poll_prompts import (
    _clean_text_for_json,
    _get_persona_field,
    _build_poll_system_prompt,
    _build_poll_user_prompt,
    _parse_poll_from_json,
)

logger = logging.getLogger(__name__)

async def generate_poll(
    persona: Any,
    topic: str | None = None,
    client: Any = None,
) -> GeneratedPoll | None:
    """Generates an authentic, persona-grounded poll. Returns None if generation fails - NEVER posts template fallback."""
    if client is None:
        client = get_ai_client()

    sys_prompt = _build_poll_system_prompt(persona, topic=topic)
    usr_prompt = _build_poll_user_prompt(persona, topic=topic)
    job_model = getattr(settings, "MODEL_POLL_GENERATOR", "litellm/gpt-oss-120b")

    try:
        if hasattr(client, "beta") and hasattr(client.beta, "chat") and hasattr(client.beta.chat, "completions"):
            try:
                completion = await client.beta.chat.completions.parse(
                    model=job_model,
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": usr_prompt},
                    ],
                    response_format=GeneratedPoll,
                )
                if completion.choices and completion.choices[0].message.parsed:
                    return completion.choices[0].message.parsed
            except Exception as e:
                logger.warning("Beta parse failed: %s", e)

        completion = await client.chat.completions.create(
            model=job_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": usr_prompt},
            ],
            response_format={"type": "json_object"},
        )
        raw_content = completion.choices[0].message.content or ""
        poll = _parse_poll_from_json(raw_content)
        if poll is not None:
            return poll
        logger.warning("Failed to parse poll JSON from AI completion. Discarding to avoid template slop.")
        return None

    except Exception as e:
        logger.error("Error during poll generation: %s. Discarding without template fallback.", e)
        return None

__all__ = [
    "GeneratedPoll",
    "generate_poll",
    "_clean_text_for_json",
    "_parse_poll_from_json",
    "_build_poll_system_prompt",
    "_build_poll_user_prompt",
]
