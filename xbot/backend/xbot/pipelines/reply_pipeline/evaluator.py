"""
Reply Pipeline Evaluator and Persona Helpers.
"""

from __future__ import annotations

from pathlib import Path

from xbot.config import settings
from xbot.persona import load_persona
from xbot.persona.loader import Persona


def _get_persona_for_profile(profile_slug: str) -> Persona | None:
    try:
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "persona.yaml").exists():
            return load_persona(cfg_path)
    except Exception:
        pass
    return None
