from __future__ import annotations
import json
import logging
import re
from typing import Any
from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona
from .constants import *
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

    prompt = f"""You are an authentic, culturally savvy, high-IQ creator on X (Twitter) named {persona.display_name}.
You are analyzing this real live post to draft a viral, high-value QUOTE TWEET (standalone take adding a strong perspective).

=== TARGET TWEET ===
Author: @{author}
Content: "{text}"
Attached Media / Visual Details: {media_desc_str}

=== TOP 10 COMMENTS IN THE ROOM (SENTIMENT, HUMOR & DEBATE) ===
{comments_formatted if comments_formatted else 'No comments yet'}

=== GENERATION DIRECTIVES ===
1. 100% CONTEXT ACCURACY: Understand what the post, media, and room are actually discussing. Speak directly to the core topic. Never force bizarre analogies or unrelated persona hobbies.
2. HIGH-VALUE STANDALONE PERSPECTIVE: Deliver an insightful observation, witty comparison, or sharp industry take that adds genuine value to the timeline.
3. NATURAL HUMAN VOICE: Sound authentic, conversational, and observant.
4. EMOJIS & HASHTAGS: Use natural, expressive emojis (💀, 😭, 🔥, 😂, 💯, 🤌, 🌴, 🎮) where fitting. Include 1-2 relevant hashtags if natural for the topic (e.g. #GTA6, #Cinema, #DCU, #Tech).
5. GIF ATTACHMENT: Provide a 1-3 word Tenor search query in `gif_query` if a reaction GIF adds punch (e.g. 'mind blown', 'popcorn', 'sweating nervous', 'this is fine fire'); otherwise null.
6. LENGTH: Under 260 characters with clean natural punctuation (no cutting words in half).

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
                    {"role": "system", "content": "You are a world-class social media strategist and authentic creator on X."},
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

