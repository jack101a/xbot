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
            clean_json = re.sub(r"^```(?:json)?", "", clean_json, flags=re.MULTILINE)
            clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

        start_idx = clean_json.find("{")
        end_idx = clean_json.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = clean_json[start_idx : end_idx + 1]

        data = None
        try:
            data = json.loads(clean_json)
        except Exception:
            tweet_match = re.search(r'"tweet_copy"\s*:\s*"(.*?)"(?:\s*,\s*"\w+"|\s*})', clean_json, re.DOTALL)
            prompt_match = re.search(r'"image_prompt"\s*:\s*"(.*?)"(?:\s*,\s*"\w+"|\s*})', clean_json, re.DOTALL)
            aspect_match = re.search(r'"aspect_ratio"\s*:\s*"([^"]+)"', clean_json)
            fmt_match = re.search(r'"format_type"\s*:\s*"([^"]+)"', clean_json)
            sim_match = re.search(r'"target_simcluster"\s*:\s*"([^"]+)"', clean_json)
            strat_match = re.search(r'"one_two_punch_strategy"\s*:\s*"(.*?)"(?:\s*,\s*"\w+"|\s*})', clean_json, re.DOTALL)

            data = {
                "tweet_copy": tweet_match.group(1).strip() if tweet_match else "",
                "image_prompt": prompt_match.group(1).strip() if prompt_match else "",
                "aspect_ratio": aspect_match.group(1).strip() if aspect_match else "4:5",
                "format_type": fmt_match.group(1).strip() if fmt_match else resolved_format,
                "target_simcluster": sim_match.group(1).strip() if sim_match else resolved_simcluster,
                "one_two_punch_strategy": strat_match.group(1).strip() if strat_match else "Setup tension in tweet copy; deliver visual punchline in 4:5 image.",
            }

        raw_tweet_copy = (data.get("tweet_copy") or "").strip()
        if not raw_tweet_copy:
            raw_tweet_copy = f"The reality of {topic[:110]}."
        remediated_copy = gatekeeper.remediate_minor_issues(raw_tweet_copy)

        # Enforce < 140 chars strictly
        if len(remediated_copy) >= 140:
            truncated = remediated_copy[:136]
            last_space = truncated.rfind(" ")
            if last_space > 80:
                remediated_copy = truncated[:last_space] + "..."
            else:
                remediated_copy = truncated + "..."

        image_prompt = (data.get("image_prompt") or "").strip()
        if not image_prompt:
            image_prompt = VISUAL_FORMAT_TEMPLATES.get(resolved_format, {}).get("prompt_template", "") or f"Cinematic 4:5 visual breakdown of {topic}, dark theme, high contrast."

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
        logger.warning("Visual post spec AI generation encountered error for topic '%s': %s. Using high-signal template fallback.", topic[:50], e)
        fallback_prompt = (
            VISUAL_FORMAT_TEMPLATES.get(resolved_format, {}).get("prompt_template", "")
            or f"Cinematic 4:5 vertical visual representation of {topic}, dark aesthetic (#0D1117), ultra-clean composition, 8k realism."
        )
        return VisualPostSpec(
            tweet_copy=f"The reality of {topic[:110]}." if len(topic) <= 110 else f"{topic[:107]}...",
            image_prompt=fallback_prompt,
            aspect_ratio="4:5",
            format_type=resolved_format,
            target_simcluster=resolved_simcluster,
            one_two_punch_strategy="Setup tension in tweet copy; deliver visual punchline in 4:5 image.",
        )


__all__ = [
    "FORMAT_TYPES",
    "SIMCLUSTERS",
    "VISUAL_FORMAT_TEMPLATES",
    "VisualPostSpec",
    "infer_format_type",
    "infer_simcluster",
    "generate_visual_post_spec",
]
