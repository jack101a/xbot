from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from xbot.ai.client import get_ai_client

logger = logging.getLogger(__name__)

MAX_VISION_RETRIES = 2
VISION_MODEL = "litellm/gemini-3.1-flash-lite"


async def analyze_image_context(
    image_url: str,
    prompt_hint: str | None = None,
    client: Any | None = None,
) -> str | None:
    """
    Sends an image URL to Gemini Flash Lite for high-signal multimodal analysis
    (describing visual elements, text inside memes/screenshots, tone, and humor).
    Performs 2 automated retries with exponential backoff on transient errors.
    """
    if not image_url or not image_url.strip():
        return None

    clean_url = image_url.strip()
    if client is None:
        client = get_ai_client()

    hint_text = f" Context hint: {prompt_hint}" if prompt_hint else ""
    system_instruction = (
        "You are an expert visual analyst for a social media creator. "
        "Analyze the provided image and describe: (1) what is depicted, (2) any text or captions in the image, "
        "and (3) the emotional tone, meme context, or humor. Keep your summary concise (2-3 punchy sentences)."
    )

    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": f"Analyze this image for social media context.{hint_text}",
        },
        {
            "type": "image_url",
            "image_url": {"url": clean_url},
        },
    ]

    for attempt in range(1, MAX_VISION_RETRIES + 1):
        try:
            logger.info("Analyzing image vision (attempt %d/%d): %s", attempt, MAX_VISION_RETRIES, clean_url[:60])
            response = await client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=200,
                temperature=0.3,
            )
            analysis = response.choices[0].message.content
            if analysis and analysis.strip():
                clean_analysis = analysis.strip()
                logger.info("Image vision analysis completed successfully: '%s'", clean_analysis[:80])
                return clean_analysis
        except Exception as e:
            logger.warning("Image vision analysis attempt %d/%d failed: %s", attempt, MAX_VISION_RETRIES, e)
            if attempt < MAX_VISION_RETRIES:
                backoff_sec = (1.0 * attempt) + random.uniform(0.2, 0.6)
                await asyncio.sleep(backoff_sec)

    logger.warning("Image vision analysis exhausted all %d attempts for %s", MAX_VISION_RETRIES, clean_url[:60])
    return None
