import asyncio
import base64
import json
import logging
import mimetypes
from pathlib import Path
import random
import re
from typing import Any

from xbot.ai.client import get_ai_client

logger = logging.getLogger(__name__)

MAX_VISION_RETRIES = 2
VISION_MODEL = "litellm/gemini-3.1-flash-lite"


def _format_image_payload(image_source: str) -> str:
    """Formats a URL, data URI, or local filesystem path into an OpenAI-compatible image URL."""
    clean_src = image_source.strip()
    if clean_src.startswith("http://") or clean_src.startswith("https://") or clean_src.startswith("data:"):
        return clean_src

    p = Path(clean_src)
    if p.exists() and p.is_file():
        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "image/png"
        raw_b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{raw_b64}"

    return clean_src


async def analyze_image_context(
    image_url: str,
    prompt_hint: str | None = None,
    client: Any | None = None,
) -> str | None:
    """
    Sends an image (URL or local path) to vision model for high-signal multimodal analysis.
    """
    if not image_url or not image_url.strip():
        return None

    clean_url = _format_image_payload(image_url)
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
            logger.info("Analyzing image vision (attempt %d/%d)...", attempt, MAX_VISION_RETRIES)
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

    logger.warning("Image vision analysis exhausted all %d attempts", MAX_VISION_RETRIES)
    return None


async def analyze_viral_growth_media(
    image_source: str,
    tweet_text: str | None = None,
    client: Any | None = None,
) -> dict[str, Any] | None:
    """
    Multimodal vision inspection of viral X growth & follow-for-follow media.
    Extracts aesthetic style, visual composition, goal badges, and a prompt recipe.
    """
    if not image_source or not image_source.strip():
        return None

    formatted_img = _format_image_payload(image_source)
    if client is None:
        client = get_ai_client()

    system_instruction = """You are an elite Art Director & Visual Growth Analyst on X (Twitter).
Analyze the provided viral social media graphic and extract its design secrets into a JSON object:
{
  "style_category": "minimalist_dark" | "3d_milestone_render" | "retro_modern" | "network_graph" | "cyber_vector",
  "key_visual_elements": ["element1", "element2", "..."],
  "goal_indicators": ["500 followers", "target badge", "progress meter", "stars of growth", etc.],
  "color_palette": "e.g. obsidian, metallic gold, neon cyan",
  "synthesized_image_prompt": "A detailed, creative, aesthetic prompt to generate a similar high-converting milestone graphic without copying copyrighted assets."
}
Return ONLY valid JSON.
"""

    context_prompt = f"Accompanying Tweet Copy: '{tweet_text}'\n" if tweet_text else ""
    user_content = [
        {"type": "text", "text": f"Analyze this viral X growth image.\n{context_prompt}"},
        {"type": "image_url", "image_url": {"url": formatted_img}},
    ]

    for attempt in range(1, MAX_VISION_RETRIES + 1):
        try:
            logger.info("Analyzing viral growth media via vision model (attempt %d/%d)...", attempt, MAX_VISION_RETRIES)
            response = await client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                max_tokens=350,
                temperature=0.2,
            )
            raw_content = response.choices[0].message.content or ""
            clean_json = raw_content.strip()
            if "```" in clean_json:
                clean_json = re.sub(r"^```(?:json)?", "", clean_json).rstrip("`").strip()

            data = json.loads(clean_json)
            return data
        except Exception as e:
            logger.warning("analyze_viral_growth_media attempt %d failed: %s", attempt, e)
            if attempt < MAX_VISION_RETRIES:
                await asyncio.sleep(1.0 * attempt)

    return None

