"""
Unified Reply Pipeline for XBot Pro.

Runs every 5 minutes (during active hours: 6:00 AM - 2:00 AM IST):
Merges 3 high-impact reply engines:
1. Priority 1 (Sniper): Scans target KOL handles for fresh tweets (<30m), evaluates Phoenix opportunity score, crafts value-first debate catalyst replies (Priority 0 job).
2. Priority 2 (Fast Response Sentinel): Follows up on active conversations within the 15m window to capture the +150x author engagement multiplier (Priority 1 job).
3. Priority 3 (Feed Opportunities): Scans feed for high-leverage tweets (>=5K impressions) and replies with structured archetypes (Priority 2 job).

Applies:
- Anti-AI Gatekeeper validation & quote stripping
- Dynamic Formatting Engine (archetype rotation, whitespace pacing, trailing emoji stripping)
- 48-hour deduplication and rate limits via CentralGuard
- Logs every cycle in PipelineRun.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.formatting_engine import format_content
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.sniper import generate_sniper_reply
from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.realgraph import ConversationThread
from xbot.persona import load_config, load_persona
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


def _get_persona_for_profile(profile_slug: str):
    try:
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "persona.yaml").exists():
            return load_persona(cfg_path)
    except Exception:
        pass
    return None


async def execute_kol_sniper_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
) -> int:
    """Checks KOL handles and executes sniper replies with enriched thread context."""
    profile_slug = profile.profile_slug
    config = None
    try:
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists():
            config = load_config(cfg_path)
    except Exception:
        pass

    target_kols = getattr(config, "target_kols", []) if config else []
    if not target_kols and profile.config:
        target_kols = profile.config.get("target_kols", [])

    if not target_kols:
        return 0

    persona = _get_persona_for_profile(profile_slug)
    replies_count = 0

    for kol in target_kols:
        if replies_count >= max_replies:
            break

        username = kol.lstrip("@").strip()
        if not username:
            continue

        # Check latest tweet for this KOL
        check_job = BrowserJob(
            action_type="check_user_tweets",
            profile_slug=profile_slug,
            params={"username": username, "max_age_minutes": 35},
            priority=0,
        )
        job_id = enqueue_browser_job(check_job)
        check_res = await asyncio.to_thread(get_browser_job_result, job_id, 35.0)

        if not check_res or not check_res.get("found_fresh_tweet"):
            continue

        tweet_data = check_res.get("tweet_data") or check_res.get("context") or check_res.get("result") or {}
        tweet_id = str(tweet_data.get("id") or tweet_data.get("tweet_id") or "")
        tweet_text = tweet_data.get("text", "")
        tweet_url = tweet_data.get("url") or tweet_data.get("tweet_url")

        if not tweet_id or not tweet_text:
            continue

        # Dedup check
        if guard.is_target_acted_upon(profile_slug, "reply", tweet_id):
            continue

        # Growth scorer check (enforce 5K impression floor unless high score)
        opp_score = score_tweet_opportunity(tweet_data)
        if opp_score.recommended_action == "skip" and opp_score.score < 25.0:
            logger.info("ReplyPipeline: Sniper skipped tweet %s (score %.1f)", tweet_id, opp_score.score)
            continue

        # Extract full target thread context (root text, media descriptions, top 10 comments with likes, and metrics)
        top_comments = (
            tweet_data.get("top_comments")
            or tweet_data.get("comments")
            or tweet_data.get("replies_sample")
            or check_res.get("top_comments")
            or []
        )
        media_alts = (
            tweet_data.get("media_alts")
            or tweet_data.get("image_descriptions")
            or check_res.get("media_alts")
            or []
        )
        media_urls = (
            tweet_data.get("media_urls")
            or tweet_data.get("images")
            or check_res.get("media_urls")
            or []
        )
        views = (
            tweet_data.get("views")
            or tweet_data.get("impressions")
            or check_res.get("views")
            or 0
        )
        likes = tweet_data.get("likes") or check_res.get("likes") or 0
        replies = tweet_data.get("replies") or check_res.get("replies") or 0
        retweets = tweet_data.get("retweets") or check_res.get("retweets") or 0

        # Generate sniper reply with enriched context
        target_payload = {
            "author": tweet_data.get("author") or tweet_data.get("handle") or username,
            "handle": tweet_data.get("handle") or tweet_data.get("author") or username,
            "text": tweet_text,
            "url": tweet_url,
            "id": tweet_id,
            "views": views,
            "impressions": views,
            "likes": likes,
            "replies": replies,
            "retweets": retweets,
            "top_comments": top_comments,
            "media_alts": media_alts,
            "media_urls": media_urls,
        }
        sniper_res = await generate_sniper_reply(
            persona=persona,
            target_tweet=target_payload,
            opportunity_score=opp_score,
        )
        if not sniper_res or (not sniper_res.reply_text and not sniper_res.gif_query):
            continue

        # Format reply through dynamic formatting engine (preserve pure gif / emoji reactions)
        if sniper_res.response_mode in ("emoji_reaction", "pure_gif"):
            formatted_reply = sniper_res.reply_text
        else:
            formatted_reply = format_content(
                raw_text=sniper_res.reply_text,
                profile_slug=profile_slug,
                content_type="reply",
                topic=tweet_text[:60],
            )
            formatted_reply = strip_surrounding_quotes(formatted_reply)

        # Enqueue reply job with gif_query parameter
        reply_job = BrowserJob(
            action_type="reply",
            profile_slug=profile_slug,
            params={
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "text": formatted_reply,
                "gif_query": sniper_res.gif_query,
            },
            priority=0,
        )
        reply_job_id = enqueue_browser_job(reply_job)
        reply_res = await asyncio.to_thread(get_browser_job_result, reply_job_id, 25.0)

        if reply_res and reply_res.get("status") in ("success", "replied"):
            await guard.record_action(db, profile_slug, "reply", target_id=tweet_id)
            replies_count += 1

    return replies_count


async def execute_fast_response_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
) -> int:
    """Checks active conversation threads and executes follow-ups within 15m window."""
    profile_slug = profile.profile_slug
    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(minutes=20)

    stmt = (
        select(ConversationThread)
        .where(
            ConversationThread.profile_id == profile.id,
            ConversationThread.status == "active",
            ConversationThread.last_action_at >= cutoff_time,
        )
        .limit(max_replies)
    )
    result = await db.execute(stmt)
    threads = result.scalars().all()
    if not threads:
        return 0

    persona = _get_persona_for_profile(profile_slug)
    replies_count = 0
    for thread in threads:
        if replies_count >= max_replies:
            break

        thread_id = str(thread.root_tweet_id)
        target_key = f"thread_{thread.id}_{thread.turn_count}"
        if guard.is_target_acted_upon(profile_slug, "reply", target_key):
            continue

        last_msg = ""
        if thread.conversation_history:
            last_entry = thread.conversation_history[-1]
            if isinstance(last_entry, dict):
                last_msg = last_entry.get("text") or last_entry.get("content") or ""
            else:
                last_msg = str(last_entry)

        target_payload = {
            "author": thread.target_handle.lstrip("@"),
            "handle": thread.target_handle.lstrip("@"),
            "text": last_msg or f"Replying to @{thread.target_handle}",
            "id": thread.parent_tweet_id or thread.root_tweet_id,
            "url": f"https://x.com/{thread.target_handle.lstrip('@')}/status/{thread.parent_tweet_id or thread.root_tweet_id}",
            "top_comments": thread.conversation_history or [],
        }

        gif_query = None
        if persona:
            sniper_res = await generate_sniper_reply(
                persona=persona,
                target_tweet=target_payload,
            )
            if sniper_res and (sniper_res.reply_text or sniper_res.gif_query):
                reply_text = sniper_res.reply_text
                gif_query = sniper_res.gif_query
                if sniper_res.response_mode in ("emoji_reaction", "pure_gif"):
                    formatted_reply = reply_text
                else:
                    formatted_reply = format_content(reply_text, profile_slug=profile_slug, content_type="reply")
                    formatted_reply = strip_surrounding_quotes(formatted_reply)
            else:
                reply_text = "Appreciate the perspective! How do you see this evolving over the next few months?"
                formatted_reply = format_content(reply_text, profile_slug=profile_slug, content_type="reply")
                formatted_reply = strip_surrounding_quotes(formatted_reply)
        else:
            reply_text = "Appreciate the perspective! How do you see this evolving over the next few months?"
            formatted_reply = format_content(reply_text, profile_slug=profile_slug, content_type="reply")
            formatted_reply = strip_surrounding_quotes(formatted_reply)

        reply_job = BrowserJob(
            action_type="reply",
            profile_slug=profile_slug,
            params={
                "tweet_id": thread_id,
                "text": formatted_reply,
                "gif_query": gif_query,
            },
            priority=1,
        )
        reply_job_id = enqueue_browser_job(reply_job)
        reply_res = await asyncio.to_thread(get_browser_job_result, reply_job_id, 25.0)

        if reply_res and reply_res.get("status") in ("success", "replied"):
            thread.turn_count += 1
            thread.last_action_at = datetime.datetime.utcnow()
            await guard.record_action(db, profile_slug, "reply", target_id=target_key)
            replies_count += 1

    return replies_count


async def execute_feed_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
) -> int:
    """Scrapes feed for high-opportunity viral posts and posts in-character replies."""
    profile_slug = profile.profile_slug
    persona = _get_persona_for_profile(profile_slug)

    scrape_job = BrowserJob(
        action_type="scrape_feed",
        profile_slug=profile_slug,
        params={"scroll_count": 3, "collect_tweets": True},
        priority=2,
    )
    job_id = enqueue_browser_job(scrape_job)
    scrape_res = await asyncio.to_thread(get_browser_job_result, job_id, 45.0)

    if not scrape_res or scrape_res.get("status") != "success":
        return 0

    feed_tweets: list[dict[str, Any]] = scrape_res.get("tweets", [])
    if not feed_tweets:
        return 0

    replies_count = 0
    for tw in feed_tweets:
        if replies_count >= max_replies:
            break

        tweet_id = str(tw.get("id") or tw.get("tweet_id") or "")
        tweet_text = tw.get("text", "")
        tweet_url = tw.get("url") or tw.get("tweet_url")
        author = str(tw.get("author", "")).lstrip("@")

        if not tweet_id or not tweet_text:
            continue

        if guard.is_target_acted_upon(profile_slug, "reply", tweet_id):
            continue

        # Evaluate viral opportunity score
        opp_score = score_tweet_opportunity(tw)
        if opp_score.recommended_action == "skip" and opp_score.score < 20.0:
            continue

        top_comments = (
            tw.get("top_comments")
            or tw.get("comments")
            or tw.get("replies_sample")
            or []
        )
        media_alts = tw.get("media_alts") or tw.get("image_descriptions") or []
        media_urls = tw.get("media_urls") or tw.get("images") or []
        views = tw.get("views") or tw.get("impressions") or 0
        likes = tw.get("likes", 0)
        replies = tw.get("replies", 0)
        retweets = tw.get("retweets", 0)

        target_payload = {
            "author": author or "creator",
            "handle": author or "creator",
            "text": tweet_text,
            "url": tweet_url,
            "id": tweet_id,
            "views": views,
            "impressions": views,
            "likes": likes,
            "replies": replies,
            "retweets": retweets,
            "top_comments": top_comments,
            "media_alts": media_alts,
            "media_urls": media_urls,
        }
        sniper_res = await generate_sniper_reply(
            persona=persona,
            target_tweet=target_payload,
            opportunity_score=opp_score,
        )
        if not sniper_res or (not sniper_res.reply_text and not sniper_res.gif_query):
            continue

        if sniper_res.response_mode in ("emoji_reaction", "pure_gif"):
            formatted_reply = sniper_res.reply_text
        else:
            formatted_reply = format_content(
                raw_text=sniper_res.reply_text,
                profile_slug=profile_slug,
                content_type="reply",
                topic=tweet_text[:60],
            )
            formatted_reply = strip_surrounding_quotes(formatted_reply)

        reply_job = BrowserJob(
            action_type="reply",
            profile_slug=profile_slug,
            params={
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "text": formatted_reply,
                "gif_query": sniper_res.gif_query,
            },
            priority=2,
        )
        reply_job_id = enqueue_browser_job(reply_job)
        reply_res = await asyncio.to_thread(get_browser_job_result, reply_job_id, 25.0)

        if reply_res and reply_res.get("status") in ("success", "replied"):
            await guard.record_action(db, profile_slug, "reply", target_id=tweet_id)
            replies_count += 1

    return replies_count


async def run_reply_pipeline_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_total_replies: int = 4,
) -> dict[str, Any]:
    """Executes full unified reply cycle for a profile."""
    profile_slug = profile.profile_slug

    can_proceed = await guard.can_act(db, profile_slug, "reply")
    if not can_proceed:
        return {"status": "skipped", "reason": "guard_check_failed", "replies_executed": 0}

    # 1. Sniper KOL replies
    sniper_count = await execute_kol_sniper_replies(db, profile, guard, max_replies=2)

    # 2. Fast response conversation follow-ups
    sentinel_count = 0
    if sniper_count < max_total_replies:
        sentinel_count = await execute_fast_response_replies(
            db, profile, guard, max_replies=(max_total_replies - sniper_count)
        )

    # 3. Feed Opportunity Replies (if remaining budget)
    feed_count = 0
    remaining_budget = max_total_replies - (sniper_count + sentinel_count)
    if remaining_budget > 0:
        feed_count = await execute_feed_replies(db, profile, guard, max_replies=remaining_budget)

    total_replies = sniper_count + sentinel_count + feed_count
    return {
        "status": "success",
        "replies_executed": total_replies,
        "sniper_replies": sniper_count,
        "sentinel_replies": sentinel_count,
        "feed_replies": feed_count,
    }


async def _run_reply_pipeline_async() -> dict[str, Any]:
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_replies = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await run_reply_pipeline_for_profile(db, profile, guard)
                results_by_profile[profile.profile_slug] = res
                total_replies += res.get("replies_executed", 0)

                run_log = PipelineRun(
                    pipeline_name="reply",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("replies_executed", 0),
                    details=res,
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

            except Exception as e:
                logger.error("ReplyPipeline: Error processing profile %s: %s", profile.profile_slug, e, exc_info=True)
                run_log = PipelineRun(
                    pipeline_name="reply",
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
        "pipeline": "reply",
        "total_replies": total_replies,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.reply_pipeline.run_reply_pipeline")
def run_reply_pipeline() -> dict[str, Any]:
    """Celery task entry point for Unified Reply Pipeline."""
    return asyncio.run(_run_reply_pipeline_async())
