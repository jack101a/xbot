from __future__ import annotations

import json
import logging
import re
from typing import Any
from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.ai.hook_optimizer import optimize_post_hook
from xbot.ai.trend_radar import TrendItem
from xbot.config import settings

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.65


class TrendEvaluation(BaseModel):
    is_relevant: bool = Field(..., description="Whether story aligns with persona interests")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    reasoning: str = Field(default="", description="Why this story fits or does not fit persona niche")
    key_takeaways: list[str] = Field(default_factory=list, description="2-3 bullet point summaries")
    hot_take: str = Field(default="", description="Persona hot take / prediction / commentary")
    draft_post: str = Field(default="", description="Assembled tweet text (<280 chars)")
    optimized_post: str = Field(default="", description="Post enhanced via optimize_post_hook")


class _TrendAnalysisResponse(BaseModel):
    is_relevant: bool = Field(..., description="Whether story aligns with persona interests")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Relevance score (0.0 to 1.0)")
    reasoning: str = Field(default="", description="Why this story fits or does not fit persona niche")
    key_takeaways: list[str] = Field(default_factory=list, description="2-3 bullet point summaries")
    hot_take: str = Field(default="", description="Persona hot take / prediction / commentary")
    draft_post: str = Field(default="", description="Assembled tweet text (<280 chars)")


def _clean_text_for_json(text: str) -> str:
    """Clean markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _get_persona_field(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safely extracts nested field from persona object or dict."""
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current if current is not None else default


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


def _build_trend_system_prompt(persona: Any) -> str:
    """Builds the system prompt for trend relevance filtering and take generation."""
    display_name = _get_persona_field(persona, "display_name", default="Autonomous Creator")
    x_handle = _get_persona_field(persona, "x_handle", default="creator")
    background = _get_persona_field(persona, "identity", "background", default="")
    occupation = _get_persona_field(persona, "identity", "occupation", default="")
    traits = _get_persona_field(persona, "personality", "traits", default=[])
    comm_style = _get_persona_field(persona, "personality", "communication_style", default="")
    tone = _get_persona_field(persona, "writing_style", "tone", default="sharp, authentic, insightful")
    formatting = _get_persona_field(persona, "writing_style", "formatting", default=[])
    examples = _get_persona_field(persona, "writing_style", "examples", default=[])
    primary_interests = _get_persona_field(persona, "interests", "primary", default=[])
    secondary_interests = _get_persona_field(persona, "interests", "secondary", default=[])
    will_not_discuss = _get_persona_field(persona, "interests", "will_not_discuss", default=[])
    always_rules = _get_persona_field(persona, "rules", "always", default=[])
    never_rules = _get_persona_field(persona, "rules", "never", default=[])
    system_prompt = _get_persona_field(persona, "system_prompt", default="")

    prompt_parts = [
        f"You are {display_name} (@{x_handle}). You are an elite domain expert and content strategist.",
        "Your mission is to evaluate incoming industry news and trending stories, filter for relevance to your niche, and generate high-impact breaking takes for X (Twitter).\n",
        "=== CHARACTER IDENTITY & VOICE ===",
    ]

    if background:
        prompt_parts.append(f"Background: {background}")
    if occupation:
        prompt_parts.append(f"Occupation: {occupation}")
    if traits:
        prompt_parts.append(f"Personality Traits: {', '.join(traits)}")
    if comm_style:
        prompt_parts.append(f"Communication Style: {comm_style}")
    if tone:
        prompt_parts.append(f"Tone: {tone}")
    if primary_interests:
        prompt_parts.append(f"Primary Niche / Interests: {', '.join(primary_interests)}")
    if secondary_interests:
        prompt_parts.append(f"Secondary Interests: {', '.join(secondary_interests)}")
    if will_not_discuss:
        prompt_parts.append(f"Taboo Topics (Strictly Skip): {', '.join(will_not_discuss)}")
    if formatting:
        prompt_parts.append("Formatting Rules:\n" + "\n".join(f"- {fmt}" for fmt in formatting))
    if examples:
        prompt_parts.append("Voice Examples:\n" + "\n".join(f"- \"{ex}\"" for ex in examples[:3]))
    if always_rules:
        prompt_parts.append("Always Rules:\n" + "\n".join(f"- {r}" for r in always_rules))
    if never_rules:
        prompt_parts.append("Never Rules:\n" + "\n".join(f"- {r}" for r in never_rules))
    if system_prompt:
        prompt_parts.append(f"\n=== CUSTOM MASTER PROMPT ===\n{system_prompt}")

    prompt_parts.append(
        "\n=== EVALUATION & TAKE GENERATION RULES ===\n"
        "1. RELEVANCE SCORING (0.0 to 1.0): Score how strongly this story aligns with your core domain and audience.\n"
        f"   - Score >= {RELEVANCE_THRESHOLD} => is_relevant = true\n"
        f"   - Score < {RELEVANCE_THRESHOLD} or taboo topics => is_relevant = false\n"
        "2. IF NOT RELEVANT: Return is_relevant=false, score, brief reasoning, and empty takeaways/draft.\n"
        "3. IF RELEVANT:\n"
        "   - key_takeaways: 2-3 concise, high-density bullet points summarizing the core development.\n"
        "   - hot_take: 1 punchy, contrarian, authoritative, or witty opinion/implication in your authentic persona voice.\n"
        "   - draft_post: A complete, ready-to-post tweet strictly under 280 characters (<280 chars).\n"
        "4. ZERO AI FLUFF: Strictly forbidden: 'Let\\'s dive in', 'In this thread', 'Game changer', 'Unpack', 'Buckle up', or generic buzzwords.\n"
        "5. NO HASHTAGS: Never include hashtags (#)."
    )

    return "\n".join(prompt_parts)


