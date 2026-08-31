from __future__ import annotations

import json
import logging
from typing import Any

from xbot.ai.client import get_ai_client
from xbot.ai.hook_optimizer import optimize_post_hook
from xbot.ai.trend_radar import TrendItem
from xbot.config import settings

from .prompts import (
    RELEVANCE_THRESHOLD,
    _build_trend_system_prompt,
    _build_trend_user_prompt,
)
from .synthesizer import (
    TrendEvaluation,
    _TrendAnalysisResponse,
    _assemble_draft_post,
    _parse_trend_evaluation_from_json,
)

logger = logging.getLogger(__name__)


def _get_deps() -> tuple[Any, Any]:
    import sys
    _client_fn = get_ai_client
    _hook_fn = optimize_post_hook

    mod_tgen = sys.modules.get("xbot.ai.trend_gen")
    if mod_tgen:
        if hasattr(mod_tgen, "get_ai_client") and getattr(mod_tgen, "get_ai_client") is not get_ai_client:
            _client_fn = getattr(mod_tgen, "get_ai_client")
        if hasattr(mod_tgen, "optimize_post_hook") and getattr(mod_tgen, "optimize_post_hook") is not optimize_post_hook:
            _hook_fn = getattr(mod_tgen, "optimize_post_hook")

    mod_tg = sys.modules.get("xbot.ai.trend_generator")
    if mod_tg:
        if hasattr(mod_tg, "get_ai_client") and getattr(mod_tg, "get_ai_client") is not get_ai_client:
            _client_fn = getattr(mod_tg, "get_ai_client")
        if hasattr(mod_tg, "optimize_post_hook") and getattr(mod_tg, "optimize_post_hook") is not optimize_post_hook:
            _hook_fn = getattr(mod_tg, "optimize_post_hook")

    return _client_fn, _hook_fn



async def generate_trend_take(
    persona: Any,
    trend_item: TrendItem,
    client: Any | None = None,
) -> TrendEvaluation:
    """
    Evaluates a trend or news item against a persona's niche and writes an authoritative take.

    1. Evaluates relevance score (0.0 to 1.0) and determines if >= 0.65.
    2. If relevant:
       - Extracts 2-3 key takeaways.
       - Generates a persona hot take.
       - Assembles draft post (<280 chars).
       - Runs draft through optimize_post_hook to produce winning hook & formatted post.
    3. Multi-tier LLM parsing (OpenAI beta parse -> JSON object mode -> raw JSON fallback).
    4. Safe error fallback on failures.
    """
    system_prompt = _build_trend_system_prompt(persona)
    user_prompt = _build_trend_user_prompt(persona, trend_item)

    # Real-Time Web Search Fact-Grounding & Verification
    try:
        from xbot.ai.fact_grounder import ground_context_with_live_facts
        grounding_block = await ground_context_with_live_facts(f"{trend_item.title} {trend_item.summary}")
        if grounding_block:
            user_prompt += f"\n\n{grounding_block}"
    except Exception as g_err:
        logger.debug("Trend live fact grounding skipped: %s", g_err)

    model = getattr(
        settings,
        "MODEL_TREND_ANALYSIS",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    client_fn, hook_fn = _get_deps()
    ai_client = client if client is not None else client_fn()

    try:
        evaluation: TrendEvaluation | None = None

        # 1. Attempt structured parse via beta endpoint
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=_TrendAnalysisResponse,
                action_type="trend_analysis",
            )
            parsed = getattr(completion.choices[0].message, "parsed", None)
            if isinstance(parsed, _TrendAnalysisResponse):
                score = max(0.0, min(1.0, float(parsed.relevance_score)))
                is_relevant = bool(parsed.is_relevant and score >= RELEVANCE_THRESHOLD)
                evaluation = TrendEvaluation(
                    is_relevant=is_relevant,
                    relevance_score=score,
                    reasoning=parsed.reasoning,
                    key_takeaways=parsed.key_takeaways if is_relevant else [],
                    hot_take=parsed.hot_take if is_relevant else "",
                    draft_post=parsed.draft_post if is_relevant else "",
                    optimized_post="",
                )
            elif isinstance(parsed, dict):
                evaluation = _parse_trend_evaluation_from_json(json.dumps(parsed))
        except Exception as parse_err:
            logger.warning("Structured parse failed for trend generator, falling back: %s", parse_err)

        # 2. Fallback to standard chat completions with JSON mode
        if evaluation is None:
            try:
                completion = await ai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    action_type="trend_analysis",
                )
            except Exception:
                completion = await ai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    action_type="trend_analysis",
                )

            raw_content = getattr(completion.choices[0].message, "content", None)
            if isinstance(raw_content, str):
                evaluation = _parse_trend_evaluation_from_json(raw_content)

        if evaluation is None:
            logger.warning("Could not parse valid trend evaluation from LLM output.")
            return TrendEvaluation(
                is_relevant=False,
                relevance_score=0.0,
                reasoning="Failed to parse LLM evaluation output",
            )

        if not evaluation.is_relevant:
            return evaluation

        draft = evaluation.draft_post.strip()
        if not draft:
            draft = _assemble_draft_post(
                trend_item.title,
                evaluation.key_takeaways,
                evaluation.hot_take,
            )
            evaluation.draft_post = draft

        # Optimize post hook
        try:
            hook_result = await hook_fn(
                persona=persona,
                draft_content=evaluation.draft_post,
                topic=trend_item.title,
                client=ai_client,
            )
            evaluation.optimized_post = hook_result.optimized_content
        except Exception as hook_err:
            logger.warning("optimize_post_hook failed for trend take: %s", hook_err)
            evaluation.optimized_post = evaluation.draft_post

        # Multi-Tweet Thread Synthesis for high-relevance trends
        try:
            from xbot.ai.thread_generator import generate_thread
            thread_archetype = "Contrarian Breakdown" if any(w in trend_item.title.lower() for w in ["controversy", "backlash", "pulled", "ban", "debate"]) else "Framework"
            thread_res = await generate_thread(
                topic=f"{trend_item.title} - {trend_item.summary}",
                persona=persona,
                num_tweets=4,
                archetype=thread_archetype,
                deep_research=False,
                client=ai_client,
            )
            if thread_res and thread_res.tweets:
                evaluation.thread_items = thread_res.tweets
        except Exception as th_err:
            logger.debug("Thread generation skipped for trend '%s': %s", trend_item.title[:40], th_err)

        return evaluation

    except Exception as e:
        logger.error("Error in generate_trend_take: %s", e)
        return TrendEvaluation(
            is_relevant=False,
            relevance_score=0.0,
            reasoning=f"Error evaluating trend item: {e}",
        )
