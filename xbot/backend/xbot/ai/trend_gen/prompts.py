from __future__ import annotations

import logging
from typing import Any
from xbot.ai.trend_radar import TrendItem

logger = logging.getLogger(__name__)

RELEVANCE_THRESHOLD = 0.65


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
        "1. HIGH-RELEVANCE DOMAINS: Cinema/OTT releases, Hollywood/global film buzz, director announcements, consumer tech & AI developments, internet viral debates, creator culture, anime/manga, and gaming are HIGHLY RELEVANT core topics.\n"
        "2. TABOO DEFINITION: ONLY partisan electoral politics is banned. Cultural debates and entertainment/tech news are 100% encouraged!\n"
        "3. RELEVANCE SCORING (0.0 to 1.0): Score how strongly this story aligns with your persona and audience.\n"
        f"   - Score >= {RELEVANCE_THRESHOLD} => is_relevant = true\n"
        f"   - Score < {RELEVANCE_THRESHOLD} or electoral politics => is_relevant = false\n"
        "4. IF NOT RELEVANT: Return is_relevant=false, score, brief reasoning, and empty takeaways/draft.\n"
        "5. IF RELEVANT:\n"
        "   - key_takeaways: 2-3 concise, high-density bullet points summarizing the core development.\n"
        "   - hot_take: 1 punchy, contrarian, authoritative, or witty opinion/implication in your authentic persona voice.\n"
        "   - draft_post: A complete, ready-to-post tweet strictly under 280 characters (<280 chars).\n"
        "   - quote_hook: A sharp opening line for quote-tweeting or replying to other tweets on this trend.\n"
        "6. ZERO AI FLUFF: Strictly forbidden: 'Let\\'s dive in', 'In this thread', 'Game changer', 'Unpack', 'Buckle up', 'delve', 'tapestry', or generic buzzwords.\n"
        "7. AUTHENTIC HASHTAGS: Max 1-2 authentic, relevant hashtags at the very end of standalone posts if natural (e.g. #Cinema, #Tech, #AI), or 0 hashtags.\n"
        "8. EXPLICIT SUBJECT CONTEXT: Always explicitly name the movie, project, product, brand, or subject from the trend in the post text so followers immediately know what you are talking about."
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
