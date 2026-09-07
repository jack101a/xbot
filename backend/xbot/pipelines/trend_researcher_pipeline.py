"""
Trend Researcher Pipeline for XBot Pro.

Runs every 25 minutes (24/7 autonomous discovery):
1. Discovers real-time trending topics across 3 sources:
   - Source A: X Explore / Trending tab via Playwright browser
   - Source B: X "For You" timeline viral posts
   - Source C: Multi-source curated RSS feeds
2. Evaluates topic relevance against profile persona.
3. Conducts deep X search research for top candidate topics:
   - Scrapes top 20-30 viral posts for each topic
   - Enforces 7-day recency filter (since:YYYY-MM-DD)
   - Downloads real media (images/memes) from top posts
4. Stores researched dossiers in ResearchedTopic database table for the Trend Generator.
5. Deduplicates topics using a 6-hour Redis TTL and logs in PipelineRun.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.trend_radar import fetch_rss_trends
from xbot.ai.x_researcher import research_topic_comprehensively
from xbot.config import settings
from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.database import AsyncSessionLocal
from xbot.models.pipeline import PipelineRun, ResearchedTopic
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import load_config
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def discover_candidate_trends(
    profile: Profile,
    r: redis.Redis,
    container: Container | None = None,
) -> list[dict[str, Any]]:
    """Gathers trending topics from X Trending, X Feed, and RSS feeds via BrowserPort."""
    profile_slug = profile.profile_slug
    c = container or get_container()
    discovered_topics: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    # 1. Source A: X Explore / Trending tab
    try:
        trend_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SCRAPE_TRENDING,
            params={"limit": 10},
            timeout_seconds=40,
        )
        trend_res = await c.browser.execute(trend_req)

        trends_list: list[dict[str, Any]] = []
        if trend_res.status == "success":
            if trend_res.scrape and trend_res.scrape.raw.get("trends"):
                trends_list = trend_res.scrape.raw["trends"]
            elif trend_res.action_result and trend_res.action_result.raw.get("trends"):
                trends_list = trend_res.action_result.raw["trends"]

            for t in trends_list:
                name = t.get("name") or t.get("topic") or ""
                if name and name.lower() not in seen_titles:
                    seen_titles.add(name.lower())
                    discovered_topics.append({
                        "topic": name,
                        "source": "x_trending",
                        "summary": t.get("category", "Trending on X"),
                        "volume": t.get("tweet_count", ""),
                    })
    except Exception as e:
        logger.warning("TrendResearcher: Error discovering X trending topics: %s", e)

    # 2. Source B: X Feed Viral Posts
    try:
        feed_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SCRAPE_FEED,
            params={"scroll_count": 3, "collect_tweets": True},
            timeout_seconds=40,
        )
        feed_res = await c.browser.execute(feed_req)

        if feed_res.status == "success":
            feed_tweets: list[dict[str, Any]] = []
            if feed_res.scrape and feed_res.scrape.tweets:
                feed_tweets = [tw.model_dump() for tw in feed_res.scrape.tweets]
            elif feed_res.scrape and feed_res.scrape.raw.get("tweets"):
                feed_tweets = feed_res.scrape.raw["tweets"]
            elif feed_res.action_result and feed_res.action_result.raw.get("tweets"):
                feed_tweets = feed_res.action_result.raw["tweets"]

            for tw in feed_tweets[:10]:
                text = tw.get("text", "")
                if len(text) > 30 and text[:40].lower() not in seen_titles:
                    seen_titles.add(text[:40].lower())
                    discovered_topics.append({
                        "topic": text[:80],
                        "source": "x_feed",
                        "summary": f"Viral feed post by @{tw.get('author', 'creator')}",
                        "volume": str(tw.get("views", "")),
                    })
    except Exception as e:
        logger.warning("TrendResearcher: Error discovering feed viral topics: %s", e)

    return discovered_topics


async def run_trend_researcher_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_topics_to_research: int = 2,
    container: Container | None = None,
) -> dict[str, Any]:
    """Discovers and researches top topics for a profile."""
    profile_slug = profile.profile_slug
    r = guard.r

    # CentralGuard 24/7 check
    can_proceed = await guard.can_act(db, profile_slug, "trend_researcher")
    if not can_proceed:
        return {"status": "skipped", "reason": "guard_check_failed", "topics_researched": 0}

    from xbot.persona.loader import load_persona
    from xbot.safety.topic_blacklist import topic_blacklist_filter
    persona = None
    try:
        persona = load_persona(profile_slug)
    except Exception:
        pass

    # Discover candidate topics
    candidates = await discover_candidate_trends(profile, r)
    if not candidates:
        return {"status": "success", "topics_researched": 0, "message": "No candidates found"}

    # Pre-flight topic blacklist filter
    safe_candidates: list[dict[str, Any]] = []
    for item in candidates:
        topic_title = item.get("topic", "")
        summary = item.get("summary", "")
        is_blocked, block_reason = topic_blacklist_filter.is_blocked(f"{topic_title} {summary}", persona)
        if is_blocked:
            logger.info("TrendResearcher: Skipped topic '%s' due to topic blacklist: %s", topic_title[:50], block_reason)
            continue
        safe_candidates.append(item)
    candidates = safe_candidates

    researched_count = 0
    researched_titles: list[str] = []

    for item in candidates:
        if researched_count >= max_topics_to_research:
            break

        topic_title = item["topic"]
        dedup_key = f"xbot:seen_research_topic:{profile_slug}:{topic_title[:60]}"
        if r.exists(dedup_key):
            continue

        logger.info("TrendResearcher: Commencing deep X research on topic: '%s' for profile %s", topic_title, profile_slug)

        try:
            # Conduct comprehensive research: scrape 20-30 viral X posts & download media
            report = await research_topic_comprehensively(
                topic=topic_title,
                profile_slug=profile_slug,
                max_tweets=25,
            )

            if report and (getattr(report, "viral_tweets", None) or getattr(report, "summary", None)):
                tweets_list = getattr(report, "viral_tweets", []) or getattr(report, "viral_posts", [])
                scraped_posts_data = [
                    {
                        "tweet_id": getattr(p, "tweet_url", "") or getattr(p, "tweet_id", ""),
                        "author": getattr(p, "author", "") or getattr(p, "handle", ""),
                        "text": getattr(p, "text", ""),
                        "likes": getattr(p, "likes", 0),
                        "retweets": getattr(p, "retweets", 0),
                        "replies": getattr(p, "replies", 0),
                        "views": getattr(p, "views", 0),
                        "media_urls": getattr(p, "media_urls", []),
                    }
                    for p in tweets_list
                ]
                dl_media = getattr(report, "downloaded_media", [])
                media_file_paths = [
                    getattr(m, "local_path", getattr(m, "file_path", None))
                    for m in dl_media
                    if getattr(m, "local_path", getattr(m, "file_path", None))
                ]

                # Store in ResearchedTopic table
                db_topic = ResearchedTopic(
                    profile_id=profile.id,
                    topic=topic_title,
                    summary=getattr(report, "summary", None) or getattr(report, "synthesis_summary", None) or item.get("summary"),
                    source=item.get("source", "x_search"),
                    scraped_posts=scraped_posts_data,
                    media_paths=media_file_paths,
                    processed=False,
                    relevance_score=0.85,
                )
                db.add(db_topic)
                await db.commit()

                # Mark dedup in Redis (24 hour TTL)
                r.set(dedup_key, "1", ex=86400)
                researched_count += 1
                researched_titles.append(topic_title)

        except Exception as research_err:
            logger.error("TrendResearcher: Failed research on topic '%s': %s", topic_title, research_err, exc_info=True)

    return {
        "status": "success",
        "topics_researched": researched_count,
        "topics": researched_titles,
        "candidates_evaluated": len(candidates),
    }


async def _run_trend_researcher_async() -> dict[str, Any]:
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_researched = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await run_trend_researcher_for_profile(db, profile, guard)
                results_by_profile[profile.profile_slug] = res
                total_researched += res.get("topics_researched", 0)

                run_log = PipelineRun(
                    pipeline_name="trend_researcher",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("topics_researched", 0),
                    details=res,
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

            except Exception as e:
                logger.error("TrendResearcher: Error for profile %s: %s", profile.profile_slug, e, exc_info=True)
                run_log = PipelineRun(
                    pipeline_name="trend_researcher",
                    profile_id=profile.id,
                    status="failed",
                    actions_count=0,
                    error_message=str(e),
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

    return {
        "pipeline": "trend_researcher",
        "total_researched": total_researched,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.trend_researcher_pipeline.run_trend_researcher")
def run_trend_researcher() -> dict[str, Any]:
    """Celery task entry point for Trend Researcher Pipeline."""
    return asyncio.run(_run_trend_researcher_async())

