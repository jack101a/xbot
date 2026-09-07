from __future__ import annotations

import logging
from typing import Any

from xbot.container import Container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.pipelines.instant_trend.types import TrendCandidateTweet

logger = logging.getLogger(__name__)


async def search_x_for_trending_topic(
    container: Container,
    profile_slug: str,
    topic: str,
    timeout_seconds: int = 45,
) -> list[TrendCandidateTweet]:
    """
    Researches a trending topic STRICTLY on X.com via live Search DOM.
    Bypasses external search engines entirely.
    """
    logger.info("InstantTrend: Searching X for topic: '%s' using profile: %s", topic, profile_slug)
    candidates: list[TrendCandidateTweet] = []

    # Clean and query X live search directly using verified SearchMatrixStrategy
    clean_topic = topic.strip()
    if not clean_topic:
        return candidates

    try:
        from xbot.search import SearchMatrixStrategy, SearchTarget
        builder = SearchMatrixStrategy.create_viral_anchor_query(
            topic=clean_topic,
            min_faves=50,
            max_age_days=7,
            require_media=True,
            target=SearchTarget.WEB,
        )
        query = builder.build_query_string()
        search_filter = builder.filters.category.value

        req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SEARCH,
            params={
                "query": query,
                "search_filter": search_filter,
                "auto_relax": True,
            },
            timeout_seconds=timeout_seconds,
        )
        res = await container.browser.execute(req)

        if res.status not in ("success", "ok"):
            logger.warning("InstantTrend: Search failed or timed out on X: %s", res.error)
            return candidates

        # Handle parsed results from Search action
        results_data: list[dict[str, Any]] = []
        if res.scrape and res.scrape.tweets:
            for tw in res.scrape.tweets:
                results_data.append({
                    "tweet_id": tw.tweet_id,
                    "text": tw.text,
                    "url": tw.url,
                    "author": tw.handle,
                    "is_blue_tick": tw.is_pinned or False,  # fallback flag
                    "media_urls": tw.media_urls,
                    "media_alts": tw.media_alts,
                    "hashtags": tw.hashtags,
                    "has_video": tw.has_video,
                })
        elif res.action_result:
            if hasattr(res.action_result, "raw") and isinstance(res.action_result.raw, dict):
                results_data = res.action_result.raw.get("results") or []
            elif isinstance(res.action_result, dict):
                results_data = res.action_result.get("results") or []

        for raw in results_data:
            t_id = str(raw.get("tweet_id") or "")
            t_url = raw.get("url") or (f"https://x.com/i/web/status/{t_id}" if t_id else "")
            text = (raw.get("text") or "").strip()

            if not text or not t_url:
                continue

            # Fallback tweet ID extraction from url if not provided
            if not t_id and "/status/" in t_url:
                t_id = t_url.split("/status/")[-1].split("?")[0].strip("/")

            candidates.append(
                TrendCandidateTweet(
                    tweet_id=t_id or t_url,
                    text=text,
                    url=t_url,
                    author=raw.get("author") or "creator",
                    is_blue_tick=bool(raw.get("is_blue_tick", False)),
                    media_urls=raw.get("media_urls") or [],
                    media_alts=raw.get("media_alts") or [],
                    hashtags=raw.get("hashtags") or [],
                    has_video=bool(raw.get("has_video", False)),
                    is_growth_thread=bool(raw.get("is_growth_thread", False)),
                )
            )

        logger.info("InstantTrend: Found %d candidate tweets on X for '%s'.", len(candidates), topic)
    except Exception as e:
        logger.error("InstantTrend: Error during X search for '%s': %s", topic, e)

    return candidates
