from __future__ import annotations

import asyncio
import hashlib
import logging
import re

from .detector import TrendItem, fetch_rss_trends

logger = logging.getLogger(__name__)

DEFAULT_CURATED_FEEDS = [
    "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "https://www.techmeme.com/feed.xml",
    "https://hnrss.org/frontpage",
]

DEFAULT_WEB_SEARCH_TREND_QUERIES = [
    "trending Bollywood entertainment controversy today",
    "trending cinema movie viral debate",
    "trending anime manga community discussion",
    "trending AI developer tools launch",
]


async def fetch_web_search_trends(
    queries: list[str] | None = None,
    max_per_query: int = 3,
) -> list[TrendItem]:
    """Fetches real-time breaking trends via live web search (SearXNG / DDGS / Google News)."""
    from xbot.ai.fact_grounder import search_web_grounding
    from xbot.ai.sniper import BANNED_POLITICS_REGEX

    target_queries = queries or DEFAULT_WEB_SEARCH_TREND_QUERIES
    items: list[TrendItem] = []
    seen_hashes: set[str] = set()

    for q in target_queries:
        try:
            snippets = await search_web_grounding(q, max_results=max_per_query)
            for snip in snippets:
                title = snip.get("title", "").strip()
                summary = snip.get("snippet", "").strip()
                url = snip.get("url", "").strip()
                source = snip.get("source", "web_search")

                if not title or BANNED_POLITICS_REGEX.search(f"{title} {summary}"):
                    continue

                raw_id = url or title
                item_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
                if item_id in seen_hashes:
                    continue
                seen_hashes.add(item_id)

                items.append(
                    TrendItem(
                        id=item_id,
                        title=title,
                        summary=summary,
                        source_url=url,
                        source_name=f"Web ({source})",
                        published_at=None,
                    )
                )
        except Exception as e:
            logger.debug("Failed web search trend query '%s': %s", q, e)

    return items


async def fetch_multi_source_trends(
    feed_urls: list[str] | None = None,
    search_queries: list[str] | None = None,
    keywords: list[str] | None = None,
    max_total: int = 15,
) -> list[TrendItem]:
    """Combines curated Google News/Tech feeds and live web search for maximum breaking coverage."""
    from xbot.ai.sniper import BANNED_POLITICS_REGEX

    feeds_to_fetch = feed_urls if feed_urls else DEFAULT_CURATED_FEEDS
    rss_task = fetch_rss_trends(feeds_to_fetch, keywords=keywords, max_items_per_feed=4)
    web_task = fetch_web_search_trends(search_queries, max_per_query=3)

    rss_items, web_items = await asyncio.gather(rss_task, web_task, return_exceptions=True)

    combined: list[TrendItem] = []
    seen_titles: set[str] = set()

    all_raw = []
    if isinstance(web_items, list):
        all_raw.extend(web_items)
    if isinstance(rss_items, list):
        all_raw.extend(rss_items)

    for item in all_raw:
        if BANNED_POLITICS_REGEX.search(f"{item.title} {item.summary}"):
            continue
        clean_title = re.sub(r"[^\w\s]", "", item.title.lower()).strip()
        if clean_title in seen_titles:
            continue
        seen_titles.add(clean_title)
        combined.append(item)
        if len(combined) >= max_total:
            break

    return combined
