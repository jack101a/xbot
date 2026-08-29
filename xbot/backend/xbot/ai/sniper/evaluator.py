from __future__ import annotations
from .constants import *
import json
import logging
import re
from typing import Any
from pydantic import BaseModel, Field
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.client import get_ai_client
from xbot.ai.formatting_engine import (
    enforce_pacing_whitespace,
    strip_formulaic_trailing_emojis,
)
from xbot.config import settings
from xbot.persona.loader import Persona

def _detect_language_vibe(text: str, top_comments: list[Any]) -> str:
    """Detects whether the thread is Pure English or a Hinglish Mix based on vocabulary markers."""
    hinglish_markers = {
        "yaar", "bhai", "sahi", "mein", "nahi", "kya", "hai", "bhi", "toh", "arre",
        "karo", "hoga", "wala", "wali", "matlab", "alag", "kuch", "didi", "bhaiya",
        "sab", "bas", "par", "aur", "ek", "hum", "tum", "aaj", "kal", "kar", "raha",
        "rahi", "gaya", "gayi", "batao", "dekh", "sun", "apna", "apne", "sirf", "bol",
        "jugaad", "chal", "bhook", "neend", "paisa", "paise", "kaam", "zindagi"
    }

    all_text = text.lower()
    for tc in top_comments:
        c_str = tc.get("text", "") if isinstance(tc, dict) else str(tc)
        all_text += " " + c_str.lower()

    words = re.findall(r"\b[a-z]+\b", all_text)
    if not words:
        return "english"

    hinglish_hits = sum(1 for w in words if w in hinglish_markers)
    if hinglish_hits >= 2 or (hinglish_hits / max(1, len(words))) > 0.03:
        return "hinglish"
    return "english"

def clean_text_for_json(text: str) -> str:
    """Clean markdown json wrappers from LLM output."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def clean_raw_reply_text(text: str) -> str:
    """Cleans raw text output when JSON parsing fails."""
    text = clean_text_for_json(text).strip()
    text = re.sub(r'^(?:Reply|Draft|Tweet|Response):\s*', '', text, flags=re.IGNORECASE)
    text = strip_surrounding_quotes(text)
    return text.strip()

