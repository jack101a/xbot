from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

VALID_ANGLES = {"contrarian", "framework", "witty", "data", "insight"}


class SniperReplyResult(BaseModel):
    reply_text: str = Field(..., description="The drafted high-value reply text (< 280 chars)")
    angle_used: str = Field(..., description="The angle chosen: contrarian, framework, witty, data, or insight")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Brief explanation of the chosen angle")


def clean_text_for_json(text: str) -> str:
    """Clean markdown json wrappers from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def clean_raw_reply_text(text: str) -> str:
    """Cleans raw text output when JSON parsing fails."""
    text = clean_text_for_json(text).strip()
    # Remove leading quotes or formatting
    text = re.sub(r'^(?:Reply|Draft|Tweet|Response):\s*', '', text, flags=re.IGNORECASE)
    text = text.strip().strip('"\'`')
    return text.strip()


def _build_sniper_system_prompt(persona: Persona, preferred_angle: str | None = None) -> str:
    """Constructs the high-retention sniper system prompt."""
    prompt_parts = [
        f"You are {persona.display_name} (@{persona.x_handle}). You are executing a high-impact Sniper Reply on X.",
        "Your goal is to draft an immediate, high-value, high-retention reply to a target Key Opinion Leader (KOL) post.",
        "You want your reply to command attention, earn organic engagement, and trigger replies from the author and audience.\n",
        "=== CHARACTER IDENTITY & VOICE ===",
        f"Background: {persona.identity.background}",
    ]

    if getattr(persona.identity, "occupation", None):
        prompt_parts.append(f"Occupation: {persona.identity.occupation}")

    prompt_parts.append(f"Personality Traits: {', '.join(persona.personality.traits)}")
    prompt_parts.append(f"Communication Style: {persona.personality.communication_style}")
    prompt_parts.append(f"Tone: {persona.writing_style.tone}")

    if persona.writing_style.formatting:
        prompt_parts.append("Formatting Rules:\n" + "\n".join(f"- {fmt}" for fmt in persona.writing_style.formatting))

    if persona.writing_style.examples:
        prompt_parts.append("Voice Examples:\n" + "\n".join(f"- \"{ex}\"" for ex in persona.writing_style.examples[:3]))

    if persona.interests.primary:
        prompt_parts.append(f"Primary Interests: {', '.join(persona.interests.primary)}")

    if persona.rules.always:
        prompt_parts.append("Always Rules:\n" + "\n".join(f"- {r}" for r in persona.rules.always))

    if persona.rules.never:
        prompt_parts.append("Never Rules:\n" + "\n".join(f"- {r}" for r in persona.rules.never))

    if getattr(persona, "system_prompt", None):
        prompt_parts.append("\n=== CUSTOM MASTER PROMPT ===")
        prompt_parts.append(persona.system_prompt)

    prompt_parts.append(
        "\n=== X ALGORITHM & RETENTION OPTIMIZATION RULES ===\n"
        "1. HIGH DWELL TIME & CATALYST: Provide immediate insight, unique angle, or punchline that makes the reader stop scrolling.\n"
        "2. CONCISE LENGTH: Strictly under 240 characters (hard limit 280 characters) so the entire reply is visible on mobile without 'Show more' truncation.\n"
        "3. ANTI-BOT / ZERO CLICHÉS: NEVER use generic praise or filler like 'Great post!', '100% agree!', 'Awesome thread!', 'So true!', 'Interesting thoughts!'.\n"
        "4. NO HASHTAGS: Never include hashtags (#).\n"
        "5. AUTHENTIC PERSONA: Stay 100% in your unique persona voice and domain perspective."
    )

    prompt_parts.append(
        "\n=== HIGH-IMPACT REPLY ANGLES ===\n"
        "- contrarian: Respectfully challenge the core premise with a crisp, logical counter-example or alternative viewpoint.\n"
        "- framework: Distill the topic into a concise, actionable mental model or 2-3 point framework.\n"
        "- witty: Deliver a sharp, clever insider observation or relatable punchline in character.\n"
        "- data: Supply a concrete data point, metric, historical precedent, or empirical nuance.\n"
        "- insight: Provide profound domain depth, first-principles analysis, or unique tactical insight."
    )

    if preferred_angle and preferred_angle.lower() in VALID_ANGLES:
        prompt_parts.append(
            f"\nTARGET ANGLE: Use the '{preferred_angle.lower()}' angle for this reply."
        )
    else:
        prompt_parts.append(
            "\nTARGET ANGLE: Auto-select the most impactful angle among (contrarian, framework, witty, data, insight) "
            "that best matches your persona expertise and the target tweet content."
        )

    return "\n".join(prompt_parts)


def _build_sniper_user_prompt(target_tweet: dict[str, Any], preferred_angle: str | None = None) -> str:
    """Constructs the user prompt containing target tweet details and schema instructions."""
    author = target_tweet.get("author") or target_tweet.get("handle") or target_tweet.get("author_handle") or "KOL"
    author = str(author).lstrip("@")
    text = target_tweet.get("text", "").strip()

    prompt = (
        f"Target Tweet to Reply To:\n"
        f"Author: @{author}\n"
        f"Tweet Content: \"{text}\"\n\n"
        f"Craft a high-retention sniper reply adhering to your persona voice and algorithm rules.\n"
    )

    if preferred_angle and preferred_angle.lower() in VALID_ANGLES:
        prompt += f"Guide your response using the '{preferred_angle.lower()}' angle.\n"
    else:
        prompt += "Select the best angle: 'contrarian', 'framework', 'witty', 'data', or 'insight'.\n"

    prompt += (
        "\nReturn a JSON object with this exact schema:\n"
        "{\n"
        "  \"reply_text\": \"Your concise reply text (< 240 chars, max 280 chars, no hashtags)\",\n"
        "  \"angle_used\": \"contrarian | framework | witty | data | insight\",\n"
        "  \"confidence\": 0.0-1.0,\n"
        "  \"reasoning\": \"Brief explanation of the chosen angle and why it works\"\n"
        "}\n"
        "Return ONLY the valid JSON object with no surrounding commentary."
    )
    return prompt


async def generate_sniper_reply(
    persona: Persona,
    target_tweet: dict[str, Any],
    preferred_angle: str | None = None,
    client: Any | None = None,
) -> SniperReplyResult:
    """
    Generates an algorithm-optimized, high-retention sniper reply to a target KOL tweet.
    Uses persona voice, rules, and selected angle (contrarian, framework, witty, data, insight).
    """
    system_prompt = _build_sniper_system_prompt(persona, preferred_angle)
    user_prompt = _build_sniper_user_prompt(target_tweet, preferred_angle)

    model = getattr(
        settings,
        "MODEL_REPLY_ANALYSIS",
        getattr(settings, "MODEL_GENERATION", getattr(settings, "MODEL_POST_CREATION", "litellm/deepseek-v4-flash")),
    )

    ai_client = client if client is not None else get_ai_client()

    chosen_default_angle = preferred_angle.lower() if preferred_angle and preferred_angle.lower() in VALID_ANGLES else "insight"

    try:
        # 1. Attempt structured parse via beta endpoint
        try:
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SniperReplyResult,
            )
            parsed = completion.choices[0].message.parsed
            if isinstance(parsed, SniperReplyResult):
                # Ensure length constraint
                if len(parsed.reply_text) > 280:
                    parsed.reply_text = parsed.reply_text[:280].strip()
                return parsed
        except Exception as parse_err:
            logger.warning("Structured parse failed for sniper reply, falling back to JSON create: %s", parse_err)

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
            # Final fallback without response_format if json_object mode not supported
            completion = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

        raw_content = completion.choices[0].message.content or ""
        cleaned_json = clean_text_for_json(raw_content)

        try:
            data = json.loads(cleaned_json)
            if isinstance(data, dict):
                # Check for wrapped structures
                if "reply" in data and isinstance(data["reply"], dict):
                    data = data["reply"]
                elif "content" in data and isinstance(data["content"], dict):
                    data = data["content"]

                reply_text = str(data.get("reply_text") or data.get("content") or "").strip()
                angle_used = str(data.get("angle_used") or chosen_default_angle).lower()
                if angle_used not in VALID_ANGLES:
                    angle_used = chosen_default_angle
                confidence = float(data.get("confidence", 1.0))
                confidence = max(0.0, min(1.0, confidence))
                reasoning = str(data.get("reasoning") or "")

                if len(reply_text) > 280:
                    reply_text = reply_text[:280].strip()

                return SniperReplyResult(
                    reply_text=reply_text,
                    angle_used=angle_used,
                    confidence=confidence,
                    reasoning=reasoning,
                )
        except (json.JSONDecodeError, ValueError, TypeError) as json_err:
            logger.warning("JSON decoding failed for sniper reply: %s. Using raw text fallback.", json_err)

        # 3. Raw text fallback
        cleaned_raw = clean_raw_reply_text(raw_content)
        if len(cleaned_raw) > 280:
            cleaned_raw = cleaned_raw[:280].strip()

        return SniperReplyResult(
            reply_text=cleaned_raw,
            angle_used=chosen_default_angle,
            confidence=0.8 if cleaned_raw else 0.0,
            reasoning="Fallback parsed from raw text completion",
        )

    except Exception as e:
        logger.error("Error in generate_sniper_reply: %s", e)
        # Construct an in-character fallback response based on angle
        if chosen_default_angle == "contrarian":
            fallback_text = "The bigger bottleneck isn't the scale itself, but how state and verification loops are maintained across sessions."
        elif chosen_default_angle == "framework":
            fallback_text = "Key pattern here:\n1. Isolate execution context\n2. Keep verification loops deterministic\n3. Reduce context drift"
        elif chosen_default_angle == "witty":
            fallback_text = "Funny how every autonomous agent demo looks like magic until you give it a real production database."
        elif chosen_default_angle == "data":
            fallback_text = "Data shows over 80% of agent failure modes trace back to context compaction errors rather than raw model capabilities."
        else:
            fallback_text = "High signal insight. The core differentiator in production agents is deterministic state management."

        return SniperReplyResult(
            reply_text=fallback_text,
            angle_used=chosen_default_angle,
            confidence=0.0,
            reasoning=f"Offline heuristic fallback generated due to API issue: {e}",
        )
