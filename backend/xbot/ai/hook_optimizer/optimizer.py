from __future__ import annotations
import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.config import settings
from .constants import *
from .models import (
    OptimizedPostResult,
    _ViralHookResponse,
    HookCandidate,
    HookOptimizationResult,
    _HookGenerationResponse,
)
from .templates import (
    _build_hook_optimizer_system_prompt,
    _build_hook_optimizer_user_prompt,
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
    _normalize_candidate,
)

logger = logging.getLogger(__name__)

def _get_client_fallback():
    import sys
    mod = sys.modules.get("xbot.ai.hook_optimizer")
    if mod and hasattr(mod, "get_ai_client"):
        return mod.get_ai_client()
    return get_ai_client()


def _parse_candidates_from_json(raw_content: Any) -> list[HookCandidate]:
    """Extracts HookCandidate list from various JSON structures."""
    if not raw_content or not isinstance(raw_content, str):
        return []

    try:
        cleaned = clean_text_for_json(raw_content)
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning("Failed to decode JSON from hook optimizer response: %s", e)
        return []

    candidates: list[HookCandidate] = []

    if isinstance(data, dict):
        # Case 1: {"candidates": [...]}
        if "candidates" in data and isinstance(data["candidates"], list):
            for item in data["candidates"]:
                cand = _normalize_candidate(item)
                if cand:
                    candidates.append(cand)
        # Case 2: {"hooks": [...]}
        elif "hooks" in data and isinstance(data["hooks"], list):
            for item in data["hooks"]:
                cand = _normalize_candidate(item)
                if cand:
                    candidates.append(cand)
        # Case 3: Keyed by archetype {"curiosity_gap": {...}, "contrarian": {...}}
        else:
            for arch_key, item in data.items():
                if isinstance(item, dict):
                    cand = _normalize_candidate(item, default_archetype=arch_key)
                    if cand:
                        candidates.append(cand)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                cand = _normalize_candidate(item)
                if cand:
                    candidates.append(cand)

    return candidates

async def optimize_post_hook(
    persona: Any,
    draft_content: str,
    topic: str = "",
    client: Any | None = None,
) -> HookOptimizationResult:
    """
    Optimizes a post draft by generating and evaluating 4 hook archetypes:
    - curiosity_gap
    - contrarian
    - framework_breakdown
    - story_relatable

    Scores each on dwell retention and scroll-stopping power, selects the winning hook,
    and formats the final post with micro-spacing. Falls back safely to original content on errors.
    """
    system_prompt = _build_hook_optimizer_system_prompt(persona, topic)
    user_prompt = _build_hook_optimizer_user_prompt(draft_content, topic)

    model = getattr(
        settings,
        "MODEL_HOOK_OPTIMIZER",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    ai_client = client if client is not None else _get_client_fallback()

    first_line = draft_content.strip().split("\n")[0].strip() if draft_content.strip() else "Draft hook"
    fallback_hook = HookCandidate(
        archetype="curiosity_gap",
        hook_text=first_line[:140] if first_line else "Draft hook",
        score=5.0,
        reasoning="Default fallback hook",
    )

    try:
        # 1. Attempt structured parse via beta endpoint
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=_HookGenerationResponse,
            )
            parsed = getattr(completion.choices[0].message, "parsed", None)
            parsed_candidates = getattr(parsed, "candidates", None) if parsed is not None else None

            if parsed_candidates and isinstance(parsed_candidates, (list, tuple)):
                sanitized_candidates: list[HookCandidate] = []
                for cand in parsed_candidates:
                    if isinstance(cand, HookCandidate) or (hasattr(cand, "archetype") and hasattr(cand, "hook_text")):
                        sanitized_candidates.append(
                            HookCandidate(
                                archetype=str(cand.archetype),
                                hook_text=clean_hook_text(str(cand.hook_text)),
                                score=max(1.0, min(10.0, float(getattr(cand, "score", 5.0)))),
                                reasoning=str(getattr(cand, "reasoning", "")),
                            )
                        )
                    elif isinstance(cand, dict):
                        norm = _normalize_candidate(cand)
                        if norm:
                            sanitized_candidates.append(norm)

                if sanitized_candidates:
                    winning_hook = max(sanitized_candidates, key=lambda c: c.score)
                    optimized_content = format_optimized_post(draft_content, winning_hook.hook_text)
                    return HookOptimizationResult(
                        original_content=draft_content,
                        optimized_content=optimized_content,
                        winning_hook=winning_hook,
                        candidates=sanitized_candidates,
                    )
        except Exception as parse_err:
            logger.warning("Structured parse failed for hook optimizer, falling back: %s", parse_err)

        # 2. Fallback to standard chat completions with JSON mode
        try:
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
        except Exception:
            # Fallback without json_object mode
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        raw_content = getattr(completion.choices[0].message, "content", None)
        if isinstance(raw_content, str):
            candidates = _parse_candidates_from_json(raw_content)
        else:
            candidates = []

        if candidates:
            winning_hook = max(candidates, key=lambda c: c.score)
            optimized_content = format_optimized_post(draft_content, winning_hook.hook_text)
            return HookOptimizationResult(
                original_content=draft_content,
                optimized_content=optimized_content,
                winning_hook=winning_hook,
                candidates=candidates,
            )

        # If candidates could not be parsed from JSON, fallback safely returning original draft
        logger.warning("No valid hook candidates parsed from LLM output. Returning safe original content fallback.")
        win_cand = HookCandidate(
            archetype="curiosity_gap",
            hook_text=first_line[:140] if first_line else "Draft hook",
            score=5.0,
            reasoning="Fallback returned due to invalid JSON from LLM",
        )
        return HookOptimizationResult(
            original_content=draft_content,
            optimized_content=draft_content,
            winning_hook=win_cand,
            candidates=[win_cand],
        )

    except Exception as e:
        logger.error("Error in optimize_post_hook: %s", e)
        win_cand = HookCandidate(
            archetype="curiosity_gap",
            hook_text=first_line[:140] if first_line else "Draft hook",
            score=5.0,
            reasoning=f"Fallback returned due to API error: {e}",
        )
        return HookOptimizationResult(
            original_content=draft_content,
            optimized_content=draft_content,
            winning_hook=win_cand,
            candidates=[win_cand],
        )

from .virality_optimizer import optimize_post_for_virality
