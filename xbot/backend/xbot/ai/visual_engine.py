from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

from xbot.ai.anti_ai_gatekeeper import ANTI_AI_TYPOGRAPHY_DIRECTIVE, AntiAIGatekeeper
from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

# Valid format types & SimClusters
FORMAT_TYPES = Literal["storyboard_4panel", "side_by_side", "urban_lifestyle", "dark_infographic"]
SIMCLUSTERS = Literal["Tech/AI", "Cinema/Prestige", "Urban/Creator", "Anime/PopCulture"]

VISUAL_FORMAT_TEMPLATES: dict[str, dict[str, str]] = {
    "storyboard_4panel": {
        "name": "4-Panel Storyboard / Progression Comic",
        "description": "Sequential 4-panel visual comic or scenario progression in 4:5 portrait (1080x1350). High contrast, clean panel borders, escalating tension in panels 1-3 with humorous or insightful resolution in panel 4.",
        "default_simcluster": "Tech/AI",
        "prompt_template": (
            "A detailed 4-panel comic storyboard grid in 4:5 vertical portrait aspect ratio (1080x1350). "
            "Panel 1: [Setup], Panel 2: [Escalation], Panel 3: [Peak Tension], Panel 4: [Visual Punchline/Payoff]. "
            "High-contrast dark-mode palette (#0D1117 background), crisp clean panel dividers, expressive cinematic lighting, "
            "digital illustration style with refined linework, zero distorted AI text or artifacts. --ar 4:5"
        ),
    },
    "side_by_side": {
        "name": "Side-by-Side Comparison / Expectation vs Reality",
        "description": "2-panel vertical split comparison in 4:5 portrait (1080x1350). Left/Top: Expectation / Ideal / Legacy. Right/Bottom: Reality / Actual / Modern. Stark visual contrast and bold minimalist typography.",
        "default_simcluster": "Tech/AI",
        "prompt_template": (
            "A split side-by-side visual comparison in 4:5 vertical portrait aspect ratio (1080x1350). "
            "Left side: [Expectation / Legacy / Theory], soft serene lighting. "
            "Right side: [Reality / Modern / Production], dramatic high-contrast moody lighting. "
            "Bold minimalist typography labels, sharp render, ultra-detailed textures, zero blurry AI distortions. --ar 4:5"
        ),
    },
    "urban_lifestyle": {
        "name": "Candid Urban Creator Realism / 35mm Film",
        "description": "Authentic raw 35mm film photography in 4:5 portrait (1080x1350). South Asian creator aesthetic, candid realism, Kodak Portra 400 warm palette, natural ambient lighting, subtle film grain, anti-plastic authenticity.",
        "default_simcluster": "Urban/Creator",
        "prompt_template": (
            "Candid 35mm film photograph in 4:5 vertical portrait aspect ratio (1080x1350), shot on Leica M6 with 35mm f/1.4 lens on Kodak Portra 400 film. "
            "A stylish young South Asian creator in an urban studio cafe in Mumbai surrounded by camera gear and laptop, caught in a genuine candid expression. "
            "Soft natural golden-hour ambient lighting, rich warm color grading, organic film grain, authentic skin textures with subtle imperfections, no glossy AI plastic smoothing. --ar 4:5"
        ),
    },
    "dark_infographic": {
        "name": "High-Contrast Dark-Mode Cheat Sheet & System Architecture",
        "description": "Sleek high-contrast dark-mode infographic / cheatsheet in 4:5 portrait (1080x1350). Background #0D1117, neon cyan (#58A6FF) and electric amber (#F2994A) accents, monospace terminal aesthetic, modular architecture diagram.",
        "default_simcluster": "Tech/AI",
        "prompt_template": (
            "A clean, high-contrast dark-mode technical infographic and system diagram in 4:5 vertical portrait aspect ratio (1080x1350). "
            "Deep dark slate background (#0D1117), crisp vector diagrams with neon cyan (#58A6FF) and warm amber (#F2994A) signal paths. "
            "Modular architecture boxes, clean monospace typography, structured layout with high legibility on mobile screens, ultra-sharp vector graphics, zero visual clutter. --ar 4:5"
        ),
    },
}


