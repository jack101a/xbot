from __future__ import annotations

from xbot.ai.client import get_ai_client
from xbot.ai.hook_optimizer import optimize_post_hook
from .generator import generate_trend_take
from .prompts import (
    RELEVANCE_THRESHOLD,
    _build_trend_system_prompt,
    _build_trend_user_prompt,
    _clean_text_for_json,
    _get_persona_field,
)
from .synthesizer import (
    TrendEvaluation,
    _TrendAnalysisResponse,
    _assemble_draft_post,
    _parse_trend_evaluation_from_json,
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
