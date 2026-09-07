from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.ai.formatting import (
    ARCHETYPE_REGISTRY,
    CONSECUTIVE_NEWLINES_PATTERN,
    TRAILING_EMOJI_PATTERN,
    ArchetypeSpec,
    PostFormattingArchetype,
    enforce_length_cadence,
    enforce_pacing_whitespace,
    format_content,
    post_process_formatted_content,
    select_archetype,
    strip_formulaic_trailing_emojis,
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
