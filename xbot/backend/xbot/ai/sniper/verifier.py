from __future__ import annotations
import re
from typing import Any
from pydantic import BaseModel, Field
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from .constants import *

class SniperResult(BaseModel):
    response_mode: str = Field(
        default="witty_sarcasm",
        description="Response mode: pure_gif, emoji_reaction, punchy_one_liner, witty_sarcasm, casual_take, in_depth_breakdown",
    )
    reply_text: str = Field(..., description="The drafted high-value reply text (natural length, sentence case)")
    debate_catalyst: str = Field(default="", description="Optional closing question or hook if asked")
    angle: str = Field(default="insight", description="The angle chosen: contrarian, framework, question, witty, data, or insight")
    angle_used: str | None = Field(default=None, description="Backwards compatibility alias for angle")
    gif_query: str | None = Field(default=None, description="Search term for Tenor/X GIF picker or None")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", description="Brief explanation of the chosen response mode and angle")

    def __init__(self, **data: Any) -> None:
        if "reply_text" in data and isinstance(data["reply_text"], str):
            data["reply_text"] = strip_surrounding_quotes(data["reply_text"].strip())
        if "debate_catalyst" in data and isinstance(data["debate_catalyst"], str):
            data["debate_catalyst"] = strip_surrounding_quotes(data["debate_catalyst"].strip())

        if "response_mode" in data and isinstance(data["response_mode"], str):
            mode = data["response_mode"].strip().lower()
            data["response_mode"] = mode if mode in VALID_RESPONSE_MODES else "witty_sarcasm"
        else:
            data["response_mode"] = "witty_sarcasm"

        if "angle" in data and "angle_used" not in data:
            data["angle_used"] = data["angle"]
        elif "angle_used" in data and "angle" not in data:
            data["angle"] = data["angle_used"]
        elif "angle" not in data and "angle_used" not in data:
            data["angle"] = "insight"
            data["angle_used"] = "insight"

        if "debate_catalyst" not in data or not data["debate_catalyst"]:
            reply = data.get("reply_text", "")
            if reply:
                questions = re.findall(r'([^.!?\n]+\?)', reply)
                if questions:
                    data["debate_catalyst"] = questions[-1].strip()
                elif reply.strip().endswith("?"):
                    data["debate_catalyst"] = reply.strip()
                else:
                    data["debate_catalyst"] = ""
            else:
                data["debate_catalyst"] = ""
        super().__init__(**data)

SniperReplyResult = SniperResult
DynamicReplyResult = SniperResult

class QuoteTakeResult(BaseModel):
    quote_text: str = Field(..., description="The drafted high-value standalone quote take")
    gif_query: str | None = Field(default=None, description="Search term for Tenor/X GIF picker or None")
    reasoning: str = Field(default="", description="Strategic rationale for the quote take")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    topic_understanding: str = Field(default="", description="Brief breakdown of what the target post and room are about")

def verify_sniper_reply(
    reply_text: str,
    language_mode: str = "english",
    target_text: str | None = None,
    response_mode: str | None = None,
    gif_query: str | None = None,
) -> tuple[bool, str | None]:
    """
    Validates candidate reply against quality, safety, and domain-matching gatekeepers.
    Supports short replies, emoji reactions, and GIF queries without artificial length barriers.
    Returns (is_valid, failure_reason).
    """
    text = reply_text.strip()
    if response_mode == "pure_gif" and gif_query:
        pass
    elif not text:
        return False, "Empty reply text."

    # Stage 1: Length Constraint (No fixed minimums, maximum 280 chars)
    if len(text) > 280:
        return False, f"Length exceeds 280 characters ({len(text)} chars)."

    # Stage 2: Cliché & Negative Token Filters
    if BANNED_AI_WORDS_REGEX.search(text):
        m = BANNED_AI_WORDS_REGEX.search(text)
        return False, f"Contains banned AI academic word: '{m.group(0)}'."

    if BANNED_BOT_PRAISE_REGEX.search(text):
        return False, "Contains generic bot praise."

    if BANNED_ROUTINE_FILLER_REGEX.search(text):
        m = BANNED_ROUTINE_FILLER_REGEX.search(text)
        return False, f"Contains banned routine/beverage filler: '{m.group(0)}'."

    # Stage 3: Language Mode Adherence
    if language_mode == "english":
        hinglish_leak_markers = {"yaar", "bhai", "sahi", "mein", "kya", "hai", "arre", "matlab", "didi", "bhaiya"}
        words = set(re.findall(r"\b[a-z]+\b", text.lower()))
        leaks = words.intersection(hinglish_leak_markers)
        if leaks:
            return False, f"Language mode is Pure English but found Hindi words: {list(leaks)}."

    # Stage 4: Cross-Domain Contamination Gatekeeper
    if target_text:
        t_low = target_text.lower()
        r_low = text.lower()
        is_tech_target = any(k in t_low for k in TECH_KEYWORDS) and not any(k in t_low for k in ANIME_KEYWORDS)
        is_anime_target = any(k in t_low for k in ANIME_KEYWORDS) and not any(k in t_low for k in TECH_KEYWORDS)

        if is_tech_target:
            anime_contaminants = {"oda", "luffy", "zoro", "god valley", "anime", "manga", "powerscaling", "shonen", "chapter"}
            hits = [w for w in anime_contaminants if re.search(r"\b" + re.escape(w) + r"\b", r_low)]
            if hits:
                return False, f"Domain mismatch: Target post is tech, but reply contains anime keywords: {hits}."

        if is_anime_target:
            tech_contaminants = {"macbook", "gpu", "snapdragon", "m4 max", "benchmark", "nvidia", "intel", "semiconductor"}
            hits = [w for w in tech_contaminants if re.search(r"\b" + re.escape(w) + r"\b", r_low)]
            if hits:
                return False, f"Domain mismatch: Target post is anime, but reply contains tech hardware keywords: {hits}."

    # Stage 5: Banned Robotic Survey Questions Gatekeeper
    if BANNED_ROBOTIC_QUESTIONS_REGEX.search(text):
        m = BANNED_ROBOTIC_QUESTIONS_REGEX.search(text)
        return False, f"Contains robotic survey question: '{m.group(0)}'. Keep reply as a natural statement or banter."

    # Stage 6: Hard Indian Politics Blacklist
    if BANNED_POLITICS_REGEX.search(text):
        m = BANNED_POLITICS_REGEX.search(text)
        return False, f"Contains banned Indian political terms: '{m.group(0)}'."

    if target_text and BANNED_POLITICS_REGEX.search(target_text):
        return False, "Target post is related to Indian politics. Rejected by political safety filter."

    return True, None

