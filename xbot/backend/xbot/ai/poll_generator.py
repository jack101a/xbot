from __future__ import annotations

import json
import logging
import re
from typing import Any
from pydantic import BaseModel, Field, field_validator

from xbot.ai.client import get_ai_client
from xbot.config import settings

logger = logging.getLogger(__name__)


class GeneratedPoll(BaseModel):
    question: str = Field(..., max_length=200, description="Engaging poll question (<200 chars)")
    options: list[str] = Field(..., min_length=2, max_length=4, description="2 to 4 options, each max 25 chars")
    duration_days: int = Field(default=1, ge=1, le=7, description="Poll duration in days (1 to 7)")
    context_hook: str | None = Field(default=None, description="Optional opening hook before question")
    reasoning: str = Field(default="", description="Strategic reasoning for why this poll drives debate")

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[str]) -> list[str]:
        cleaned = [opt.strip()[:25] for opt in v if isinstance(opt, str) and opt.strip()]
        if not (2 <= len(cleaned) <= 4):
            raise ValueError("Poll must have between 2 and 4 options")
        # Ensure each option is <= 25 chars (X limitation)
        return cleaned


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


def _build_poll_system_prompt(persona: Any, topic: str | None = None) -> str:
    """Builds the system prompt for native X poll generation."""
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
    always_rules = _get_persona_field(persona, "rules", "always", default=[])
    never_rules = _get_persona_field(persona, "rules", "never", default=[])
    system_prompt = _get_persona_field(persona, "system_prompt", default="")

    prompt_parts = [
        f"You are {display_name} (@{x_handle}). You are an expert at creating viral, debate-provoking Native X (Twitter) polls.",
        "Your mission is to generate a highly engaging, curiosity-driven poll that drives votes, replies, and dwell time in your niche.\n",
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
        "\n=== STRICT POLL CONSTRAINTS (X PLATFORM RULES) ===\n"
        "1. QUESTION: Concise, polarizing, curiosity-inducing, or debate-provoking question strictly under 200 characters (<200 chars).\n"
        "2. OPTIONS: Must have exactly 2 to 4 options (2-4 options).\n"
        "3. OPTION LENGTH: HARD LIMIT OF 25 CHARACTERS per option (max 25 chars per option). Every single option MUST be <= 25 characters.\n"
        "4. DURATION: Poll duration between 1 and 7 days (typically 1 to 3 days).\n"
        "5. CONTEXT HOOK: Optional 1-line opening hook before the poll question to frame the debate.\n"
        "6. NO HASHTAGS: Never include hashtags (#).\n"
        "7. ZERO AI FLUFF: Avoid generic openers like 'Let's dive in', 'What do you think?', 'Quick question for the community'."
    )

    if topic:
        prompt_parts.append(f"\nFOCUS TOPIC: {topic}")

    return "\n".join(prompt_parts)


def _build_poll_user_prompt(persona: Any, topic: str | None = None) -> str:
    """Builds the user prompt for poll generation."""
    primary_interests = _get_persona_field(persona, "interests", "primary", default=[])
    default_niche = primary_interests[0] if primary_interests and isinstance(primary_interests, list) else "software engineering and technology"
    focus_topic = topic or default_niche

    return (
        f"Target Topic / Niche: {focus_topic}\n\n"
        f"Generate a polarizing, high-engagement Native X poll about this topic.\n"
        f"Requirements:\n"
        f"- question: Clear, provocative question (<200 characters)\n"
        f"- options: 2 to 4 options, each strictly under 25 characters (<= 25 chars)\n"
        f"- duration_days: Integer from 1 to 7 (default 1)\n"
        f"- context_hook: Optional punchy 1-line hook or null\n"
        f"- reasoning: Brief strategic rationale for why this drives votes & discussion\n\n"
        f"Return a JSON object matching this schema:\n"
        f"{{\n"
        f"  \"question\": \"Which database bottleneck causes the most production outages?\",\n"
        f"  \"options\": [\n"
        f"    \"Index bloat\",\n"
        f"    \"Replication lag\",\n"
        f"    \"Connection spikes\",\n"
        f"    \"Lock contention\"\n"
        f"  ],\n"
        f"  \"duration_days\": 1,\n"
        f"  \"context_hook\": \"Stateful scaling is always a headache.\",\n"
        f"  \"reasoning\": \"Sparks strong opinions on backend architecture pain points.\"\n"
        f"}}\n"
        f"Return ONLY valid JSON with no surrounding text."
    )


def _parse_poll_from_json(raw_content: Any) -> GeneratedPoll | None:
    """Extracts GeneratedPoll from JSON string or dict."""
    if not raw_content or not isinstance(raw_content, str):
        return None

    try:
        cleaned = _clean_text_for_json(raw_content)
        data = json.loads(cleaned)
    except Exception as e:
        logger.warning("Failed to decode JSON from poll generator response: %s", e)
        return None

    if not isinstance(data, dict):
        return None

    # Handle {"poll": {...}} wrapping
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


def _generate_fallback_poll(persona: Any, topic: str | None = None, reason: str = "Fallback") -> GeneratedPoll:
    """Generates a safe, high-quality default poll when LLM call fails."""
    primary_interests = _get_persona_field(persona, "interests", "primary", default=[])
    interest = topic or (
        primary_interests[0]
        if primary_interests and isinstance(primary_interests, list)
        else "software architecture"
    )
    
    question = f"What's the hardest part of scaling {interest}?"
    if len(question) > 200:
        question = question[:200]

    return GeneratedPoll(
        question=question,
        options=["Architecture design", "Performance & latency", "Operational cost", "Team alignment"],
        duration_days=1,
        context_hook=f"Real talk about {interest}:",
        reasoning=f"Default fallback poll generated due to: {reason}",
    )


async def generate_poll(
    persona: Any,
    topic: str | None = None,
    client: Any | None = None,
) -> GeneratedPoll:
    """
    Generates a high-engagement, debate-provoking Native X poll tailored to the persona's voice and niche.

    Enforces strict X platform limits (2-4 options, each <=25 chars, question <200 chars).
    Uses multi-tier LLM parsing with safe fallback.
    """
    system_prompt = _build_poll_system_prompt(persona, topic)
    user_prompt = _build_poll_user_prompt(persona, topic)

    model = getattr(
        settings,
        "MODEL_POLL_GENERATOR",
        getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b"),
    )

    ai_client = client if client is not None else get_ai_client()

    try:
        # 1. Attempt structured parse via beta endpoint
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=GeneratedPoll,
            )
            parsed = getattr(completion.choices[0].message, "parsed", None)
            if isinstance(parsed, GeneratedPoll):
                return parsed
            elif isinstance(parsed, dict):
                poll = _parse_poll_from_json(json.dumps(parsed))
                if poll:
                    return poll
        except Exception as parse_err:
            logger.warning("Structured parse failed for poll generator, falling back: %s", parse_err)

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
            poll = _parse_poll_from_json(raw_content)
            if poll:
                return poll

        logger.warning("Could not parse valid poll from LLM output. Using fallback poll.")
        return _generate_fallback_poll(persona, topic, reason="Unparseable LLM output")

    except Exception as e:
        logger.error("Error in generate_poll: %s", e)
        return _generate_fallback_poll(persona, topic, reason=str(e))
