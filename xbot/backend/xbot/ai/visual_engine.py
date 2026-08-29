from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

from xbot.ai.anti_ai_gatekeeper import ANTI_AI_TYPOGRAPHY_DIRECTIVE, AntiAIGatekeeper
from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

# Valid format types & SimClusters
from xbot.ai.visual_templates import (
    FORMAT_TYPES,
    SIMCLUSTERS,
    VISUAL_FORMAT_TEMPLATES,
)


from xbot.ai.visual_models import VisualPostSpec
from xbot.ai.visual_inference import (
    infer_format_type,
    infer_simcluster,
    _build_visual_system_prompt,
    _build_visual_user_prompt,
)


async def generate_visual_post_spec(
    topic: str,
    format_type: str | None = None,
    persona: Persona | None = None,
    client: Any | None = None,
) -> VisualPostSpec:
    """
    Generates a 4:5 Visual Post Specification with One-Two Punch captioning
    and AI routing fallback (Gemini Flash / DeepSeek cascade).
    """
    if client is None:
        client = get_ai_client()

    gatekeeper = AntiAIGatekeeper()
    resolved_format = format_type or infer_format_type(topic)
    resolved_simcluster = infer_simcluster(topic, resolved_format)

    system_prompt = _build_visual_system_prompt(persona=persona, format_type=resolved_format)
    user_prompt = _build_visual_user_prompt(topic=topic, format_type=resolved_format, persona=persona)

    model_cascade = getattr(
        settings, "MODEL_POST_CREATION", "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    )

    try:
        logger.info("Generating visual post spec for topic: '%s' (format: %s)", topic[:50], resolved_format)
        response = await client.chat.completions.create(
            model=model_cascade,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.75,
            max_tokens=650,
        )

        content_str = response.choices[0].message.content or ""
        clean_json = content_str.strip()
        if "```" in clean_json:
            clean_json = re.sub(r"^```(?:json)?", "", clean_json).rstrip("`").strip()

        data = json.loads(clean_json)

        raw_tweet_copy = data.get("tweet_copy", "").strip()
        remediated_copy = gatekeeper.remediate_minor_issues(raw_tweet_copy)

        # Enforce < 140 chars strictly
        if len(remediated_copy) >= 140:
            truncated = remediated_copy[:136]
            last_space = truncated.rfind(" ")
            if last_space > 80:
                remediated_copy = truncated[:last_space] + "..."
            else:
                remediated_copy = truncated + "..."

        image_prompt = data.get("image_prompt", "").strip()
        if not image_prompt:
            image_prompt = VISUAL_FORMAT_TEMPLATES.get(resolved_format, {}).get("prompt_template", "")

        aspect_ratio = data.get("aspect_ratio", "4:5")
        if aspect_ratio not in ("4:5", "1:1"):
            aspect_ratio = "4:5"

        out_format = data.get("format_type", resolved_format)
        if out_format not in VISUAL_FORMAT_TEMPLATES:
            out_format = resolved_format

        out_simcluster = data.get("target_simcluster", resolved_simcluster)
        if out_simcluster not in ["Tech/AI", "Cinema/Prestige", "Urban/Creator", "Anime/PopCulture"]:
            out_simcluster = resolved_simcluster

        strategy = data.get("one_two_punch_strategy", "Setup tension in tweet copy; deliver visual punchline in 4:5 image.")

        return VisualPostSpec(
            tweet_copy=remediated_copy,
            image_prompt=image_prompt,
            aspect_ratio=aspect_ratio,
            format_type=out_format,
            target_simcluster=out_simcluster,
            one_two_punch_strategy=strategy,
        )

    except Exception as e:
        logger.error("Visual post spec AI generation failed for topic '%s': %s. Discarding without template fallback.", topic[:50], e)
        return None


__all__ = [
    "FORMAT_TYPES",
    "SIMCLUSTERS",
    "VISUAL_FORMAT_TEMPLATES",
    "VisualPostSpec",
    "infer_format_type",
    "infer_simcluster",
    "generate_visual_post_spec",
]
