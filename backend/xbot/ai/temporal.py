"""
xbot.ai.temporal: Centralized temporal grounding engine.

Ensures all LLM completions (post creation, reply analysis, sniper quotes,
trend research, campaign planning) are permanently and strictly grounded
in the real-world current date, time, and calendar year (e.g. 2026).
Prevents LLMs from hallucinating outdated training-cutoff years (e.g. 2023/2024).
"""

from __future__ import annotations

import datetime
from typing import Any
from zoneinfo import ZoneInfo

TEMPORAL_MARKER = "[REAL-WORLD TEMPORAL ANCHOR"


def get_temporal_anchor(tz_str: str | None = None) -> str:
    """
    Generates a high-priority temporal anchor block with the exact real-world
    date, calendar year, local time, and UTC time, along with strict instructions
    instructing the LLM not to revert to its training cutoff year.
    """
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    if tz_str:
        try:
            now_local = now_utc.astimezone(ZoneInfo(tz_str))
        except Exception:
            now_local = datetime.datetime.now().astimezone()
    else:
        now_local = datetime.datetime.now().astimezone()

    current_year = now_local.strftime("%Y")
    current_date_str = now_local.strftime("%A, %B %d, %Y")
    local_time_str = now_local.strftime("%I:%M:%S %p %Z")
    utc_time_str = now_utc.strftime("%H:%M:%S UTC")

    return (
        f"{TEMPORAL_MARKER} - STRICT REAL-TIME GROUNDING]\n"
        f"• Current Real-World Date: {current_date_str}\n"
        f"• Current Calendar Year: {current_year}\n"
        f"• Current Time: {local_time_str} ({utc_time_str})\n"
        "• CRITICAL TEMPORAL RULES:\n"
        f"  1. The active real-world calendar year is {current_year}. STRICTLY FORBIDDEN to claim or assume the current year is 2023, 2024, or 2025.\n"
        f"  2. Even if your base model training knowledge cut-off occurred earlier, you MUST treat {current_year} as the present moment.\n"
        f"  3. All commentary, references to 'today', 'this year', recent announcements, movie/show releases, tech benchmarks, or events MUST be anchored in {current_year}.\n"
        "=================================================="
    )


def inject_temporal_anchor_to_messages(
    messages: list[dict[str, Any]], tz_str: str | None = None
) -> list[dict[str, Any]]:
    """
    Injects the temporal anchor into a list of OpenAI/LiteLLM chat messages.
    If a system message exists, it appends the anchor to it.
    If no system message exists, it prepends a new system message at index 0.
    """
    if not messages:
        return [{"role": "system", "content": get_temporal_anchor(tz_str)}]

    anchor = get_temporal_anchor(tz_str)
    new_messages: list[dict[str, Any]] = []
    system_found = False

    for msg in messages:
        m_copy = dict(msg)
        if m_copy.get("role") == "system" and not system_found:
            content = str(m_copy.get("content") or "")
            if TEMPORAL_MARKER not in content:
                m_copy["content"] = f"{content.strip()}\n\n{anchor}" if content.strip() else anchor
            system_found = True
        new_messages.append(m_copy)

    if not system_found:
        new_messages.insert(0, {"role": "system", "content": anchor})

    return new_messages


def inject_temporal_anchor_to_prompt(
    prompt: str, tz_str: str | None = None
) -> str:
    """
    Prepends the temporal anchor to a raw string prompt.
    """
    if TEMPORAL_MARKER in prompt:
        return prompt
    anchor = get_temporal_anchor(tz_str)
    return f"{anchor}\n\n{prompt.strip()}"
