from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import random
import re
import uuid
from pathlib import Path
from typing import Any

import redis
from sqlalchemy import select

import xbot.tasks as tasks
from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
from xbot.celery_app import celery_app

logger = logging.getLogger("xbot.tasks")


async def _check_trend_radar_async(base_profile_dir: Path | str | None = None) -> dict[str, Any]:
    """
    Periodically checks RSS and trend radar sources for all active profiles,
    evaluates relevance against each persona niche, synthesizes 3-bullet takes + hot takes with optimized hooks,
    and stages approved content into the Content database table with Redis deduplication.
    """
    r = tasks.redis.from_url(settings.REDIS_URL)
    base_dir = Path(base_profile_dir) if base_profile_dir else Path("/home/ubuntu/projects/xbot/data/profiles")

    total_profiles = 0
    items_scanned = 0
    items_staged = 0
    errors: list[str] = []

    try:
        async with tasks.AsyncSessionLocal() as db:
            stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
            res = await db.execute(stmt)
            active_profiles = res.scalars().all()

            if not active_profiles:
                logger.info("No active profiles found for trend radar checking.")
                return {
                    "status": "success",
                    "profiles_processed": 0,
                    "items_scanned": 0,
                    "items_staged": 0,
                }

            for profile in active_profiles:
                profile_slug = profile.profile_slug
                profile_id = profile.id
                profile_dir = base_dir / profile_slug

                try:
                    total_profiles += 1

                    # 1. Load persona
                    try:
                        persona = tasks.load_persona(profile_dir)
                    except Exception as ex:
                        logger.warning("Failed to load persona for profile %s: %s", profile_slug, ex)
                        errors.append(f"{profile_slug}: {ex}")
                        continue

                    # 2. Extract configured trend sources or fallback to defaults
                    feed_urls: list[str] = []
                    keywords: list[str] = []

                    trend_sources = getattr(persona, "trend_sources", None)
                    if isinstance(trend_sources, dict):
                        feed_urls = trend_sources.get("rss_feeds", []) or []
                        keywords = trend_sources.get("keywords", []) or []
                    elif hasattr(trend_sources, "rss_feeds"):
                        feed_urls = getattr(trend_sources, "rss_feeds", []) or []
                        keywords = getattr(trend_sources, "keywords", []) or []
                    elif isinstance(getattr(persona, "raw_character_card", None), dict):
                        raw_ts = persona.raw_character_card.get("trend_sources", {})
                        if isinstance(raw_ts, dict):
                            feed_urls = raw_ts.get("rss_feeds", []) or []
                            keywords = raw_ts.get("keywords", []) or []

                    if not feed_urls:
                        feed_urls = ["https://hnrss.org/frontpage"]

                    if not keywords and persona.interests and persona.interests.primary:
                        keywords = list(persona.interests.primary)

                    # 3. Fetch trends from RSS/Atom feeds or multi-source real-time radar
                    try:
                        trends = await tasks.fetch_rss_trends(feed_urls, keywords=keywords)
                        if not trends and feed_urls == ["https://hnrss.org/frontpage"]:
                            trends = await tasks.fetch_multi_source_trends(
                                feed_urls=feed_urls if feed_urls else None,
                                keywords=keywords,
                                max_total=12,
                            )
                    except Exception as ex:
                        logger.warning("Failed to fetch trends for profile %s: %s", profile_slug, ex)
                        errors.append(f"{profile_slug} trend fetch: {ex}")
                        continue

                    items_scanned += len(trends)

                    # 4. Process each trend item
                    breaking_trend_summaries = []
                    for item in trends:
                        item_id = item.id
                        seen_key = f"xbot:seen_trends:{profile_id}:{item_id}"
                        seen_set_key = f"xbot:seen_trends:{profile_id}"

                        # Redis Deduplication
                        try:
                            if r.exists(seen_key) or r.sismember(seen_set_key, item_id):
                                logger.debug("Trend item %s already seen for profile %s; skipping.", item_id, profile_slug)
                                continue
                        except Exception as r_err:
                            logger.warning("Redis dedup check error: %s", r_err)

                        # Evaluate Take via LLM
                        eval_result = await tasks.generate_trend_take(persona, item)

                        # Cache in Redis with 7-day TTL
                        try:
                            r.set(seen_key, "1", ex=604800)
                            r.sadd(seen_set_key, item_id)
                        except Exception as r_err:
                            logger.warning("Redis cache error: %s", r_err)

                        # If relevant, record for session planner
                        if eval_result.is_relevant and eval_result.relevance_score >= 0.65:
                            breaking_trend_summaries.append({
                                "topic": item.title,
                                "summary": item.summary,
                                "hot_take": eval_result.hot_take,
                                "quote_hook": eval_result.quote_hook,
                            })

                        # If highly relevant and post produced, synthesize visual spec and stage Content record in DB (max 3 per run)
                        if eval_result.is_relevant and eval_result.relevance_score >= 0.70 and eval_result.optimized_post and items_staged < 3:
                            post_text = eval_result.optimized_post
                            
                            # Conduct deep X research to collect top 20-30 viral posts for topic background
                            gif_query = None
                            media_paths = []
                            research_report_dict = None
                            try:
                                from xbot.ai.x_researcher import research_topic_comprehensively
                                r_report = await research_topic_comprehensively(
                                    topic=item.title,
                                    persona=persona,
                                    max_tweets=25,
                                    profile_slug=profile_slug,
                                )
                                if r_report:
                                    research_report_dict = r_report.model_dump()
                                    # Note: Scraped search images are NOT attached to text posts
                            except Exception as r_err:
                                logger.debug("Trend X media research skipped: %s", r_err)

                            metadata = {
                                "trend_id": item.id,
                                "trend_title": item.title,
                                "source_url": item.source_url,
                                "source_name": item.source_name,
                                "published_at": item.published_at,
                                "relevance_score": eval_result.relevance_score,
                                "reasoning": eval_result.reasoning,
                                "key_takeaways": eval_result.key_takeaways,
                                "hot_take": eval_result.hot_take,
                                "draft_post": eval_result.draft_post,
                                "optimized_post": eval_result.optimized_post,
                                "research_report": research_report_dict,
                                "gif_query": gif_query,
                                "media_paths": media_paths if media_paths else None,
                            }

                            cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
                            prof_config = tasks.load_config(cfg_path) if cfg_path.exists() else None
                            req_appr = getattr(prof_config, "require_post_approval", False) if prof_config else False
                            staged_status = ContentStatus.DRAFT if req_appr else ContentStatus.APPROVED

                            content_record = Content(
                                profile_id=profile_id,
                                content_type=ContentType.ORIGINAL,
                                body=post_text,
                                status=staged_status,
                                ai_metadata=metadata,
                                created_at=datetime.datetime.utcnow(),
                            )
                            db.add(content_record)

                            # If a high-value thread was generated, stage the thread as well
                            if eval_result.thread_items and len(eval_result.thread_items) >= 3:
                                thread_root = eval_result.thread_items[0]
                                thread_meta = {
                                    **metadata,
                                    "thread_items": eval_result.thread_items,
                                    "is_thread": True,
                                }
                                thread_record = Content(
                                    profile_id=profile_id,
                                    content_type=ContentType.THREAD,
                                    body=thread_root,
                                    status=staged_status,
                                    ai_metadata=thread_meta,
                                    created_at=datetime.datetime.utcnow(),
                                )
                                db.add(thread_record)
                                logger.info(
                                    "Staged trend thread (%d parts, status=%s) for profile %s: '%s'",
                                    len(eval_result.thread_items),
                                    staged_status.value,
                                    profile_slug,
                                    item.title,
                                )

                            await db.commit()
                            items_staged += 1
                            logger.info(
                                "Staged high-relevance trend visual content %s for profile %s: '%s' (relevance=%.2f)",
                                content_record.id,
                                profile_slug,
                                item.title,
                                eval_result.relevance_score,
                            )

                    # Store breaking trends in Redis for live session planner
                    if breaking_trend_summaries:
                        try:
                            r.set(f"xbot:breaking_trends:{profile_id}", json.dumps(breaking_trend_summaries), ex=14400)
                        except Exception as r_err:
                            logger.debug("Failed to store breaking trends in Redis: %s", r_err)

                except Exception as p_ex:
                    logger.error("Error in trend radar loop for profile %s: %s", profile_slug, p_ex)
                    errors.append(f"{profile_slug}: {p_ex}")

        return {
            "status": "success" if not errors else "partial_success",
            "profiles_processed": total_profiles,
            "items_scanned": items_scanned,
            "items_staged": items_staged,
            "errors": errors if errors else None,
        }

    except Exception as overall_ex:
        logger.error("Trend radar task encountered critical error: %s", overall_ex)
        return {"status": "failed", "error": str(overall_ex)}


@celery_app.task(name="xbot.tasks.check_trend_radar")
def check_trend_radar() -> dict[str, Any]:
    """Celery periodic task scanning RSS feeds and trend radar sources for active profiles, generating takes, and staging content."""
    logger.info("Starting Celery check trend radar task.")
    return asyncio.run(tasks._check_trend_radar_async())
