from __future__ import annotations
import json
import logging
import re
from typing import Any
from pydantic import BaseModel, Field
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.ai.formatting_engine import (
    enforce_pacing_whitespace,
    strip_formulaic_trailing_emojis,
)
from xbot.config import settings
from xbot.persona.loader import Persona
from .constants import *
from .evaluator import _detect_language_vibe, clean_text_for_json, clean_raw_reply_text
from .prompt_builder import _build_sniper_system_prompt, _build_sniper_user_prompt

logger = logging.getLogger(__name__)

from .verifier import (
    SniperResult,
    SniperReplyResult,
    DynamicReplyResult,
    QuoteTakeResult,
    verify_sniper_reply,
)

async def generate_sniper_reply(
    persona: Persona,
    target_tweet: dict[str, Any],
    preferred_angle: str | None = None,
    opportunity_score: Any | None = None,
    client: Any | None = None,
) -> SniperResult:
    """
    Generates an algorithm-optimized, high-retention sniper reply supporting 6 modalities to a target KOL tweet.
    Uses persona voice, rules, room reading, and selected angle without forcing artificial question marks.
    Enforces verification with up to 2 retries.
    """
    author = target_tweet.get("author") or target_tweet.get("handle") or "creator"
    clean_author = str(author).lstrip("@")
    target_text = target_tweet.get("text", "")
    top_comments = target_tweet.get("top_comments") or []
    lang_mode = _detect_language_vibe(target_text, top_comments)

    system_prompt = _build_sniper_system_prompt(persona, preferred_angle)
    user_prompt = _build_sniper_user_prompt(target_tweet, preferred_angle)

    # Real-Time Web Search Fact-Grounding & Verification
    try:
        from xbot.ai.fact_grounder import ground_context_with_live_facts
        grounding_block = await ground_context_with_live_facts(target_text)
        if grounding_block:
            user_prompt += f"\n\n{grounding_block}"
    except Exception as g_err:
        logger.debug("Live fact grounding lookup skipped: %s", g_err)

    model = getattr(
        settings,
        "MODEL_REPLY_ANALYSIS",
        getattr(settings, "MODEL_GENERATION", getattr(settings, "MODEL_POST_CREATION", "gemini-3.5-flash-lite")),
    )

    ai_client = client if client is not None else get_ai_client()
    chosen_default_angle = preferred_angle.lower() if preferred_angle and preferred_angle.lower() in VALID_ANGLES else "insight"

    # Multimodal Vision Payload Construction if Images Exist
    media_urls = [u for u in target_tweet.get("media_urls", []) if isinstance(u, str) and u.startswith("http")]
    if media_urls:
        vision_user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for u in media_urls[:2]:
            vision_user_content.append({
                "type": "image_url",
                "image_url": {"url": u}
            })
    else:
        vision_user_content = user_prompt

    # 1. Attempt structured parse if supported by client
    try:
        if hasattr(ai_client, "beta") and hasattr(ai_client.beta, "chat") and hasattr(ai_client.beta.chat.completions, "parse"):
            completion = await ai_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SniperResult,
            )
            parsed = completion.choices[0].message.parsed
            if isinstance(parsed, SniperResult):
                if len(parsed.reply_text) > 260:
                    parsed.reply_text = parsed.reply_text[:260].strip()
                parsed.reply_text = strip_surrounding_quotes(parsed.reply_text)
                return parsed
    except Exception as parse_err:
        logger.debug("Structured parse skipped/failed: %s", parse_err)

    # 2. Attempt standard completions with up to 3 retries and verification
    for attempt in range(3):
        try:
            try:
                completion = await ai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": vision_user_content},
                    ],
                    response_format={"type": "json_object"},
                )
            except Exception:
                completion = await ai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )

            raw_content = completion.choices[0].message.content or ""
            if not isinstance(raw_content, str):
                raw_content = str(raw_content)

            cleaned_json = clean_text_for_json(raw_content)
            data = json.loads(cleaned_json)

            if isinstance(data, dict):
                if "reply" in data and isinstance(data["reply"], dict):
                    data = data["reply"]
                elif "content" in data and isinstance(data["content"], dict):
                    data = data["content"]

                reply_text = strip_surrounding_quotes(str(data.get("reply_text") or data.get("content") or "").strip())
                response_mode = str(data.get("response_mode") or "witty_sarcasm").lower().strip()
                if response_mode not in VALID_RESPONSE_MODES:
                    response_mode = "witty_sarcasm"

                debate_catalyst = strip_surrounding_quotes(str(data.get("debate_catalyst") or "").strip())
                angle_used = str(data.get("angle") or data.get("angle_used") or chosen_default_angle).lower()
                if angle_used not in VALID_ANGLES:
                    angle_used = chosen_default_angle
                confidence = float(data.get("confidence", 1.0))
                reasoning = str(data.get("reasoning") or "")

                raw_gif = data.get("gif_query")
                gif_query = None
                if raw_gif and str(raw_gif).strip().lower() not in ("null", "none", "", "n/a", "false"):
                    gif_query = str(raw_gif).strip()

                # Verification Check
                is_valid, fail_reason = verify_sniper_reply(
                    reply_text,
                    language_mode=lang_mode,
                    target_text=target_text,
                    response_mode=response_mode,
                    gif_query=gif_query,
                )
                if not is_valid and attempt < 2:
                    logger.warning("Sniper reply verification failed on attempt %d: %s. Retrying...", attempt + 1, fail_reason)
                    user_prompt += f"\n\nPREVIOUS GENERATION FAILED VERIFICATION: {fail_reason}. Please rewrite cleanly."
                    continue

                reply_text = strip_surrounding_quotes(reply_text)
                if response_mode not in ("emoji_reaction", "pure_gif"):
                    reply_text = strip_formulaic_trailing_emojis(reply_text)
                    reply_text = enforce_pacing_whitespace(reply_text)
                reply_text = strip_surrounding_quotes(reply_text)

                if len(reply_text) > 260:
                    reply_text = reply_text[:260].strip()

                return SniperResult(
                    response_mode=response_mode,
                    reply_text=reply_text,
                    debate_catalyst=debate_catalyst,
                    angle=angle_used,
                    angle_used=angle_used,
                    gif_query=gif_query,
                    confidence=confidence,
                    reasoning=reasoning,
                )
        except Exception as e:
            logger.warning("Attempt %d failed during sniper reply generation: %s", attempt + 1, e)

    # 3. Raw text fallback check
    if 'raw_content' in locals() and raw_content:
        cleaned_raw = clean_raw_reply_text(raw_content)
        if cleaned_raw:
            if len(cleaned_raw) > 260:
                cleaned_raw = cleaned_raw[:260].strip()
            cleaned_raw = strip_surrounding_quotes(cleaned_raw)
            return SniperResult(
                response_mode="casual_take",
                reply_text=cleaned_raw,
                angle=chosen_default_angle,
                angle_used=chosen_default_angle,
                confidence=0.8,
                reasoning="Fallback parsed from raw text completion",
            )

    # 4. If all models fail/timeout after retries, discard to avoid low-quality slop
    logger.warning("All top-tier writing models exhausted for @%s. Discarding reply to retry in next session.", clean_author)
    return SniperResult(
        response_mode="witty_sarcasm",
        reply_text="",
        debate_catalyst="",
        angle=chosen_default_angle,
        angle_used=chosen_default_angle,
        gif_query=None,
        confidence=0.0,
        reasoning=f"Generation failed: All top-tier writing models failed or timed out after retries for @{clean_author}. Discarded to prevent posting low-quality output.",
    )

from .quote_generator import generate_quote_take