def _build_trend_user_prompt(persona: Any, trend_item: TrendItem) -> str:
    """Builds the user prompt evaluating a specific trend item."""
    primary_interests = _get_persona_field(persona, "interests", "primary", default=[])
    taboos = _get_persona_field(persona, "interests", "will_not_discuss", default=[])

    return (
        f"Headline: {trend_item.title}\n"
        f"Summary: {trend_item.summary}\n"
        f"Source: {trend_item.source_name} ({trend_item.source_url})\n\n"
        f"Persona Core Niches: {', '.join(primary_interests) if primary_interests else 'Technology'}\n"
        f"Persona Taboos: {', '.join(taboos) if taboos else 'None'}\n\n"
        f"Analyze this news item against the persona niche.\n"
        f"Return a JSON object matching this schema:\n"
        f"{{\n"
        f"  \"is_relevant\": true,\n"
        f"  \"relevance_score\": 0.88,\n"
        f"  \"reasoning\": \"Why this story fits or does not fit the persona niche\",\n"
        f"  \"key_takeaways\": [\n"
        f"    \"Core bullet point 1\",\n"
        f"    \"Core bullet point 2\"\n"
        f"  ],\n"
        f"  \"hot_take\": \"Persona opinion, contrarian view, or prediction\",\n"
        f"  \"draft_post\": \"Assembled post text under 280 chars\"\n"
        f"}}\n"
        f"Return ONLY valid JSON with no surrounding text."
    )


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

    model = getattr(
        settings,
        "MODEL_TREND_ANALYSIS",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    ai_client = client if client is not None else get_ai_client()

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
                evaluation = _parse_trend_evaluation_from_json(raw_content)

        # If LLM response could not be parsed, return safe non-relevant evaluation
        if evaluation is None:
            logger.warning("Could not parse valid trend evaluation from LLM output.")
            return TrendEvaluation(
                is_relevant=False,
                relevance_score=0.0,
                reasoning="Failed to parse LLM evaluation output",
            )

        # If not relevant, return early without hook optimization
        if not evaluation.is_relevant:
            return evaluation

        # If relevant, ensure draft_post is present
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
            hook_result = await optimize_post_hook(
                persona=persona,
                draft_content=evaluation.draft_post,
                topic=trend_item.title,
                client=ai_client,
            )
            evaluation.optimized_post = hook_result.optimized_content
        except Exception as hook_err:
            logger.warning("optimize_post_hook failed for trend take: %s", hook_err)
            evaluation.optimized_post = evaluation.draft_post

        return evaluation

    except Exception as e:
        logger.error("Error in generate_trend_take: %s", e)
        return TrendEvaluation(
            is_relevant=False,
            relevance_score=0.0,
            reasoning=f"Error evaluating trend item: {e}",
        )
