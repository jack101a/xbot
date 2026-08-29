from __future__ import annotations

import logging
import random
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .typography import PostFormattingArchetype

logger = logging.getLogger(__name__)

# Regex Patterns for Post-Processing
TRAILING_EMOJI_PATTERN = re.compile(
    r"[\s\u200b]*[\U00010000-\U0010ffff\u2600-\u27ff\u2b50\u2705\u2728\u274c\u27a1\U0001f300-\U0001f9ff]+[\s\u200b]*$"
)
CONSECUTIVE_NEWLINES_PATTERN = re.compile(r"\n{3,}")


def enforce_pacing_whitespace(
    text: str, archetype: PostFormattingArchetype | None = None
) -> str:
    """
    Enforces double line break (\\n\\n) visual pacing, collapses redundant whitespace,
    and formats bullet lists cleanly.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""

    # Collapse 3+ newlines to standard \n\n
    cleaned = CONSECUTIVE_NEWLINES_PATTERN.sub("\n\n", cleaned)

    # Format lines
    lines = [line.rstrip() for line in cleaned.split("\n")]
    formatted_lines: list[str] = []

    for line in lines:
        line_str = line.strip()
        if not line_str:
            formatted_lines.append("")
            continue

        # If line is a bullet item and previous line was regular text without empty line, insert double break
        if line_str.startswith(("-", "•", "* ")) and formatted_lines and formatted_lines[-1] != "":
            prev_line = formatted_lines[-1].strip()
            if not prev_line.startswith(("-", "•", "* ")):
                formatted_lines.append("")

        formatted_lines.append(line_str)

    result = "\n".join(formatted_lines)
    return CONSECUTIVE_NEWLINES_PATTERN.sub("\n\n", result).strip()


def strip_formulaic_trailing_emojis(
    text: str, strip_probability: float = 0.70
) -> str:
    """
    Strips formulaic LLM trailing emoji dumps while preserving natural inline emojis.
    Guarantees that >60% of all generated posts end cleanly on punctuation.
    """
    cleaned = text.strip()
    match = TRAILING_EMOJI_PATTERN.search(cleaned)
    if not match:
        return cleaned

    matched_text = match.group(0).strip()
    # If 2+ emojis or generic AI rocket/flame/sparkle clichés, strip with 100% certainty
    is_multi = len(re.findall(r"[\U00010000-\U0010ffff\u2600-\u27ff]", matched_text)) >= 2
    is_cliche = any(c in matched_text for c in ["🚀", "🔥", "✨", "💡", "🤖", "💻", "📈", "🎯", "⚡"])

    if is_multi or is_cliche or random.random() < strip_probability:
        cleaned = TRAILING_EMOJI_PATTERN.sub("", cleaned).rstrip()
        # If stripping removed ending punctuation, restore clean ending
        if cleaned and not cleaned[-1] in ".!?:;'\"`)":
            cleaned += "."
    return cleaned


def enforce_length_cadence(
    text: str, archetype: PostFormattingArchetype, max_hard_limit: int = 280
) -> str:
    """
    Validates and shapes post length based on the chosen archetype's envelope.
    """
    cleaned = text.strip()
    if len(cleaned) <= max_hard_limit:
        return cleaned

    # Smart truncation on sentence boundaries if over hard 280 limit
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    accumulated: list[str] = []
    curr_len = 0

    for s in sentences:
        if curr_len + len(s) + 1 <= max_hard_limit:
            accumulated.append(s)
            curr_len += len(s) + 1
        else:
            break

    if accumulated:
        return " ".join(accumulated).strip()
    return cleaned[: max_hard_limit - 3].rstrip() + "..."
