from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.ai.image_engine import generate_post_image_async
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

GROWTH_TARGET_GOALS = ["500", "1K", "2K", "5K", "ROAD TO 500", "ROAD TO 1000", "ROAD TO 2K"]

GROWTH_ARCHETYPES = [
    "FOLLOWER_TARGET_GOAL",
    "STARS_OF_GROWTH_MOMENTUM",
    "COMMUNITY_CONNECTION_NETWORK",
    "RETRO_MODERN_X_BIRD_ASCENT",
    "BUILD_IN_PUBLIC_MILESTONE",
    "GLOBAL_MUTUALS_CONNECT",
    "CREATOR_MILESTONE_CELEBRATION",
    "RESILIENCE_MINDSET",
    "ACTIVE_BOOST_CONNECT",
]

GROWTH_IMAGE_THEMES = [
    "A sleek, minimalist dark-mode milestone card with a glowing golden progress bar and bold modern typography 'ROAD TO 500' on dark brushed obsidian (#0B0E14), subtle amber rim lighting, ultra-clean graphic design.",
    "A striking conceptual artwork of glowing geometric stairs of growth ascending into a deep midnight sky illuminated by brilliant constellations and golden stardust particles, cinematic 3D realism.",
    "A modern aesthetic network graph with glowing golden and cyan interconnected nodes forming a radiant community web on dark slate, symbolizing global mutual creators connecting.",
    "A stylized, minimalist 3D geometric origami bird in dark obsidian and glowing gold accents taking flight from a sleek milestone podium reading 'TARGET: 1000', modern aesthetic.",
    "A sleek creator milestone plaque displaying '500 FOLLOWERS GOAL • X GROWTH' with a glowing neon circular progress meter and gold accent lines on a matte black background.",
    "A clean minimalist studio shot of a floating 3D golden milestone trophy with 'TARGET: 2K MUTUALS' embossed on the podium, dark ambient lighting with subtle gold dust particles.",
    "A modern developer aesthetic graphic: dark terminal window card with glowing green/cyan code syntax and a bold header 'TECH & BUILD • ROAD TO 500', ultra-crisp typography on matte obsidian.",
    "A sleek aesthetic card with 3D geometric gold and glass blocks forming an upward stair with 'X GROWTH • 500 GOAL', high-contrast minimalism, dark studio background.",
    "A surreal minimalist digital artwork of a glowing neon key unlocking a floating obsidian door against a cosmic dark twilight sky with stars of growth, cinematic rim lighting.",
]


class GrowthPostResult(BaseModel):
    tweet_copy: str = Field(..., description="High-converting creative growth/connection tweet copy with CTA")
    image_prompt: str = Field(..., description="Detailed AI creative image prompt with rich visual variation")
    aspect_ratio: str = Field(default="1:1", description="Creative image aspect ratio (1:1, 16:9, 4:5, 3:2)")
    archetype: str = Field(..., description="Chosen growth archetype")
    target_goal: str = Field(default="500", description="Milestone goal (500, 1K, 2K, etc.)")
    cta_type: str = Field(..., description="Call-to-action type to drive comments")


