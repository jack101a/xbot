"""
Topic normalization and extraction utilities for XBot.
"""

from __future__ import annotations

import re


def extract_topic_tag(text: str) -> str:
    """
    Normalizes a topic string, trend headline, or premise into a clean, lowercased topic tag.
    e.g.:
      'One Piece Chapter 1120 - Gear 5 Luffy' -> 'one_piece'
      'Harry Potter HBO Series Casting' -> 'harry_potter'
      'Apple Event iPhone 16 Pro launch' -> 'apple_event'
    """
    if not text:
        return 'general'

    # Remove URLs, hashtags, punctuation
    cleaned = re.sub(r'https?://\S+|#\w+|[^a-zA-Z0-9\s]', ' ', text)
    words = cleaned.strip().lower().split()

    # Common filler words to ignore when extracting core topic entity
    filler = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'of', 'in', 'on', 'for',
        'to', 'and', 'or', 'but', 'just', 'new', 'breaking', 'latest', 'update',
        'official', 'rumor', 'news', 'revealed', 'confirmed', 'leaks', 'teaser',
        'trailer', 'release', 'date', 'why', 'how', 'what', 'when', 'who', 'with',
        'about', 'this', 'that', 'these', 'those', 'over', 'after', 'before'
    }

    meaningful = [w for w in words if w not in filler and len(w) > 1]
    if meaningful:
        return '_'.join(meaningful[:3])
    elif words:
        return '_'.join(words[:2])
    return 'general'
