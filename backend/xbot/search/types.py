"""
xbot.search.types: Core types and enumerations for X search query construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SearchTarget(str, Enum):
    """Execution target for search queries."""
    WEB = "web"  # Scraped via Playwright on x.com/search (requires Web/X Pro operators)
    API = "api"  # Programmatic X API v2 (requires API operators)


class SearchCategory(str, Enum):
    """Result category / tab on X.com."""
    TOP = "top"          # Ranked by engagement and relevance (default URL)
    LATEST = "live"      # Reverse-chronological live stream (&f=live)
    MEDIA = "media"      # Photos and videos (&f=media)
    PEOPLE = "user"      # Account search (&f=user)


@dataclass
class SearchFilters:
    """Configurable filter parameters for X search queries."""
    keywords: list[str] = field(default_factory=list)
    exact_phrases: list[str] = field(default_factory=list)
    excluded_terms: list[str] = field(default_factory=list)
    min_faves: Optional[int] = None        # Web: min_faves, API: min_likes
    min_retweets: Optional[int] = None     # Web: min_retweets, API: min_reposts
    exclude_retweets: bool = True          # Web: -filter:retweets, API: -is:retweet
    require_media: bool = False            # Web: filter:media, API: has:media
    require_verified: bool = False         # Web: filter:verified, API: is:verified
    since_date: Optional[str] = None       # Format: YYYY-MM-DD
    until_date: Optional[str] = None       # Format: YYYY-MM-DD
    category: SearchCategory = SearchCategory.TOP
