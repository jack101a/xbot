from __future__ import annotations
import json
import logging
import re
from typing import Any
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona
from xbot.persona.prompt_engine import build_character_master_prompt
from xbot.persona.worldview_engine import build_worldview_prompt_section
from .constants import *
from .evaluator import clean_text_for_json
from .verifier import QuoteTakeResult

logger = logging.getLogger(__name__)

async def generate_quote_take(
    persona: Persona,
    target_tweet: dict[str, Any],
    client: Any | None = None,
) -> QuoteTakeResult:
    """
    Generates a viral, high-signal Quote Tweet take tailored to the full root post,
    attached visual media descriptions, and top 10 liked comments in the thread.
    """
    author = target_tweet.get("author") or target_tweet.get("handle") or "Creator"
    author = str(author).lstrip("@")
    text = target_tweet.get("text", "").strip()
    media_alts = target_tweet.get("media_alts") or []
    top_comments = target_tweet.get("top_comments") or []

    comments_formatted = ""
    for ci, c in enumerate(top_comments[:10], 1):
        if isinstance(c, dict):
            c_author = c.get("author") or "user"
            c_text = c.get("text", "").strip()
            c_likes = c.get("likes") or 0
            comments_formatted += f"{ci}. @{c_author}: \"{c_text}\" ({c_likes} likes)\n"
        else:
            comments_formatted += f"{ci}. \"{str(c).strip()}\"\n"

    media_desc_str = ", ".join(media_alts) if media_alts else "Embedded image/video media"

    import datetime
    now_dt = datetime.datetime.now().astimezone()
    date_str = now_dt.strftime("%A, %B %d, %Y")
    year_str = str(now_dt.year)

    worldview_block = build_worldview_prompt_section(
        persona,
        context_text=text,
        top_comments=top_comments,
        is_reply=True,
    )

    master_char_prompt = build_character_master_prompt(persona, action_type="quote")

    prompt = f"""=== TASK: HIGH-IMPACT QUOTE TWEET ===
You are analyzing this real live post to draft a viral, high-value QUOTE TWEET (standalone take adding a strong perspective).

=== TARGET TWEET ===
Author: @{author}
Content: "{text}"
Attached Media / Visual Details: {media_desc_str}

=== TOP 10 COMMENTS IN THE ROOM (SENTIMENT, HUMOR & DEBATE) ===
{comments_formatted if comments_formatted else 'No comments yet'}

=== PERSONA WORLDVIEW, STANCE & DIALECT DIRECTIVES ===
{worldview_block}

=== GENERATION DIRECTIVES ===
1. CONTEXT ACCURACY: Understand what the post and discussion are actually about. Speak directly to that specific topic.
2. ADD VALUE & AVOID REPETITION: Don't repeat what the original post already says. Deliver a witty take, counter-perspective, or relatable reaction.
3. ORGANIC TONE: Speak naturally like a real person on X. Avoid generic AI enthusiasm or canned corporate phrases.
4. NO LISTS OR BULLETS: Never use numbered lists (1. 2. 3.) or bullet points in a quote tweet. Keep it 1-2 punchy sentences.
5. HASHTAGS: Max of 2 hashtags, only if directly relevant to the specific topic (e.g. #OnePiece, #GTA6). Zero hashtags is preferred.
6. GIF ATTACHMENT: Provide a 1-3 word Tenor search query in `gif_query` if a reaction GIF adds punch; otherwise null.
7. PACING & LENGTH: Punchy and concise beats long and boring. Natural length suited for an X quote tweet.

Return ONLY a JSON object matching this schema:
{{
  "topic_understanding": "1-2 sentences explaining what the post, image, and room are discussing",
  "quote_text": "Your complete quote tweet take (natural length, sentence case)",
  "gif_query": "Tenor search query or null",
  "reasoning": "Brief explanation of why this perspective fits the topic"
}}
"""

    model = getattr(
        settings,
        "MODEL_REPLY_ANALYSIS",
        getattr(settings, "MODEL_GENERATION", getattr(settings, "MODEL_POST_CREATION", "gemini-3.5-flash-lite")),
    )
    ai_client = client if client is not None else get_ai_client()

    for attempt in range(3):
        try:
            resp = await ai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": master_char_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75,
                max_tokens=600,
            )
            raw = resp.choices[0].message.content or ""
            clean_json = clean_text_for_json(raw)
            data = json.loads(clean_json)

            if isinstance(data, dict):
                quote_text = strip_surrounding_quotes(str(data.get("quote_text") or data.get("content") or "").strip())
                from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper
                quote_text = AntiAIGatekeeper.enforce_max_hashtags(quote_text, max_tags=2)
                if len(quote_text) > 260:
                    quote_text = quote_text[:260].strip()

                raw_gif = data.get("gif_query")
                gif_query = None
                if raw_gif and str(raw_gif).strip().lower() not in ("null", "none", "", "n/a", "false"):
                    gif_query = str(raw_gif).strip()

                return QuoteTakeResult(
                    quote_text=quote_text,
                    gif_query=gif_query,
                    reasoning=str(data.get("reasoning") or ""),
                    topic_understanding=str(data.get("topic_understanding") or ""),
                    confidence=1.0,
                )
        except Exception as err:
            logger.warning("Attempt %d failed during quote take generation for @%s: %s", attempt + 1, author, err)

    # Discard if all writing models exhausted - NEVER post generic template text
    logger.warning("All writing models exhausted for quote take on @%s. Discarding to prevent posting generic templates.", author)
    return QuoteTakeResult(
        quote_text="",
        gif_query=None,
        reasoning="Generation failed: All writing models exhausted. Discarded to prevent posting generic templates.",
        confidence=0.0,
    )

