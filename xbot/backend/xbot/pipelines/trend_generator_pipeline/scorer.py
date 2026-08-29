"""
Trend Generator Creation Decision Matrix and Scorer.
"""

from __future__ import annotations

from xbot.models.pipeline import ResearchedTopic
from xbot.persona.loader import Persona


def determine_creation_format(topic: ResearchedTopic, persona: Persona | None = None) -> str:
    """
    Evaluates topic depth, category, media, and keyword semantics to route to
    one of the 4 creation modalities:
    1. 'thread': Deep research (>= 8 posts & long topic, or explicit deep-dive keywords)
    2. 'visual': High visual/humor/lifestyle/infographic appeal
    3. 'poll': Polarizing A/B dilemmas, comparisons, community choices
    4. 'post': Fast news, sharp takes, hot observations (default)
    """
    t_text = (topic.topic or "").lower()
    s_text = (topic.summary or "").lower()
    combined = f"{t_text} {s_text}"
    scraped = topic.scraped_posts or []

    # Visual keywords (memes, infographics, cheatsheets, comics, lifestyle)
    visual_keywords = [
        "meme", "comic", "storyboard", "infographic", "cheatsheet", "cheat sheet",
        "system design", "system architecture", "architecture diagram", "architecture cheatsheet",
        "vlog", "lifestyle", "candid", "photo", "photography",
        "cinema", "nolan", "imax", "relatable", "humor", "funny", "stages of",
        "moment you", "when you", "expectation vs reality", "side by side", "behind the scenes",
        "bts", "diagram", "illustration", "setup", "4-panel", "4:5",
    ]

    # Poll keywords (polarizing dilemmas, comparisons, community choices)
    poll_keywords = [
        " vs ", " vs. ", "versus", " or ", "which ", "choose", "poll", "debate",
        "prefer", "which is better", "what's better", "whats better", "pick one",
        "dilemma", "would you rather", "ranking",
    ]

    # 1. Thread candidate (deep research)
    if (len(scraped) >= 8 and len(topic.topic) > 30) or any(
        kw in combined for kw in ["deep dive", "in-depth breakdown", "mega thread", "complete guide", "masterclass", "full breakdown"]
    ):
        return "thread"

    # 2. Visual candidate
    if topic.source == "visual" or any(kw in combined for kw in visual_keywords):
        return "visual"

    # 3. Poll candidate
    if any(kw in combined for kw in poll_keywords):
        return "poll"

    # 4. Default: Standalone hot take
    return "post"
