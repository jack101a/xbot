from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.ai.nvidia_image import generate_and_save_nvidia_image_async
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

GROWTH_ARCHETYPES = [
    "GLOBAL_MUTUALS_CONNECT",
    "CREATOR_MILESTONE_CELEBRATION",
    "RESILIENCE_MINDSET",
    "ACTIVE_BOOST_CONNECT",
]

GROWTH_IMAGE_THEMES = [
    "A sleek 3D metallic gold checkmark with glowing neon blue accents on a dark slate background (#0D1117), ultra-clean render, 4:5 portrait aspect ratio.",
    "A minimalist high-contrast diamond trophy with glowing cybernetic reflections and dark studio lighting, 4:5 portrait aspect ratio.",
    "A futuristic atmospheric creator studio desk at night with neon cyan and amber lighting, multiple glowing monitors showing charts and code, cinematic lighting, 4:5 aspect ratio.",
    "A bold 3D typography artwork displaying 'GLOBAL NETWORK' with floating gold particles and volumetric lighting on dark glass, 4:5 portrait aspect ratio.",
    "A 3D golden laurel wreath and verified badge on a matte black podium with subtle smoke and dramatic rim lighting, 4:5 aspect ratio.",
]


class GrowthPostResult(BaseModel):
    tweet_copy: str = Field(..., description="High-converting growth/connection tweet copy with CTA")
    image_prompt: str = Field(..., description="Detailed NVIDIA GenAI prompt for 4:5 or 1:1 image")
    aspect_ratio: Literal["4:5", "1:1"] = Field(default="4:5", description="Image aspect ratio")
    archetype: str = Field(..., description="Chosen growth archetype")
    cta_type: str = Field(..., description="Call-to-action type to drive comments")


GROWTH_SYSTEM_PROMPT = """You are an elite X (Twitter) Organic Growth & Community Director.
Your job is to generate highly engaging, authentic growth & connection posts that inspire other creators, builders, and active users to drop comments, like, and connect as mutuals.

KEY GROWTH ARCHETYPES:
1. GLOBAL_MUTUALS_CONNECT: Celebrating mutual support, global creators, and building together.
   Example: "We can bond together in harmony. We are global partners, creators, and mutuals. Drop your handle below — let's connect and support each other 🔥🤝"
2. CREATOR_MILESTONE_CELEBRATION: Milestone mindset, celebrating progress, building in public.
   Example: "Every milestone starts with consistency. Celebrate small wins, keep building, and never stop learning. Who's active today? Drop a 👋"
3. RESILIENCE_MINDSET: Powerful, authentic mindset wisdom paired with community encouragement.
   Example: "Pressure creates diamonds. Patience turns effort into excellence. Keep climbing, your peak is waiting. Drop 'Active' if you're grinding today 💎✨"
4. ACTIVE_BOOST_CONNECT: Direct, friendly interactive post welcoming mutual connections.
   Example: "Never afraid of failure — keep trying. If you're looking to connect with active verified creators, drop 'Hello' below. Following back active mutuals! 🚀"

RULES:
- Keep copy authentic, energetic, and clean (under 260 characters).
- Include natural emojis (🤝, 🔥, 🚀, 💎, 💯, ✨).
- Always include an easy comment trigger CTA (e.g. "Drop your handle", "Drop 'Hello'", "Say Hi below").
- The image prompt must specify 4:5 portrait aspect ratio, dark mode aesthetic (#0D1117), crisp 3D or cinematic realism, zero distorted AI text.

Return ONLY a JSON object:
{
  "tweet_copy": "...",
  "image_prompt": "...",
  "aspect_ratio": "4:5",
  "archetype": "GLOBAL_MUTUALS_CONNECT" | "CREATOR_MILESTONE_CELEBRATION" | "RESILIENCE_MINDSET" | "ACTIVE_BOOST_CONNECT",
  "cta_type": "drop_handle" | "drop_hello" | "say_hi" | "active_check"
}
"""


async def generate_growth_post_spec(
    persona: Persona | None = None,
    preferred_archetype: str | None = None,
    client: Any | None = None,
) -> GrowthPostResult:
    """
    Synthesizes an authentic, high-converting growth tweet with an image prompt.
    """
    if client is None:
        client = get_ai_client()

    chosen_archetype = preferred_archetype or random.choice(GROWTH_ARCHETYPES)
    creator_name = persona.display_name if persona else "Creator"
    creator_handle = f"@{persona.x_handle.lstrip('@')}" if persona and persona.x_handle else "@creator"

    user_prompt = f"""Generate a high-engagement growth post for {creator_name} ({creator_handle}).
Archetype: {chosen_archetype}
Pillars / Interests: {', '.join(persona.interests.primary) if persona else 'Tech, AI, Cinema, Growth'}
Ensure it has a natural connection CTA to inspire comments from active mutuals.
"""

    model_cascade = getattr(
        settings, "MODEL_POST_CREATION", "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    )

    try:
        response = await client.chat.completions.create(
            model=model_cascade,
            messages=[
                {"role": "system", "content": GROWTH_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=500,
        )

        content_str = response.choices[0].message.content or ""
        clean_json = content_str.strip()
        if "```" in clean_json:
            clean_json = re.sub(r"^```(?:json)?", "", clean_json).rstrip("`").strip()

        data = json.loads(clean_json)
        return GrowthPostResult(
            tweet_copy=data.get("tweet_copy", "").strip()[:260],
            image_prompt=data.get("image_prompt", "").strip() or random.choice(GROWTH_IMAGE_THEMES),
            aspect_ratio="4:5",
            archetype=data.get("archetype", chosen_archetype),
            cta_type=data.get("cta_type", "drop_hello"),
        )
    except Exception as e:
        logger.error("Growth post AI generation failed: %s. Discarding without template fallback.", e)
        return None


async def generate_growth_post_with_image(
    persona: Persona | None = None,
    output_dir: str | None = None,
    client: Any | None = None,
) -> tuple[GrowthPostResult | None, str | None]:
    """
    Generates growth copy and immediately renders a 4:5 image via NVIDIA GenAI.
    Returns (GrowthPostResult, local_image_file_path).
    """
    post_spec = await generate_growth_post_spec(persona=persona, client=client)
    if not post_spec:
        return None, None

    try:
        image_path = await generate_and_save_nvidia_image_async(
            prompt=post_spec.image_prompt,
            aspect_ratio="4:5",
            output_dir=output_dir,
        )
    except Exception as img_err:
        logger.warning("Primary image prompt generation failed (%s). Retrying with clean verified theme.", img_err)
        verified_prompt = random.choice(GROWTH_IMAGE_THEMES)
        post_spec.image_prompt = verified_prompt
        try:
            image_path = await generate_and_save_nvidia_image_async(
                prompt=verified_prompt,
                aspect_ratio="4:5",
                output_dir=output_dir,
            )
        except Exception:
            image_path = None

    return post_spec, image_path
