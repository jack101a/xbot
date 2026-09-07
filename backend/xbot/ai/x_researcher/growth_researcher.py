"""
Autonomous Growth Researcher & Vision Learner for XBot Pro.

Explores real-time viral tweets on X for:
- "follow for follow" / "f4f"
- "followers growth" / "road to 500" / "1k followers"
- "mutuals connect" / "active creators follow back"

Scrapes viral posts, downloads high-converting media assets,
and uses multimodal vision models to extract design secrets,
typography patterns, and aesthetic prompt recipes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any

from xbot.ai.vision import analyze_viral_growth_media
from xbot.ai.x_researcher.crawler import scrape_x_top_tweets
from xbot.ai.x_researcher.extractor import download_viral_media

logger = logging.getLogger(__name__)

INSIGHTS_FILE = Path("/home/ubuntu/projects/xbot/data/growth_insights.json")
DEFAULT_GROWTH_QUERIES = [
    "follow for follow",
    "followers growth",
    "f4f",
    "mutuals connect",
    "road to 500",
    "active creators follow back",
]


async def research_viral_growth_patterns(
    queries: list[str] | None = None,
    max_tweets: int = 15,
    max_vision_analyses: int = 5,
    profile_slug: str = "test_profile1",
) -> list[dict[str, Any]]:
    """
    Scrapes top viral growth posts from X, downloads media assets,
    and runs vision model analysis to learn high-converting prompt recipes.
    """
    search_queries = queries or DEFAULT_GROWTH_QUERIES[:3]
    logger.info("Starting viral growth research on X for queries: %s", search_queries)

    # 1. Scrape top viral tweets from X
    tweets = await scrape_x_top_tweets(
        queries=search_queries,
        max_tweets=max_tweets,
        profile_slug=profile_slug,
        max_age_days=14,
    )

    if not tweets:
        logger.warning("No viral growth tweets scraped from X.")
        return get_latest_growth_insights()

    # 2. Download media assets from tweets
    topic_slug = f"growth_{int(time.time())}"
    downloaded = await download_viral_media(
        tweets=tweets,
        topic_slug=topic_slug,
        max_images=max_vision_analyses,
    )

    insights: list[dict[str, Any]] = []

    # 3. Vision Model Multimodal Analysis on downloaded media
    for item in downloaded:
        try:
            analysis = await analyze_viral_growth_media(
                image_source=item.local_path,
                tweet_text=item.caption,
            )
            if analysis:
                entry = {
                    "source_tweet_author": item.author_handle,
                    "source_tweet_caption": item.caption,
                    "local_media_path": item.local_path,
                    "vision_analysis": analysis,
                    "synthesized_prompt": analysis.get("synthesized_image_prompt"),
                    "style_category": analysis.get("style_category"),
                    "goal_indicators": analysis.get("goal_indicators", []),
                    "timestamp": time.time(),
                }
                insights.append(entry)
        except Exception as e:
            logger.warning("Vision analysis error on %s: %s", item.local_path, e)

    # 4. Also harvest high-performing text copy patterns
    copy_patterns = []
    for tw in tweets[:8]:
        if len(tw.text.strip()) > 30:
            copy_patterns.append({
                "author": tw.handle,
                "text": tw.text.strip(),
                "likes": tw.likes,
                "retweets": tw.retweets,
            })

    # 5. Persist learned insights to disk
    payload = {
        "updated_at": time.time(),
        "total_insights": len(insights),
        "visual_insights": insights,
        "copy_patterns": copy_patterns,
    }

    try:
        INSIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        INSIGHTS_FILE.write_text(json.dumps(payload, indent=2))
        logger.info("Persisted %d viral growth visual insights to %s", len(insights), INSIGHTS_FILE)
    except Exception as e:
        logger.warning("Could not persist growth insights: %s", e)

    return insights


def get_latest_growth_insights() -> list[dict[str, Any]]:
    """Loads cached vision-learned growth insights from disk."""
    if not INSIGHTS_FILE.exists():
        return []
    try:
        data = json.loads(INSIGHTS_FILE.read_text())
        return data.get("visual_insights", [])
    except Exception:
        return []
