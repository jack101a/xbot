from __future__ import annotations

# Re-export facade for backward compatibility
from xbot.ai.trend_radar import (
    DEFAULT_CURATED_FEEDS,
    DEFAULT_WEB_SEARCH_TREND_QUERIES,
    TrendItem,
    _clean_text,
    _fetch_single_feed,
    _find_child_by_tags,
    _get_child_text,
    _is_recent_timestamp,
    _parse_atom_entry,
    _parse_rss_item,
    _strip_ns,
    fetch_multi_source_trends,
    fetch_rss_trends,
    fetch_web_search_trends,
    parse_feed_xml,
)

__all__ = [
    "DEFAULT_CURATED_FEEDS",
    "DEFAULT_WEB_SEARCH_TREND_QUERIES",
    "TrendItem",
    "_clean_text",
    "_fetch_single_feed",
    "_find_child_by_tags",
    "_get_child_text",
    "_is_recent_timestamp",
    "_parse_atom_entry",
    "_parse_rss_item",
    "_strip_ns",
    "fetch_multi_source_trends",
    "fetch_rss_trends",
    "fetch_web_search_trends",
    "parse_feed_xml",
]
