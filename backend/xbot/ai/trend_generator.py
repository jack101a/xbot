from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.ai.trend_gen import (
    RELEVANCE_THRESHOLD,
    TrendEvaluation,
    _TrendAnalysisResponse,
    _assemble_draft_post,
    _build_trend_system_prompt,
    _build_trend_user_prompt,
    _clean_text_for_json,
    _get_persona_field,
    _parse_trend_evaluation_from_json,
    generate_trend_take,
    get_ai_client,
    optimize_post_hook,
)

__all__ = [
    "RELEVANCE_THRESHOLD",
    "TrendEvaluation",
    "_TrendAnalysisResponse",
    "_clean_text_for_json",
    "_get_persona_field",
    "_assemble_draft_post",
    "_build_trend_system_prompt",
    "_build_trend_user_prompt",
    "_parse_trend_evaluation_from_json",
    "generate_trend_take",
    "get_ai_client",
    "optimize_post_hook",
]
