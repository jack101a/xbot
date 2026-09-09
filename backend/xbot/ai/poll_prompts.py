from __future__ import annotations
import json
import logging
from typing import Any
from xbot.ai.poll_models import GeneratedPoll
from xbot.persona.prompt_engine import build_character_master_prompt

logger = logging.getLogger(__name__)

def _clean_text_for_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def _get_persona_field(obj: Any, *keys: str, default: Any = None) -> Any:
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current if current is not None else default

def _build_poll_system_prompt(persona: Any, topic: str | None = None) -> str:
    master_char_prompt = build_character_master_prompt(persona, action_type="poll") if persona else "You are an authentic creator on X (Twitter)."

    prompt_parts = [
        master_char_prompt,
        "\n=== TASK INSTRUCTIONS: NATIVE X (TWITTER) POLL ===",
        "Your mission is to generate a highly engaging, curiosity-driven interactive poll that drives votes, replies, and dwell time in your niche.\n",
    ]

    prompt_parts.append(
        "\n=== STRICT POLL CONSTRAINTS (X PLATFORM RULES) ===\n"
        "1. QUESTION: Concise, polarizing, curiosity-inducing, or debate-provoking question strictly under 200 characters (<200 chars).\n"
        "2. OPTIONS: Must have exactly 2 to 4 options (2-4 options).\n"
        "3. OPTION LENGTH: HARD LIMIT OF 25 CHARACTERS per option (max 25 chars per option). Every single option MUST be <= 25 characters.\n"
        "4. DURATION: Poll duration between 1 and 7 days (typically 1 to 3 days).\n"
        "5. CONTEXT HOOK: Optional 1-line opening hook before the poll question to frame the debate.\n"
        "6. NO HASHTAGS: Never include hashtags (#).\n"
        "7. NATURAL LOWERCASE/CASING: Sound like an authentic practitioner, not an automated survey bot."
    )
    return "\n".join(prompt_parts)

def _build_poll_user_prompt(persona: Any, topic: str | None = None) -> str:
    primary_interests = _get_persona_field(persona, "interests", "primary", default=[])
    focus = topic if topic else (primary_interests[0] if primary_interests else "software development")

    return (
        f"Generate an irresistible, debate-inducing poll for your followers about: \"{focus}\".\n\n"
        f"Output JSON Schema:\n"
        f"{{\n"
        f"  \"question\": \"Polarizing question <200 chars\",\n"
        f"  \"options\": [\"Option 1 (<=25 chars)\", \"Option 2 (<=25 chars)\"],\n"
        f"  \"duration_days\": 1,\n"
        f"  \"context_hook\": \"Optional 1-line context hook\",\n"
        f"  \"reasoning\": \"Why this poll drives debate\"\n"
        f"}}\n"
        f"Return ONLY valid JSON."
    )

def _parse_poll_from_json(raw_content: Any) -> GeneratedPoll | None:
    if not raw_content or not isinstance(raw_content, str):
        return None
    try:
        cleaned = _clean_text_for_json(raw_content)
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning("Failed to decode JSON from poll response: %s", e)
        return None

    if not isinstance(data, dict):
        return None

    if "poll" in data and isinstance(data["poll"], dict):
        data = data["poll"]

    question = str(data.get("question") or "").strip()
    if not question:
        return None
    if len(question) > 200:
        question = question[:200].strip()

    raw_options = data.get("options")
    if not isinstance(raw_options, (list, tuple)):
        return None

    cleaned_options = [
        str(opt).strip()[:25]
        for opt in raw_options
        if isinstance(opt, (str, int, float)) and str(opt).strip()
    ]
    if not (2 <= len(cleaned_options) <= 4):
        return None

    try:
        duration_days = int(data.get("duration_days", 1))
        duration_days = max(1, min(7, duration_days))
    except (ValueError, TypeError):
        duration_days = 1

    context_hook = data.get("context_hook")
    if context_hook is not None:
        context_hook = str(context_hook).strip()
        if not context_hook:
            context_hook = None

    reasoning = str(data.get("reasoning") or "").strip()

    try:
        return GeneratedPoll(
            question=question,
            options=cleaned_options,
            duration_days=duration_days,
            context_hook=context_hook,
            reasoning=reasoning,
        )
    except Exception as e:
        logger.warning("Failed to validate GeneratedPoll model: %s", e)
        return None