class VisualPostSpec(BaseModel):
    tweet_copy: str = Field(..., description="Setup tension hook strictly under 140 characters")
    image_prompt: str = Field(..., description="Detailed visual prompt specifying 4:5 portrait aspect ratio, lighting, dark mode, high contrast")
    aspect_ratio: Literal["4:5", "1:1"] = Field(default="4:5", description="Aspect ratio (4:5 for mobile screen takeover or 1:1 square)")
    format_type: str = Field(..., description="Visual format type: storyboard_4panel, side_by_side, urban_lifestyle, dark_infographic")
    target_simcluster: str = Field(..., description="Target SimCluster: Tech/AI, Cinema/Prestige, Urban/Creator, Anime/PopCulture")
    one_two_punch_strategy: str = Field(..., description="Cognitive separation strategy where copy sets up tension and image delivers punchline")

    @field_validator("tweet_copy")
    @classmethod
    def validate_tweet_copy(cls, v: str) -> str:
        clean = " ".join(v.strip().split())
        if len(clean) >= 140:
            # Truncate cleanly at word boundary or sentence boundary under 140 chars
            truncated = clean[:136]
            last_space = truncated.rfind(" ")
            if last_space > 80:
                clean = truncated[:last_space] + "..."
            else:
                clean = truncated + "..."
        return clean

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, v: str) -> str:
        if v not in ("4:5", "1:1"):
            raise ValueError(f"Aspect ratio must be '4:5' or '1:1', got '{v}'")
        return v


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


def generate_fallback_visual_spec(
    topic: str,
    format_type: str | None = None,
    persona: Persona | None = None,
) -> VisualPostSpec:
    """
    Generates a high-quality deterministic VisualPostSpec when AI models are unavailable or timed out.
    """
    resolved_format = format_type or infer_format_type(topic)
    if resolved_format not in VISUAL_FORMAT_TEMPLATES:
        resolved_format = "storyboard_4panel"

    resolved_simcluster = infer_simcluster(topic, resolved_format)
    template = VISUAL_FORMAT_TEMPLATES[resolved_format]

    # Persona-aware tone injection
    creator_name = persona.display_name if persona else "Creator"

    if resolved_format == "storyboard_4panel":
        tweet_copy = f"The 4 stages of realizing {topic[:70]}."
        image_prompt = (
            f"A 4-panel storyboard comic in 4:5 vertical portrait aspect ratio (1080x1350). "
            f"Subject: \"{topic}\". Panel 1: Optimistic start. Panel 2: Subtle complication. "
            f"Panel 3: Escalating panic. Panel 4: Hilarious resigned acceptance. "
            f"Dark mode aesthetic (#0D1117 background), vibrant lighting, expressive character, no distorted AI text. --ar 4:5"
        )
        strategy = "Tweet copy sets up the universal 4-stage dilemma; 4-panel comic image delivers the visual punchline."

    elif resolved_format == "side_by_side":
        tweet_copy = f"Expectation vs reality when dealing with {topic[:65]}."
        image_prompt = (
            f"A high-contrast side-by-side comparison split in 4:5 vertical portrait aspect ratio (1080x1350). "
            f"Topic: \"{topic}\". Left panel: Ideal textbook theory with calm lighting. "
            f"Right panel: Chaotic practical reality with high-contrast dramatic shadows. "
            f"Minimalist clean labels, crisp render. --ar 4:5"
        )
        strategy = "Tweet copy presents a classic expectation hook; side-by-side visual delivers the contrast payoff."

    elif resolved_format == "urban_lifestyle":
        tweet_copy = f"Behind the scenes of {topic[:75]}."
        image_prompt = (
            f"Candid 35mm film photograph in 4:5 vertical portrait aspect ratio (1080x1350) on Kodak Portra 400. "
            f"A stylish South Asian creator working on \"{topic}\" at a wooden desk in an atmospheric urban cafe. "
            f"Warm golden lighting, soft film grain, authentic textures, no plastic AI smoothing. --ar 4:5"
        )
        strategy = "Tweet copy frames authentic creator behind-the-scenes; 35mm photography delivers aesthetic dwell value."

    else:  # dark_infographic
        tweet_copy = f"System breakdown: {topic[:80]}."
        image_prompt = (
            f"High-contrast dark-mode technical infographic in 4:5 vertical portrait aspect ratio (1080x1350). "
            f"Topic: \"{topic}\". Deep dark background (#0D1117), neon cyan (#58A6FF) and amber (#F2994A) vector diagrams, "
            f"monospace terminal boxes, clean modular flow with high mobile legibility. --ar 4:5"
        )
        strategy = "Tweet copy introduces the core framework; dark infographic delivers high-utility bookmarkable visual value."

    return VisualPostSpec(
        tweet_copy=tweet_copy[:139],
        image_prompt=image_prompt,
        aspect_ratio="4:5",
        format_type=resolved_format,
        target_simcluster=resolved_simcluster,
        one_two_punch_strategy=strategy,
    )


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
        "1. Tweet Copy (Setup / Tension Hook): Strictly UNDER 140 characters (< 140 chars). Builds curiosity, tension, irony, or a relatable dilemma. Do NOT give away the punchline in text.\n"
        "2. Image Prompt (Visual Payoff / Punchline): Detailed visual generation prompt in 4:5 vertical portrait aspect ratio (1080x1350) for mobile viewport takeover (~74% mobile screen).\n"
        "   - Include lighting, color palette, camera/lens specs, high contrast, dark mode theme (#0D1117) where applicable, and zero distorted AI text.\n"
        "3. Aspect Ratio: Default to '4:5' (or '1:1').\n"
        "4. Format Types: 'storyboard_4panel', 'side_by_side', 'urban_lifestyle', 'dark_infographic'.\n"
        "5. Target SimClusters: 'Tech/AI', 'Cinema/Prestige', 'Urban/Creator', 'Anime/PopCulture'.\n\n"
        f"{persona_context}"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        '  "tweet_copy": "Setup tension hook strictly under 140 chars",\n'
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
        "- Tweet copy MUST be strictly < 140 characters.\n"
        "- Default aspect ratio to 4:5 for maximum mobile screen takeover.\n"
        "- The image prompt must deliver the visual payoff that makes the tweet copy click."
    )

    return "\n\n".join(lines)


