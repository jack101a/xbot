from __future__ import annotations
import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.config import settings
from .constants import *
from .models import HookCandidate

def extract_links(text: str) -> tuple[str, str | None]:
    """
    Strips external links from text to avoid the -70% to -80% algorithmic reach penalty
    and isolates the primary URL for 1st-reply injection.
    """
    if not text:
        return "", None

    matches = LINK_REGEX.findall(text)
    extracted_link = matches[0].rstrip(".,;:!?") if matches else None

    # Replace markdown link syntax [text](url) -> text
    clean_text = re.sub(r'\[([^\]]+)\]\((?:https?://|www\.)[^\s)]+\)', r'\1', text)

    # Remove remaining URLs
    clean_text = LINK_REGEX.sub('', clean_text)

    # Clean up empty brackets, parens, trailing 'link:', 'url:', etc.
    clean_text = re.sub(r'\(\s*\)', '', clean_text)
    clean_text = re.sub(r'\[\s*\]', '', clean_text)
    clean_text = re.sub(r'(?:link|url|source|read more):\s*$', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)

    # Clean multiple spaces on each line
    lines = []
    for line in clean_text.split('\n'):
        line_clean = re.sub(r'[ \t]+', ' ', line).strip()
        lines.append(line_clean)

    # Collapse multiple blank lines
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result).strip()
    return result, extracted_link

def calculate_bookmark_score(text: str) -> float:
    """
    Evaluates bookmark-bait utility based on numbered frameworks, action steps,
    cheat sheets, checklists, and high-density formatting (1.0 to 10.0).
    """
    if not text or not text.strip():
        return 1.0

    clean_text = text.strip()
    score = 2.5  # Base score

    # 1. Numbered items / action steps / bullets
    list_item_pattern = re.compile(
        r'^\s*(?:\d+[\.\)]|step\s*\d+[:\.]?|rule\s*\d+[:\.]?|phase\s*\d+[:\.]?|part\s*\d+[:\.]?|[•\-\*])\s+',
        re.IGNORECASE | re.MULTILINE,
    )
    list_matches = list_item_pattern.findall(clean_text)
    num_items = len(list_matches)

    if num_items >= 5:
        score += 3.5
    elif num_items >= 3:
        score += 2.5
    elif num_items >= 1:
        score += 1.5

    # 2. High-utility bookmark keywords
    text_lower = clean_text.lower()
    keyword_hits = sum(1 for kw in BOOKMARK_KEYWORDS if kw in text_lower)
    score += min(3.5, keyword_hits * 1.0)

    # 3. Multiline structure & formatting
    paragraphs = [p for p in clean_text.split('\n\n') if p.strip()]
    if len(paragraphs) >= 2 or '\n' in clean_text:
        score += 1.0

    # 4. Code snippets or monospaced text
    if '`' in clean_text:
        score += 0.5

    return max(1.0, min(10.0, round(score, 1)))

def trim_open_loop_hook(text: str, max_len: int = 99) -> str:
    """Cleans and trims hook to strictly <100 characters for mobile fold retention."""
    text = clean_hook_text(text).strip()
    if len(text) <= max_len:
        return text
    # Try to trim at punctuation boundary before max_len
    trimmed = text[:max_len]
    last_punct = max(trimmed.rfind('.'), trimmed.rfind('?'), trimmed.rfind('!'), trimmed.rfind(':'))
    if last_punct > 40:
        return trimmed[:last_punct + 1].strip()
    last_space = trimmed.rfind(' ')
    if last_space > 40:
        return trimmed[:last_space].strip()
    return trimmed.strip()

def clean_text_for_json(text: str) -> str:
    """Clean markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def clean_hook_text(text: str) -> str:
    """Cleans hook text of quotes and archetype prefixes."""
    text = text.strip()
    # Remove archetype / label prefixes like "Contrarian: ", "Hook 1: ", etc.
    text = re.sub(
        r"^(?:curiosity[_\s-]?gap|contrarian|framework[_\s-]?breakdown|story[_\s-]?relatable|hook\s*\d*|opening|option\s*\d*):\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.strip().strip('"\'`')
    if len(text) > 140:
        text = text[:140].strip()
    return text

def format_optimized_post(draft_content: str, winning_hook_text: str) -> str:
    """
    Formats the post by substituting the draft's opening line with the winning hook
    and applying micro-spacing to maximize dwell time on the X feed.
    """
    draft = draft_content.strip()
    hook = winning_hook_text.strip()
    if not draft:
        return hook

    # Case 1: Multiple paragraphs separated by double newlines
    paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        body = "\n\n".join(paragraphs[1:])
        return f"{hook}\n\n{body}"

    # Case 2: Multiple lines separated by single newlines
    lines = [l.strip() for l in draft.split("\n") if l.strip()]
    if len(lines) > 1:
        body = "\n\n".join(lines[1:])
        return f"{hook}\n\n{body}"

    # Case 3: Single paragraph with multiple sentences
    sentences = re.split(r"(?<=[.!?])\s+", draft)
    if len(sentences) > 1:
        body = "\n\n".join(sentences[1:])
        return f"{hook}\n\n{body}"

    return hook

def _get_persona_field(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safely extracts nested field from persona object or dict."""
    current = obj
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        else:
            current = getattr(current, key, None)
    return current if current is not None else default

def _normalize_candidate(raw: dict[str, Any], default_archetype: str = "curiosity_gap") -> HookCandidate | None:
    """Normalizes a raw candidate dict into a validated HookCandidate."""
    if not isinstance(raw, dict):
        return None

    raw_archetype = str(raw.get("archetype") or default_archetype).strip().lower()
    archetype = ARCHETYPE_ALIASES.get(raw_archetype, default_archetype)
    if archetype not in VALID_ARCHETYPES:
        archetype = "curiosity_gap"

    hook_text = clean_hook_text(str(raw.get("hook_text") or raw.get("hook") or raw.get("text") or ""))
    if not hook_text:
        return None

    try:
        score = float(raw.get("score", 5.0))
        score = max(1.0, min(10.0, score))
    except (ValueError, TypeError):
        score = 5.0

    reasoning = str(raw.get("reasoning") or raw.get("explanation") or "").strip()

    return HookCandidate(
        archetype=archetype,  # type: ignore[arg-type]
        hook_text=hook_text,
        score=score,
        reasoning=reasoning,
    )