def compute_next_milestone(current_followers: int) -> int:
    """Calculates the next target follower goal in strict 500-gap intervals (500, 1000, 1500, 2000, 2500...)."""
    if current_followers <= 0:
        return 500
    return ((int(current_followers) // 500) + 1) * 500


GROWTH_SYSTEM_PROMPT = """You are an elite Growth Specialist for X (Twitter) specializing in high-engagement viral Follow-for-Follow and Community Growth posts.

YOUR CORE MISSION:
Generate ultra-simple, high-converting growth posts modeled directly on top-performing viral accounts on X (like @Vincent4T_, @Busayocomics, @FollowLoopx) paired with eye-catching 3D milestone graphic prompts.

VIRAL 3-LINE POST STRUCTURE (Under 180 characters):
1. Line 1: Goal Hook asking about the follower milestone (e.g. "Want 500 active followers?", "If you need 500+ real followers?", "Ready to hit 1000 followers today? 🚀", "Looking for 500 active mutuals?").
2. Line 2: 1-Word / Fast Action Trigger that takes 1 second to reply (e.g. "Just type = ACTIVE", "Just Say YES", "Hit me with a HELLO 👋", "Drop your handle below", "Type = DONE").
3. Line 3: Fast Reciprocity Promise (e.g. "I’ll follow back everyone instantly!", "I'll give your page a boost ✨", "Let's connect & grow together 🤝", "Following back immediately!").

- Include 2-3 high-energy emojis (🎯, 🚀, 👋, 🤝, ✨, 🔥, 💯).
- Include 1-2 top growth/niche hashtags (e.g. #FollowForFollowBack, #GainFollowers, #500Followers, #TechTwitter, #BuildInPublic, #F4F).

IMAGE PROMPT INSTRUCTIONS (3D Viral Milestone Aesthetics):
Generate a prompt for a high-end 3D graphic centered on the dynamic milestone number:
- Style 1 (Prestige 3D Gold & Emerald): A high-quality 3D render of the number '{target_milestone}' in bold, polished metallic gold typography, centered with a golden verified checkmark emblem above it, set against a rich dark emerald green textured background.
- Style 2 (Vibrant Neon Glow Badge): A glowing 3D neon achievement crest with '{target_milestone}+' in radiant neon-pink/cyan with light rays and sparkles on dark backdrop.
- Style 3 (Luxury Liquid Gold Wave): A dramatic 3D render of the number '{target_milestone} ACTIVE' with elegant flowing ribbons of liquid gold and modern typography 'COMMENT • FOLLOW • CONNECT'.

Return ONLY a JSON object:
{
  "tweet_copy": "...",
  "image_prompt": "...",
  "aspect_ratio": "1:1",
  "archetype": "FOLLOWER_TARGET_GOAL",
  "target_goal": "500" | "1000" | "1500" | "2000",
  "cta_type": "active_trigger"
}
"""


async def generate_growth_post_spec(
    persona: Persona | None = None,
    current_followers: int = 0,
    preferred_archetype: str | None = None,
    client: Any | None = None,
) -> GrowthPostResult:
    """
    Synthesizes a high-converting growth tweet with a 3D milestone image prompt based on dynamic 500-gap milestones.
    """
    if client is None:
        client = get_ai_client()

    target_milestone = compute_next_milestone(current_followers)
    chosen_archetype = preferred_archetype or "FOLLOWER_TARGET_GOAL"
    creator_name = persona.display_name if persona else "Creator"
    creator_handle = f"@{persona.x_handle.lstrip('@')}" if persona and persona.x_handle else "@creator"

    user_prompt = f"""Generate a viral growth post for {creator_name} ({creator_handle}).
Current Followers: {current_followers}
Next Follower Milestone Goal: {target_milestone} Followers (or {target_milestone}+)

Requirements:
- Follow the high-converting 3-line format (Goal question -> 1-word action trigger -> Reciprocal boost promise).
- Keep it simple, punchy, low friction, with 2-3 emojis and 1-2 growth hashtags.
- Craft a matching 3D milestone visual prompt featuring the bold number '{target_milestone}'.
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
            clean_json = re.sub(r"^```(?:json)?", "", clean_json, flags=re.MULTILINE)
            clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

        # Find first { and last }
        start_idx = clean_json.find("{")
        end_idx = clean_json.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            clean_json = clean_json[start_idx : end_idx + 1]

        try:
            data = json.loads(clean_json)
        except Exception:
            tweet_match = re.search(r'"tweet_copy"\s*:\s*"(.*?)"(?:\s*,\s*"\w+"|\s*})', clean_json, re.DOTALL)
            prompt_match = re.search(r'"image_prompt"\s*:\s*"(.*?)"(?:\s*,\s*"\w+"|\s*})', clean_json, re.DOTALL)
            aspect_match = re.search(r'"aspect_ratio"\s*:\s*"([^"]+)"', clean_json)
            arch_match = re.search(r'"archetype"\s*:\s*"([^"]+)"', clean_json)
            cta_match = re.search(r'"cta_type"\s*:\s*"([^"]+)"', clean_json)
            goal_match = re.search(r'"target_goal"\s*:\s*"([^"]+)"', clean_json)

            data = {
                "tweet_copy": tweet_match.group(1).strip() if tweet_match else "",
                "image_prompt": prompt_match.group(1).strip() if prompt_match else "",
                "aspect_ratio": aspect_match.group(1).strip() if aspect_match else "1:1",
                "archetype": arch_match.group(1).strip() if arch_match else chosen_archetype,
                "target_goal": goal_match.group(1).strip() if goal_match else str(target_milestone),
                "cta_type": cta_match.group(1).strip() if cta_match else "drop_hello",
            }

        tweet_text = (data.get("tweet_copy") or "").strip()[:260]
        image_p = (data.get("image_prompt") or "").strip() or f"A sleek 3D render of the milestone number '{target_milestone}' in polished metallic gold on a dark minimalist background."
        ratio_val = (data.get("aspect_ratio") or "1:1").strip()

        if not tweet_text:
            raise ValueError(f"No tweet_copy extracted from AI response (raw: {content_str[:120]})")

        return GrowthPostResult(
            tweet_copy=tweet_text,
            image_prompt=image_p,
            aspect_ratio=ratio_val,
            archetype=data.get("archetype", chosen_archetype),
            target_goal=str(data.get("target_goal", target_milestone)),
            cta_type=data.get("cta_type", "drop_hello"),
        )
    except Exception as e:
        logger.error("Growth post AI generation failed: %s.", e)
        return None


async def generate_growth_post_with_image(
    persona: Persona | None = None,
    current_followers: int = 0,
    output_dir: str | None = None,
    client: Any | None = None,
) -> tuple[GrowthPostResult | None, str | None]:
    """
    Generates growth copy and immediately renders an image via ChatGPT (with Flux fallback).
    Returns (GrowthPostResult, local_image_file_path).
    """
    post_spec = await generate_growth_post_spec(
        persona=persona,
        current_followers=current_followers,
        client=client,
    )
    if not post_spec:
        return None, None

    ratio = getattr(post_spec, "aspect_ratio", "1:1") or "1:1"
    try:
        image_path = await generate_post_image_async(
            prompt=post_spec.image_prompt,
            aspect_ratio=ratio,
            output_dir=output_dir,
            provider_preference="chatgpt",
        )
    except Exception as img_err:
        logger.warning("Growth image generation failed: %s", img_err)
        image_path = None

    return post_spec, image_path