async def generate_visual_post_spec(
    topic: str,
    format_type: str | None = None,
    persona: Persona | None = None,
    client: Any | None = None,
) -> VisualPostSpec:
    """
    Generates a 4:5 Visual Post Specification with One-Two Punch captioning
    and AI routing fallback (Gemini Flash / DeepSeek cascade).
    """
    if client is None:
        client = get_ai_client()

    gatekeeper = AntiAIGatekeeper()
    resolved_format = format_type or infer_format_type(topic)
    resolved_simcluster = infer_simcluster(topic, resolved_format)

    system_prompt = _build_visual_system_prompt(persona=persona, format_type=resolved_format)
    user_prompt = _build_visual_user_prompt(topic=topic, format_type=resolved_format, persona=persona)

    model_cascade = getattr(
        settings, "MODEL_POST_CREATION", "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
    )

    try:
        logger.info("Generating visual post spec for topic: '%s' (format: %s)", topic[:50], resolved_format)
        response = await client.chat.completions.create(
            model=model_cascade,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.75,
            max_tokens=650,
        )

        content_str = response.choices[0].message.content or ""
        clean_json = content_str.strip()
        if "```" in clean_json:
            clean_json = re.sub(r"^```(?:json)?", "", clean_json).rstrip("`").strip()

        data = json.loads(clean_json)

        raw_tweet_copy = data.get("tweet_copy", "").strip()
        remediated_copy = gatekeeper.remediate_minor_issues(raw_tweet_copy)

        # Enforce < 140 chars strictly
        if len(remediated_copy) >= 140:
            truncated = remediated_copy[:136]
            last_space = truncated.rfind(" ")
            if last_space > 80:
                remediated_copy = truncated[:last_space] + "..."
            else:
                remediated_copy = truncated + "..."

        image_prompt = data.get("image_prompt", "").strip()
        if not image_prompt:
            image_prompt = VISUAL_FORMAT_TEMPLATES.get(resolved_format, {}).get("prompt_template", "")

        aspect_ratio = data.get("aspect_ratio", "4:5")
        if aspect_ratio not in ("4:5", "1:1"):
            aspect_ratio = "4:5"

        out_format = data.get("format_type", resolved_format)
        if out_format not in VISUAL_FORMAT_TEMPLATES:
            out_format = resolved_format

        out_simcluster = data.get("target_simcluster", resolved_simcluster)
        if out_simcluster not in ["Tech/AI", "Cinema/Prestige", "Urban/Creator", "Anime/PopCulture"]:
            out_simcluster = resolved_simcluster

        strategy = data.get("one_two_punch_strategy", "Setup tension in tweet copy; deliver visual punchline in 4:5 image.")

        return VisualPostSpec(
            tweet_copy=remediated_copy,
            image_prompt=image_prompt,
            aspect_ratio=aspect_ratio,
            format_type=out_format,
            target_simcluster=out_simcluster,
            one_two_punch_strategy=strategy,
        )

    except Exception as e:
        logger.warning("Visual post spec AI generation failed for topic '%s': %s. Using deterministic template fallback.", topic[:50], e)
        return generate_fallback_visual_spec(
            topic=topic,
            format_type=format_type,
            persona=persona,
        )
