from __future__ import annotations
from typing import Any
from xbot.ai.anti_ai_gatekeeper import ANTI_AI_TYPOGRAPHY_DIRECTIVE
from xbot.ai.visual_templates import VISUAL_FORMAT_TEMPLATES
from xbot.persona.loader import Persona
from xbot.ai.visual_models import VisualPostSpec

def infer_format_type(topic: str) -> str:
    """
    Infers the optimal visual format type based on topic keywords.
    """
    t_lower = topic.lower()

    # 1. Side by side comparisons
    if any(kw in t_lower for kw in ["vs", "versus", "comparison", "compared", "difference", "expectation vs reality", "before and after"]):
        return "side_by_side"

    # 2. Dark infographics & cheatsheets
    if any(kw in t_lower for kw in ["cheatsheet", "cheat sheet", "infographic", "system design", "architecture", "framework", "roadmap", "benchmark", "guide", "diagram"]):
        return "dark_infographic"

    # 3. Urban lifestyle / 35mm creator realism
    if any(kw in t_lower for kw in ["creator", "lifestyle", "cafe", "vlog", "street photography", "mumbai", "behind the scenes", "bts", "desk setup", "coffee"]):
        return "urban_lifestyle"

    # 4. 4-panel storyboard comic
    if any(kw in t_lower for kw in ["comic", "story", "panel", "step", "friday", "deploy", "realize", "moment", "struggle", "escalation"]):
        return "storyboard_4panel"

    return "storyboard_4panel"


def infer_simcluster(topic: str, format_type: str) -> str:
    """
    Infers the target SimCluster for algorithmic distribution based on topic and format.
    """
    t_lower = topic.lower()

    if any(kw in t_lower for kw in ["cinema", "film", "movie", "nolan", "imax", "director", "hollywood", "bollywood", "cinematography", "trailer"]):
        return "Cinema/Prestige"

    if any(kw in t_lower for kw in ["anime", "manga", "gaming", "vtuber", "otaku", "tier list", "waifu"]):
        return "Anime/PopCulture"

    if any(kw in t_lower for kw in ["creator", "vlog", "lifestyle", "mumbai", "editing", "camera", "youtube", "grind", "b-roll"]):
        return "Urban/Creator"

    if any(kw in t_lower for kw in ["ai", "tech", "python", "code", "dev", "gpu", "llm", "backend", "system", "postgres", "cloud", "software", "api"]):
        return "Tech/AI"

    # Default fallback based on format template
    template_info = VISUAL_FORMAT_TEMPLATES.get(format_type)
    if template_info and "default_simcluster" in template_info:
        return template_info["default_simcluster"]

    return "Tech/AI"


def _build_visual_system_prompt(persona: Persona | None = None, format_type: str | None = None) -> str:
    persona_context = ""
    if persona:
        persona_context = (
            f"Creator Persona: {persona.display_name} (@{persona.x_handle.lstrip('@')})\n"
            f"Tone & Voice: {persona.personality.communication_style}\n"
            f"Values: {', '.join(persona.personality.values)}\n"
            f"Interests: {', '.join(persona.interests.primary)}\n\n"
        )

    return (
        "You are an expert Visual Post & Meme Virality Director for X (Twitter).\n"
        "Your task is to design high-engagement visual post specifications utilizing the 'One-Two Punch' strategy:\n"
        "1. Tweet Copy (Setup / Tension Hook / Reaction): Natural, flexible human length (from a punchy 1-word reaction like 'real 💯' or 'pure cinema 😭' to a 1-2 sentence tension setup up to 280 chars). Do NOT artificially force every post to be the exact same length.\n"
        "2. Image Prompt (Visual Payoff / Punchline): Detailed visual generation prompt in 4:5 vertical portrait aspect ratio (1080x1350) for mobile viewport takeover (~74% mobile screen).\n"
        "   - Include lighting, color palette, camera/lens specs, high contrast, dark mode theme (#0D1117) where applicable, and zero distorted AI text.\n"
        "3. Aspect Ratio: Default to '4:5' (or '1:1').\n"
        "4. Format Types: 'storyboard_4panel', 'side_by_side', 'urban_lifestyle', 'dark_infographic'.\n"
        "5. Target SimClusters: 'Tech/AI', 'Cinema/Prestige', 'Urban/Creator', 'Anime/PopCulture'.\n\n"
        f"{persona_context}"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        '  "tweet_copy": "Natural human caption or tension hook (can be short reaction like \'pure cinema 😭\' or detailed take)",\n'
        '  "image_prompt": "Detailed image generation prompt specifying 4:5 aspect ratio (1080x1350), lighting, composition, colors, zero AI artifacts",\n'
        '  "aspect_ratio": "4:5",\n'
        '  "format_type": "storyboard_4panel" | "side_by_side" | "urban_lifestyle" | "dark_infographic",\n'
        '  "target_simcluster": "Tech/AI" | "Cinema/Prestige" | "Urban/Creator" | "Anime/PopCulture",\n'
        '  "one_two_punch_strategy": "Explanation of how tweet copy sets up tension and image delivers visual punchline"\n'
        "}"
    )


def _build_visual_user_prompt(
    topic: str,
    format_type: str | None = None,
    persona: Persona | None = None,
) -> str:
    lines = [f"## Topic / Visual Premise\n\"{topic}\""]

    if format_type and format_type in VISUAL_FORMAT_TEMPLATES:
        t_info = VISUAL_FORMAT_TEMPLATES[format_type]
        lines.append(
            f"## Desired Visual Format: {t_info['name']} ({format_type})\n"
            f"- Description: {t_info['description']}\n"
            f"- Base Style Reference: {t_info['prompt_template']}"
        )
    else:
        lines.append(
            "## Visual Format Direction\n"
            "Select the most viral format type among: storyboard_4panel, side_by_side, urban_lifestyle, dark_infographic."
        )

    lines.append(
        "## Key Directives:\n"
        "- Allow natural human length (short punchy reaction, meme quote, or 1-2 sentence hook up to 280 chars).\n"
        "- Default aspect ratio to 4:5 for maximum mobile screen takeover.\n"
        "- The image prompt must deliver the visual payoff that makes the tweet copy click."
    )

    return "\n\n".join(lines)


