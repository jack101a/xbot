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
from xbot.database import AsyncSessionLocal
from xbot.models.pipeline import PipelineRun, ResearchedTopic
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import load_config
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def discover_candidate_trends(
    profile: Profile,
    r: redis.Redis,
) -> list[dict[str, Any]]:
    """Gathers trending topics from X Trending, X Feed, and RSS feeds."""
    profile_slug = profile.profile_slug
    discovered_topics: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    # 1. Source A: X Explore / Trending tab
    try:
        trend_job = BrowserJob(
            action_type="scrape_trending",
            profile_slug=profile_slug,
            params={"limit": 10},
            priority=4,
        )
        job_id = enqueue_browser_job(trend_job)
        trend_res = await asyncio.to_thread(get_browser_job_result, job_id, 40.0)

        if trend_res and trend_res.get("status") == "success":
            trends_list = trend_res.get("trends", [])
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
        feed_job = BrowserJob(
            action_type="scrape_feed",
            profile_slug=profile_slug,
            params={"scroll_count": 3, "collect_tweets": True},
            priority=4,
        )
        feed_job_id = enqueue_browser_job(feed_job)
        feed_res = await asyncio.to_thread(get_browser_job_result, feed_job_id, 40.0)

        if feed_res and feed_res.get("status") == "success":
            for tw in feed_res.get("tweets", [])[:10]:
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

    # 3. Source C: Curated RSS Feeds
    try:
        config = None
        from pathlib import Path
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists():
            config = load_config(cfg_path)

        rss_items = await fetch_rss_trends(config=config, max_items=8)
        for item in rss_items:
            if item.title and item.title.lower() not in seen_titles:
                seen_titles.add(item.title.lower())
                discovered_topics.append({
                    "topic": item.title,
                    "source": "rss",
                    "summary": item.summary or item.title,
                    "volume": "RSS Feed",
                })
    except Exception as e:
        logger.warning("TrendResearcher: Error fetching RSS trends: %s", e)

    return discovered_topics


async def run_trend_researcher_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_topics_to_research: int = 2,
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
                max_posts=25,
            )

            if report and report.viral_posts:
                scraped_posts_data = [
                    {
                        "tweet_id": p.tweet_id,
                        "author": p.author,
                        "text": p.text,
                        "likes": p.likes,
                        "retweets": p.retweets,
                        "replies": p.replies,
                        "views": p.views,
                        "media_urls": p.media_urls,
                    }
                    for p in report.viral_posts
                ]
                media_file_paths = [m.file_path for m in report.downloaded_media if m.file_path]

                # Store in ResearchedTopic table
                db_topic = ResearchedTopic(
                    profile_id=profile.id,
                    topic=topic_title,
                    summary=report.synthesis_summary or item.get("summary"),
                    source=item.get("source", "x_search"),
                    scraped_posts=scraped_posts_data,
                    media_paths=media_file_paths,
                    processed=False,
                    relevance_score=0.85,
                )
                db.add(db_topic)
                await db.commit()

                # Mark dedup in Redis (6 hour TTL)
                r.set(dedup_key, "1", ex=21600)
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

