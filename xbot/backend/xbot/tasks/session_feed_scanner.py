"""
Session Feed Scanner Submodule.
Scrapes feed snapshot, audits target creator (KOL) opportunities, performs niche search, and ingests live trends.
"""

from __future__ import annotations

import logging
import random
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks

logger = logging.getLogger("xbot.tasks.session_feed_scanner")


async def scan_session_feed(
    page: Any,
    profile_id: uuid.UUID,
    profile_slug: str,
    persona: Any,
    manager: Any,
    config: Any,
    db: AsyncSession,
    is_mock: bool = False,
    session_id: uuid.UUID | None = None,
) -> list[dict[str, Any]]:
    """Gathers live feed tweets, creator KOL opportunities, niche searches, and breaking trends."""
    if is_mock:
        feed_snapshot = [
            {
                "author": "@tech_insider",
                "text": "AI agents are transforming software engineering in 2026! What are your thoughts on autonomous coding assistants?",
                "likes": "142",
                "retweets": "35",
                "url": "https://x.com/tech_insider/status/1234567890",
            },
            {
                "author": "@saas_builder",
                "text": "Just launched our new SaaS analytics dashboard! Consistency and customer feedback are everything.",
                "likes": "89",
                "retweets": "12",
                "url": "https://x.com/saas_builder/status/1234567891",
            },
            {
                "author": "@ai_researcher",
                "text": "Deep learning scaling laws vs algorithmic efficiency: why small specialized models are winning in production environments.",
                "likes": "310",
                "retweets": "64",
                "url": "https://x.com/ai_researcher/status/1234567892",
            },
        ]
        if session_id:
            tasks.broadcast_session_log(
                session_id,
                "mock_mode_active",
                {"message": "🧪 [MOCK / DEMO MODE ACTIVE] Running session with simulated X feed. No live requests sent to X."},
            )
        return feed_snapshot

    feed_snapshot: list[dict[str, Any]] = []

    # 1. Scrape feed
    browse_feed = tasks.BrowseFeed()
    try:
        scraped = await browse_feed.execute(page, max_scrolls=1)
        if scraped:
            feed_snapshot.extend(scraped)
    except Exception as e:
        logger.warning("Feed browsing encountered non-fatal error: %s", e)

    # 2. Live Opportunity Hunting: Scan target creators (KOLs) defined in persona
    try:
        if persona and getattr(persona, "target_kols", None):
            checker = tasks.CheckUserLatestTweet()
            shuffled_kols = list(persona.target_kols)
            random.shuffle(shuffled_kols)

            for kol in shuffled_kols[:5]:
                clean_h = kol.handle.lstrip("@")
                try:
                    logger.info("Scanning target creator @%s for live reply opportunities...", clean_h)
                    kol_tweet = await checker.execute(page, handle=clean_h)
                    if kol_tweet and kol_tweet.get("text"):
                        t_url = kol_tweet.get("url") or f"https://x.com/{clean_h}"

                        # Deduplication: check if we already replied or liked in last 48h
                        already_replied = await tasks.has_already_acted(db, profile_id, t_url, "reply", hours=48)
                        already_liked = await tasks.has_already_acted(db, profile_id, t_url, "like", hours=48)

                        if already_replied or already_liked:
                            logger.info("Skipping creator tweet %s: already replied/liked in last 48h", t_url)
                            continue

                        already_quoted = await tasks.has_already_acted(db, profile_id, t_url, "quote", hours=48)

                        feed_snapshot.append({
                            "author": clean_h,
                            "text": kol_tweet.get("text"),
                            "url": t_url,
                            "likes": kol_tweet.get("likes", 0),
                            "retweets": kol_tweet.get("retweets", 0),
                            "replies": kol_tweet.get("replies", 0),
                            "top_comments": kol_tweet.get("top_comments", []),
                            "already_replied": already_replied,
                            "already_quoted": already_quoted,
                        })
                except Exception as k_err:
                    logger.warning("Could not check target creator @%s: %s", clean_h, k_err)
    except Exception as p_err:
        logger.warning("Error during KOL opportunity scanning: %s", p_err)

    # 2b. High-Signal Domain Search: Scan for relevant niche discussions
    try:
        target_topics = getattr(persona, "content_pillars", []) or ["technology", "cinema", "AI", "gaming"]
        if target_topics:
            chosen_topic = random.choice(target_topics)
            search_q = f"{chosen_topic} min_faves:50 lang:en"
            logger.info("Searching high-signal discussions on live X Search: %s", search_q)
            searcher = tasks.SearchQuery()
            niche_results = await searcher.execute(page, query=search_q)
            for nr in (niche_results or [])[:4]:
                n_url = nr.get("url")
                if n_url and await tasks.has_already_acted(db, profile_id, n_url, "reply", hours=168):
                    continue
                feed_snapshot.append({
                    "author": nr.get("author", "creator"),
                    "text": nr.get("text", ""),
                    "url": n_url,
                    "is_blue_tick": nr.get("is_blue_tick", False),
                    "likes": nr.get("likes", 50),
                    "retweets": nr.get("retweets", 10),
                    "replies": nr.get("replies", 15),
                })
    except Exception as s_err:
        logger.warning("Niche topic search scan encountered non-fatal error: %s", s_err)

    # 3. Live Trends Ingestion: Fetch breaking trends and viral discussions
    try:
        from xbot.ai.trend_radar import fetch_rss_trends
        rss_urls = [
            "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=en-IN&gl=IN&ceid=IN%3Aen",
            "https://feeds.feedburner.com/TechCrunch/",
        ]
        live_trends = await fetch_rss_trends(rss_urls[:2], max_items_per_feed=3)
        for tr in (live_trends or [])[:4]:
            feed_snapshot.append({
                "author": f"LiveNews ({tr.source_name})",
                "text": f"🔥 [BREAKING NEWS/TOPIC FOR STANDALONE POST ONLY]: {tr.title}",
                "url": None,
                "type": "trend_topic",
                "is_news_article": True,
            })
    except Exception as t_err:
        logger.debug("Trend pre-scan skipped or failed: %s", t_err)

    logger.info("Total live opportunities & trends assembled in feed snapshot: %d items", len(feed_snapshot))
    return feed_snapshot
