from __future__ import annotations
import json
import logging
import re
from typing import Any
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.config import settings
from .constants import *
from .models import OptimizedPostResult, _ViralHookResponse
from .templates import (
    _build_virality_system_prompt,
    _build_virality_user_prompt,
    _infer_archetype_from_text,
)
from .scorer import (
    extract_links,
    calculate_bookmark_score,
    trim_open_loop_hook,
    clean_text_for_json,
    clean_hook_text,
    format_optimized_post,
    _get_persona_field,
)
from .optimizer import _get_client_fallback

logger = logging.getLogger(__name__)

async def optimize_post_for_virality(
    draft: str,
    goal: str = "bookmark_and_dwell",
    persona: Any | None = None,
    client: Any | None = None,
) -> OptimizedPostResult:
    """
    Optimizes a post draft for algorithmic virality:
    1. Extracts & strips external links (isolating for 1st-reply injection).
    2. Crafts an open-loop curiosity hook strictly <100 characters before the mobile fold.
    3. Formats the body as high-utility bookmark-bait (cheat sheets, checklists, numbered steps).
    4. Evaluates bookmark utility score (1.0 to 10.0).
    5. Categorizes under 4 viral archetypes (contrarian_reversal, asymmetric_result, zero_to_hero, framework_breakdown).
    """
    clean_draft, extracted_link = extract_links(draft)
    base_bookmark_score = calculate_bookmark_score(clean_draft)

    # Separate draft into first line/paragraph vs remaining body
    lines = [line.strip() for line in clean_draft.split('\n') if line.strip()]
    first_line = lines[0] if lines else "Key insights on engineering & systems."
    remaining_body = "\n\n".join(lines[1:]) if len(lines) > 1 else ""

    fallback_hook = trim_open_loop_hook(first_line, max_len=99)
    fallback_archetype = _infer_archetype_from_text(clean_draft)

    ai_client = client if client is not None else _get_client_fallback()
    model = getattr(
        settings,
        "MODEL_HOOK_OPTIMIZER",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    system_prompt = _build_virality_system_prompt(persona, goal)
    user_prompt = _build_virality_user_prompt(clean_draft, goal)

    try:
        # 1. Structured parse attempt
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=_ViralHookResponse,
                action_type="hook_optimizer",
            )
            parsed = getattr(completion.choices[0].message, "parsed", None)
            if parsed and isinstance(parsed, _ViralHookResponse):
                hook = trim_open_loop_hook(parsed.open_loop_hook, max_len=99)
                body_clean, body_link = extract_links(parsed.clean_body or remaining_body)
                combined_link = extracted_link or body_link
                calculated_score = calculate_bookmark_score(body_clean or clean_draft)
                score = max(calculated_score, float(parsed.bookmark_score))

                return OptimizedPostResult(
                    open_loop_hook=hook,
                    bookmark_score=min(10.0, max(1.0, score)),
                    clean_body=body_clean,
                    extracted_link=combined_link,
                    archetype=parsed.archetype,
                )
        except Exception as parse_err:
            logger.debug("Structured virality parse failed, trying standard JSON mode: %s", parse_err)

        # 2. Standard JSON mode attempt
        try:
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                action_type="hook_optimizer",
            )
        except Exception:
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                action_type="hook_optimizer",
            )

        raw_content = getattr(completion.choices[0].message, "content", None)
        if isinstance(raw_content, str):
            cleaned = clean_text_for_json(raw_content)
            data = json.loads(cleaned)
            if isinstance(data, dict):
                raw_hook = str(data.get("open_loop_hook") or data.get("hook") or fallback_hook)
                hook = trim_open_loop_hook(raw_hook, max_len=99)
                raw_body = str(data.get("clean_body") or data.get("body") or remaining_body)
                body_clean, body_link = extract_links(raw_body)
                combined_link = extracted_link or body_link
                calculated_score = calculate_bookmark_score(body_clean or clean_draft)
                raw_score = float(data.get("bookmark_score", calculated_score))
                score = max(calculated_score, raw_score)
                archetype = str(data.get("archetype", fallback_archetype))

                return OptimizedPostResult(
                    open_loop_hook=hook,
                    bookmark_score=min(10.0, max(1.0, score)),
                    clean_body=body_clean,
                    extracted_link=combined_link,
                    archetype=archetype,
                )
    except Exception as e:
        logger.warning("Virality optimization model call failed: %s. Returning clean heuristic result.", e)

    # 3. Offline Heuristic Fallback
    return OptimizedPostResult(
        open_loop_hook=fallback_hook,
        bookmark_score=base_bookmark_score,
        clean_body=remaining_body,
        extracted_link=extracted_link,
        archetype=fallback_archetype,
    )

