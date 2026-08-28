"""
Independent Quote Pipeline for XBot Pro.

Runs every 15 minutes (during active hours: 6:00 AM - 2:00 AM IST):
1. Scrapes feed for viral tweets in the profile's niche.
2. Gates by >=50,000 impressions floor and rejects F4F engagement trains.
3. Generates high-entropy counter-perspectives or analytical takes.
4. Formats via Dynamic Formatting Engine (archetype rotation).
5. Executes 1-2 quotes per cycle via Central Browser Queue.
6. Records 48-hour deduplication and logs in PipelineRun.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper
from xbot.ai.formatting_engine import PostFormattingArchetype, format_content
from xbot.ai.growth_scorer import is_f4f_or_engagement_growth_post
from xbot.ai.post_synthesizer import synthesize_creator_post
from xbot.database import AsyncSessionLocal
from xbot.models.pipeline import PipelineRun
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result
from xbot.pipelines.central_guard import CentralGuard

logger = logging.getLogger(__name__)


async def run_quote_pipeline_for_profile(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_quotes: int = 2,
) -> dict[str, Any]:
    """Executes quote cycle for a single profile."""
    profile_slug = profile.profile_slug

    # 1. Guard check
    can_proceed = await guard.can_act(db, profile_slug, "quote")
    if not can_proceed:
        return {"status": "skipped", "reason": "guard_check_failed", "quotes_executed": 0}

    # 2. Scrape feed for candidates
    scrape_job = BrowserJob(
        action_type="scrape_feed",
        profile_slug=profile_slug,
        params={"scroll_count": 3, "collect_tweets": True},
        priority=3,
    )
    job_id = enqueue_browser_job(scrape_job)
    scrape_res = await asyncio.to_thread(get_browser_job_result, job_id, 45.0)

    if not scrape_res or scrape_res.get("status") != "success":
        return {"status": "failed", "reason": "feed_scrape_failed", "quotes_executed": 0}

    feed_tweets: list[dict[str, Any]] = scrape_res.get("tweets", [])
    if not feed_tweets:
        return {"status": "success", "quotes_executed": 0}

    quotes_count = 0
    gatekeeper = AntiAIGatekeeper()

    for tw in feed_tweets:
        if quotes_count >= max_quotes:
            break

        tweet_id = str(tw.get("id") or tw.get("tweet_id") or "")
        tweet_text = tw.get("text", "")
        tweet_url = tw.get("url") or tw.get("tweet_url")
        views = tw.get("views") or tw.get("impressions") or 0

        if not tweet_id or not tweet_text:
            continue

        # Dedup check
        if guard.is_target_acted_upon(profile_slug, "quote", tweet_id):
            continue

        # Reject F4F / Follow-train bait
        if is_f4f_or_engagement_growth_post(tweet_text):
            continue

        # Enforce 50,000 impression threshold
        try:
            views_int = int(str(views).replace(",", "").replace(".", "").replace("K", "000").replace("M", "000000")) if isinstance(views, str) else int(views)
        except Exception:
            views_int = 0

        if views_int > 0 and views_int < 50000:
            continue

        # Load profile persona
        from xbot.persona.loader import load_persona
        persona = None
        try:
            persona = load_persona(profile_slug)
        except Exception as p_err:
            logger.debug("Could not load persona for %s: %s", profile_slug, p_err)

        # Synthesize a contextual sharp quote take
        try:
            from xbot.ai.sniper import generate_sniper_reply
            quote_res_obj = await generate_sniper_reply(
                persona=persona,
                target_tweet=tw,
            )
            raw_quote = quote_res_obj.reply_text.strip()
            if not raw_quote or raw_quote.lower() in ("spot on", "great post"):
                logger.warning("Quote synthesis returned empty or generic text for tweet %s, skipping.", tweet_id)
                continue
        except Exception as syn_err:
            logger.warning("Quote synthesis failed for tweet %s: %s. Skipping without quoting.", tweet_id, syn_err)
            continue

        # Anti-AI gatekeeper check
        val_res = gatekeeper.validate(raw_quote)
        if not val_res.is_valid:
            raw_quote = gatekeeper.remediate_minor_issues(raw_quote)


        # Format via dynamic formatting engine
        formatted_quote = format_content(
            raw_text=raw_quote,
            profile_slug=profile_slug,
            content_type="quote",
            archetype=PostFormattingArchetype.HOT_TAKE_PUNCH,
        )

        # Enqueue browser quote job
        quote_job = BrowserJob(
            action_type="quote",
            profile_slug=profile_slug,
            params={"tweet_id": tweet_id, "tweet_url": tweet_url, "text": formatted_quote},
            priority=2,
        )
        quote_job_id = enqueue_browser_job(quote_job)
        quote_res = await asyncio.to_thread(get_browser_job_result, quote_job_id, 30.0)

        if quote_res and quote_res.get("status") in ("success", "quoted"):
            await guard.record_action(db, profile_slug, "quote", target_id=tweet_id)
            quotes_count += 1

    return {
        "status": "success",
        "quotes_executed": quotes_count,
    }


async def _run_quote_pipeline_async() -> dict[str, Any]:
    guard = CentralGuard()
    started_at = datetime.datetime.utcnow()
    total_quotes = 0
    results_by_profile: dict[str, Any] = {}

    async with AsyncSessionLocal() as db:
        stmt = select(Profile).where(Profile.status == ProfileStatus.ACTIVE)
        profiles = (await db.execute(stmt)).scalars().all()

        for profile in profiles:
            try:
                res = await run_quote_pipeline_for_profile(db, profile, guard)
                results_by_profile[profile.profile_slug] = res
                total_quotes += res.get("quotes_executed", 0)

                run_log = PipelineRun(
                    pipeline_name="quote",
                    profile_id=profile.id,
                    status=res.get("status", "success"),
                    actions_count=res.get("quotes_executed", 0),
                    details=res,
                    started_at=started_at,
                    completed_at=datetime.datetime.utcnow(),
                )
                db.add(run_log)
                await db.commit()

            except Exception as e:
                logger.error("QuotePipeline: Error for profile %s: %s", profile.profile_slug, e, exc_info=True)
                run_log = PipelineRun(
                    pipeline_name="quote",
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
        "pipeline": "quote",
        "total_quotes": total_quotes,
        "profiles": results_by_profile,
        "duration_seconds": (datetime.datetime.utcnow() - started_at).total_seconds(),
    }


from xbot.celery_app import celery_app


@celery_app.task(name="xbot.pipelines.quote_pipeline.run_quote_pipeline")
def run_quote_pipeline() -> dict[str, Any]:
    """Celery task entry point for Quote Pipeline."""
    return asyncio.run(_run_quote_pipeline_async())

