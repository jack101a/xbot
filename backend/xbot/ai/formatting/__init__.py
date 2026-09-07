from __future__ import annotations

from .cleaner import (
    CONSECUTIVE_NEWLINES_PATTERN,
    TRAILING_EMOJI_PATTERN,
    enforce_length_cadence,
    enforce_pacing_whitespace,
    strip_formulaic_trailing_emojis,
)
from .engine import format_content, post_process_formatted_content
from .typography import (
    ARCHETYPE_REGISTRY,
    ArchetypeSpec,
    PostFormattingArchetype,
    select_archetype,
)

__all__ = [
    "PostFormattingArchetype",
    "ArchetypeSpec",
    "ARCHETYPE_REGISTRY",
    "TRAILING_EMOJI_PATTERN",
    "CONSECUTIVE_NEWLINES_PATTERN",
    "select_archetype",
    "enforce_pacing_whitespace",
    "strip_formulaic_trailing_emojis",
    "enforce_length_cadence",
    "post_process_formatted_content",
    "format_content",
]
