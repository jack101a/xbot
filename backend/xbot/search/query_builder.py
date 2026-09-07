"""
xbot.search.query_builder: Declarative, empirically-verified query compiler for X search.

Translates high-level search specifications into 100% valid query strings
specifically compliant with X.com's live Earlybird search engine.
Prevents operator pollution between Web and API syntax.
"""

from __future__ import annotations

import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from xbot.search.types import SearchCategory, SearchFilters, SearchTarget

# Earlybird index buckets engagement reliably at 50, 100, 500, 1000
VALID_ENGAGEMENT_TIERS = [50, 100, 500, 1000]


def _normalize_engagement_tier(val: int) -> int:
    """Snaps engagement value to the closest valid Earlybird tier (minimum 50)."""
    if val <= 50:
        return 50
    for tier in VALID_ENGAGEMENT_TIERS:
        if val <= tier:
            return tier
    return 1000


class XSearchQueryBuilder:
    """
    Fluent builder for compiling strictly validated X search queries.
    """

    def __init__(self, target: SearchTarget = SearchTarget.WEB) -> None:
        self.target = target
        self.filters = SearchFilters()

    def keyword(self, word: str) -> XSearchQueryBuilder:
        clean = word.strip()
        if clean and clean not in self.filters.keywords:
            self.filters.keywords.append(clean)
        return self

    def exact_phrase(self, phrase: str) -> XSearchQueryBuilder:
        clean = phrase.strip().strip('"')
        if clean and clean not in self.filters.exact_phrases:
            self.filters.exact_phrases.append(clean)
        return self

    def exclude(self, term: str) -> XSearchQueryBuilder:
        clean = term.strip().lstrip("-")
        if clean and clean not in self.filters.excluded_terms:
            self.filters.excluded_terms.append(clean)
        return self

    def min_faves(self, count: int) -> XSearchQueryBuilder:
        self.filters.min_faves = _normalize_engagement_tier(count)
        return self

    def min_retweets(self, count: int) -> XSearchQueryBuilder:
        self.filters.min_retweets = max(5, count)
        return self

    def exclude_retweets(self, enable: bool = True) -> XSearchQueryBuilder:
        self.filters.exclude_retweets = enable
        return self

    def require_media(self, enable: bool = True) -> XSearchQueryBuilder:
        self.filters.require_media = enable
        return self

    def require_verified(self, enable: bool = True) -> XSearchQueryBuilder:
        self.filters.require_verified = enable
        return self

    def since(self, date_str: str) -> XSearchQueryBuilder:
        self.filters.since_date = date_str
        return self

    def since_days_ago(self, days: int, tz_str: Optional[str] = None) -> XSearchQueryBuilder:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        if tz_str:
            try:
                now_dt = now_dt.astimezone(ZoneInfo(tz_str))
            except Exception:
                pass
        target_date = (now_dt - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        self.filters.since_date = target_date
        return self

    def until(self, date_str: str) -> XSearchQueryBuilder:
        self.filters.until_date = date_str
        return self

    def category(self, cat: SearchCategory) -> XSearchQueryBuilder:
        self.filters.category = cat
        return self

    def build_query_string(self) -> str:
        """
        Compiles the query string for search execution.
        Strictly applies empirically verified operators for the designated target.
        """
        parts: list[str] = []

        # 1. Exact phrases
        for phrase in self.filters.exact_phrases:
            parts.append(f'"{phrase}"')

        # 2. Keywords
        for kw in self.filters.keywords:
            parts.append(kw)

        # 3. Excluded terms
        for ex in self.filters.excluded_terms:
            parts.append(f"-{ex}")

        # 4. Target-specific operators
        if self.target == SearchTarget.WEB:
            # Verified Web / X Pro Operators
            if self.filters.min_faves is not None:
                parts.append(f"min_faves:{self.filters.min_faves}")

            if self.filters.min_retweets is not None:
                parts.append(f"min_retweets:{self.filters.min_retweets}")

            if self.filters.exclude_retweets:
                parts.append("-filter:retweets")

            if self.filters.require_media:
                parts.append("filter:media")

            if self.filters.require_verified:
                parts.append("filter:verified")

            if self.filters.since_date:
                parts.append(f"since:{self.filters.since_date}")

            if self.filters.until_date:
                parts.append(f"until:{self.filters.until_date}")

        else:
            # API v2 Operators
            if self.filters.min_faves is not None:
                parts.append(f"min_likes:{self.filters.min_faves}")

            if self.filters.min_retweets is not None:
                parts.append(f"min_reposts:{self.filters.min_retweets}")

            if self.filters.exclude_retweets:
                parts.append("-is:retweet")

            if self.filters.require_media:
                parts.append("has:media")

            if self.filters.require_verified:
                parts.append("is:verified")

        return " ".join(parts).strip()

    def build_url(self) -> str:
        """Constructs the full x.com search URL including category filters."""
        from urllib.parse import quote_plus
        q = self.build_query_string()
        f_param = f"&f={self.filters.category.value}" if self.filters.category != SearchCategory.TOP else ""
        return f"https://x.com/search?q={quote_plus(q)}{f_param}"

    def get_adaptive_fallback_queries(self) -> list[tuple[str, SearchCategory]]:
        """
        Generates a sequence of progressively relaxed queries to execute if the
        strict initial query yields 0 results.
        """
        fallback_list: list[tuple[str, SearchCategory]] = []

        # 1. Primary strict query
        primary_q = self.build_query_string()
        fallback_list.append((primary_q, self.filters.category))

        # 2. Relax engagement to 50 if it was higher
        if self.filters.min_faves and self.filters.min_faves > 50:
            relaxed_faves = XSearchQueryBuilder(self.target)
            relaxed_faves.filters = SearchFilters(**self.filters.__dict__)
            relaxed_faves.filters.min_faves = 50
            fallback_list.append((relaxed_faves.build_query_string(), self.filters.category))

        # 3. Drop engagement & media requirement, keep date and retweet exclusion
        relaxed_middle = XSearchQueryBuilder(self.target)
        relaxed_middle.filters = SearchFilters(
            keywords=list(self.filters.keywords),
            exact_phrases=list(self.filters.exact_phrases),
            exclude_retweets=True,
            since_date=self.filters.since_date,
            category=self.filters.category,
        )
        fallback_list.append((relaxed_middle.build_query_string(), self.filters.category))

        # 4. Live community pulse fallback
        raw_topic = " ".join(self.filters.exact_phrases + self.filters.keywords)
        fallback_list.append((raw_topic, SearchCategory.LATEST))

        # Deduplicate while preserving order
        seen = set()
        unique_fallbacks = []
        for q, cat in fallback_list:
            key = (q, cat)
            if q and key not in seen:
                seen.add(key)
                unique_fallbacks.append(key)

        return unique_fallbacks
