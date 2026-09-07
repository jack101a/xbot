"""
Trend Generator Collector and Persona Helpers.
"""

from __future__ import annotations

from pathlib import Path

from xbot.config import settings
from xbot.models.profile import Profile
from xbot.persona import load_persona
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Persona,
    Personality,
    Rules,
    WritingStyle,
)


def _get_persona_for_profile(profile_slug: str) -> Persona | None:
    """Loads Persona for a given profile slug if available."""
    try:
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "persona.yaml").exists():
            return load_persona(cfg_path)
    except Exception:
        pass
    return None


def _get_default_persona(profile: Profile | None = None) -> Persona:
    """Provides a safe default Persona instance if not configured on disk."""
    name = profile.display_name if profile and profile.display_name else "Creator"
    handle = profile.x_handle if profile and profile.x_handle else "@creator"
    slug = profile.profile_slug if profile and profile.profile_slug else "default"
    return Persona(
        id=slug,
        display_name=name,
        x_handle=handle,
        identity=Identity(background="Digital creator and cultural observer", occupation="Content Creator"),
        personality=Personality(
            traits=["witty", "analytical", "observant"],
            values=["authenticity", "creativity"],
            communication_style="Sharp, authentic, insightful",
        ),
        interests=Interests(
            primary=["technology", "culture", "creative workflows"],
            secondary=["memes", "productivity"],
        ),
        writing_style=WritingStyle(
            tone="Sharp, witty, authentic",
            typical_length="concise",
            formatting=[],
            examples=[],
        ),
        goals=Goals(content_pillars=["tech", "culture"], short_term=[], long_term=[]),
        rules=Rules(always=["be authentic"], never=["no spam"]),
    )


def _detect_reaction_gif_query(text: str, topic: str) -> str | None:
    """Infers an optional reaction GIF search query for punchy standalone takes."""
    combined = f"{text} {topic}".lower()
    if any(kw in combined for kw in ["dead", "💀", "crying", "unhinged", "wild", "insane", "facepalm", "smh", "plot twist"]):
        return "mind blown"
    if any(kw in combined for kw in ["cinema", "pure cinema", "masterpiece", "movie", "nolan"]):
        return "pure cinema"
    if any(kw in combined for kw in ["agree", "facts", "100%", "real", "nodding"]):
        return "nodding yes"
    if any(kw in combined for kw in ["drama", "tea", "roast", "feud", "beef"]):
        return "popcorn eating"
    return None
