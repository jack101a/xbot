from __future__ import annotations

import json
import logging
from typing import Any
from pydantic import BaseModel, Field

from .prompts import RELEVANCE_THRESHOLD, _clean_text_for_json

logger = logging.getLogger(__name__)


class TrendEvaluation(BaseModel):
    is_relevant: bool = Field(..., description="Whether story aligns with persona interests")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    reasoning: str = Field(default="", description="Why this story fits or does not fit persona niche")
    key_takeaways: list[str] = Field(default_factory=list, description="2-3 bullet point summaries")
    hot_take: str = Field(default="", description="Persona hot take / prediction / commentary")
    draft_post: str = Field(default="", description="Assembled tweet text (<280 chars)")
    optimized_post: str = Field(default="", description="Post enhanced via optimize_post_hook")
    thread_items: list[str] | None = Field(default=None, description="Multi-tweet thread breakdown (3-5 tweets) if topic warrants a thread")
    quote_hook: str | None = Field(default=None, description="Punchy hook/angle for quote-tweeting or replying to this trend")


class _TrendAnalysisResponse(BaseModel):
    is_relevant: bool = Field(..., description="Whether story aligns with persona interests")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    reasoning: str = Field(default="", description="Why this story fits or does not fit persona niche")
    key_takeaways: list[str] = Field(default_factory=list, description="2-3 bullet point summaries")
    hot_take: str = Field(default="", description="Persona hot take / prediction / commentary")
    draft_post: str = Field(default="", description="Assembled tweet text (<280 chars)")
    quote_hook: str | None = Field(default=None, description="Hook for quoting/replying to tweets about this trend")


def _assemble_draft_post(trend_title: str, key_takeaways: list[str], hot_take: str) -> str:
    """Assembles a concise draft tweet from takeaways and persona hot take."""
    lines: list[str] = []
    if key_takeaways:
        for point in key_takeaways[:3]:
            pt = point.strip()
            if pt:
                if not pt.startswith("•") and not pt.startswith("-"):
                    pt = f"• {pt}"
                lines.append(pt)
    if hot_take.strip():
        if lines:
            lines.append("")
        lines.append(hot_take.strip())
    elif trend_title.strip() and not lines:
        lines.append(trend_title.strip())

    draft = "\n".join(lines).strip()
    if len(draft) > 280:
        draft = draft[:280].strip()
    return draft


def _parse_trend_evaluation_from_json(raw_content: Any) -> TrendEvaluation | None:
    """Extracts TrendEvaluation from JSON string or dict."""
    if not raw_content or not isinstance(raw_content, str):
        return None

    try:
        cleaned = _clean_text_for_json(raw_content)
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning("Failed to decode JSON from trend generator response: %s", e)
        return None

    if not isinstance(data, dict):
        return None

    # Handle {"evaluation": {...}} or {"trend": {...}} wrapping
    for key in ("evaluation", "trend", "result"):
        if key in data and isinstance(data[key], dict):
            data = data[key]
            break

    try:
        score = float(data.get("relevance_score", 0.5))
        score = max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        score = 0.5

    raw_relevant = data.get("is_relevant")
    if isinstance(raw_relevant, str):
        is_relevant = raw_relevant.lower() in ("true", "1", "yes")
    elif isinstance(raw_relevant, bool):
        is_relevant = raw_relevant
    else:
        is_relevant = score >= RELEVANCE_THRESHOLD

    if score < RELEVANCE_THRESHOLD:
        is_relevant = False

    reasoning = str(data.get("reasoning") or "").strip()

    raw_takeaways = data.get("key_takeaways")
    key_takeaways: list[str] = []
    if isinstance(raw_takeaways, (list, tuple)):
        key_takeaways = [
            str(pt).strip()
            for pt in raw_takeaways
            if isinstance(pt, (str, int, float)) and str(pt).strip()
        ]
    elif isinstance(raw_takeaways, str) and raw_takeaways.strip():
        key_takeaways = [line.strip() for line in raw_takeaways.split("\n") if line.strip()]

    hot_take = str(data.get("hot_take") or "").strip()
    draft_post = str(data.get("draft_post") or "").strip()

    if not is_relevant:
        key_takeaways = []
        hot_take = ""
        draft_post = ""

    try:
        return TrendEvaluation(
            is_relevant=is_relevant,
            relevance_score=score,
            reasoning=reasoning,
            key_takeaways=key_takeaways,
            hot_take=hot_take,
            draft_post=draft_post,
            optimized_post="",
        )
    except Exception as e:
        logger.warning("Failed to construct TrendEvaluation model: %s", e)
        return None
