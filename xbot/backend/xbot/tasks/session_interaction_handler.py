"""
Session Interaction Handlers (Reply, Quote, Follow, Like, and Navigation).
"""

from __future__ import annotations

import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import xbot.tasks as tasks
from xbot.ai.growth_scorer import is_f4f_or_engagement_growth_post, score_tweet_opportunity
from xbot.ai.sniper import generate_quote_take, generate_sniper_reply
from xbot.browser.actions.x_actions import (
    FollowEngagers,
    Retweet,
    ScrapeProfileMetrics,
    ScrapeTrends,
    UnfollowNonFollowers,
    UnfollowUser,
)
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.session import Action, ActionStatus

logger = logging.getLogger("xbot.tasks.session_interaction_handler")

SELECTORS = {"tweet": '[data-testid="tweet"]'}


async def handle_reply_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    profile_slug: str,
    p_action: Any,
    db_action: Action,
    page: Any,
    manager: Any,
    tweet_url: str | None,
) -> bool:
    """Handles targeted tweet reply synthesis and browser posting."""
    if not tweet_url or "/status/" not in tweet_url:
        logger.warning("Reply action skipped: target '%s' is not a valid X tweet status URL.", p_action.target)
        db_action.status = ActionStatus.SKIPPED
        db_action.error = f"Invalid reply target: '{p_action.target}' is not an X tweet status URL."
        return True

    if await tasks.has_already_acted(db, profile_id, tweet_url, "reply", hours=48):
        logger.info("Target tweet %s already replied to in last 48h. Skipping duplicate.", tweet_url)
        db_action.status = ActionStatus.SKIPPED
        db_action.error = "Already replied to this tweet in last 48 hours."
        return True

    reply_action = tasks.ReplyToTweet()
    logger.info("Navigating directly to target tweet URL to reply: %s", tweet_url)
    try:
        await page.goto(tweet_url, wait_until="commit", timeout=20000)
        await page.wait_for_selector(SELECTORS["tweet"], timeout=15000)
    except Exception as nav_e:
        logger.warning("Target tweet navigation / selector wait warning: %s", nav_e)
    await tasks.sleep_think_time(1000, 2500)

    live_ctx = await reply_action.scrape_target_tweet_context(page, target_idx=0)
    persona = tasks.load_persona(manager.base_profile_dir / profile_slug)

    if persona and live_ctx.get("text"):
        opp_score = score_tweet_opportunity(live_ctx)
        if opp_score.recommended_action == "skip":
            logger.info("Phoenix Growth Scorer recommended skipping target tweet %s (score=%.1f): %s", tweet_url, opp_score.score, opp_score.reasoning)
            db_action.status = ActionStatus.SKIPPED
            db_action.error = f"Opportunity score skipped: {opp_score.reasoning}"
            db_action.result = {"opportunity_score": opp_score.model_dump()}
            await db.commit()
            return True

        sniper_res = await generate_sniper_reply(
            persona=persona,
            target_tweet=live_ctx,
            preferred_angle=getattr(p_action, "preferred_angle", None) or getattr(p_action, "angle", None),
            opportunity_score=opp_score,
        )
        final_reply_text = sniper_res.reply_text
        final_gif_query = sniper_res.gif_query or getattr(p_action, "gif_query", None)
        db_action.content = final_reply_text
        res_dict = sniper_res.model_dump()
        res_dict["opportunity_score"] = opp_score.model_dump()
        db_action.result = res_dict
        await db.commit()

        if not final_reply_text or sniper_res.confidence == 0.0:
            logger.warning("Sniper reply safely skipped: Top-tier writing models timed out. Will retry in next session.")
            db_action.status = ActionStatus.SKIPPED
            db_action.error = "Top-tier writing models busy/unavailable after retries. Discarded to prevent posting low quality."
            await db.commit()
            return True
    else:
        final_reply_text = p_action.content
        final_gif_query = getattr(p_action, "gif_query", None)
        if not final_reply_text:
            logger.warning("Reply skipped: No content provided or planned.")
            db_action.status = ActionStatus.SKIPPED
            db_action.error = "No reply content available."
            await db.commit()
            return True

    return await reply_action.execute(
        page,
        reply_text=final_reply_text,
        tweet_url=tweet_url,
        tweet_index=0,
        gif_query=final_gif_query,
    )


async def handle_quote_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    p_action: Any,
    db_action: Action,
    page: Any,
    persona: Any,
    tweet_url: str | None,
    is_mock: bool = False,
) -> bool:
    """Handles quote-tweet actions with F4F guard and contextual quote synthesis."""
    if not tweet_url or "/status/" not in tweet_url:
        db_action.status = ActionStatus.SKIPPED
        db_action.error = f"Invalid quote target: '{p_action.target}' is not an X tweet status URL."
        return True

    if await tasks.has_already_acted(db, profile_id, tweet_url, "quote", hours=48):
        db_action.status = ActionStatus.SKIPPED
        db_action.error = "Already quoted this tweet in last 48 hours."
        return True

    if not is_mock:
        live_ctx = await tasks.ReplyToTweet().scrape_target_tweet_context(page, tweet_url=tweet_url, target_idx=0)
        target_text = live_ctx.get("text", "")
        if is_f4f_or_engagement_growth_post(target_text) or is_f4f_or_engagement_growth_post(p_action.content or ""):
            db_action.status = ActionStatus.SKIPPED
            db_action.error = "Quoting F4F / engagement-growth posts is forbidden. Synthesize original posts instead."
            return True
        quote_res = await generate_quote_take(persona=persona, target_tweet=live_ctx)
        quote_text = quote_res.quote_text
        quote_gif_query = quote_res.gif_query or getattr(p_action, "gif_query", None)
        db_action.content = quote_text
        db_action.result = quote_res.model_dump()
        await db.commit()
    else:
        quote_text = getattr(p_action, "content", "") or ""
        quote_gif_query = getattr(p_action, "gif_query", None)

    # Strictly reject empty or generic template text
    if not quote_text or len(quote_text.strip()) < 8 or any(c in quote_text.lower() for c in ["adding to the discussion", "sharp perspective on this", "spot on"]):
        logger.warning("Quote action skipped: AI generation failed or content was generic template.")
        db_action.status = ActionStatus.SKIPPED
        db_action.error = "Quote generation failed or was generic template. Action skipped to maintain quality."
        await db.commit()
        return True

    return await tasks.QuoteTweet().execute(page, quote_text=quote_text, tweet_url=tweet_url, gif_query=quote_gif_query)


async def handle_follow_action(
    db: AsyncSession,
    profile_id: uuid.UUID,
    p_action: Any,
    username_target: str | None,
    page: Any,
) -> bool:
    """Handles follow actions with reciprocity candidate discovery and tracking."""
    target_to_follow = username_target or p_action.target
    if target_to_follow:
        clean_target = target_to_follow.lstrip("@")
        rel_chk = await db.execute(select(FollowRelationship).where(FollowRelationship.profile_id == profile_id, FollowRelationship.target_handle == clean_target))
        if rel_chk.scalar_one_or_none():
            target_to_follow = None

    if not target_to_follow:
        c_res = await db.execute(select(FollowCandidate).where(FollowCandidate.profile_id == profile_id, FollowCandidate.status.in_(["discovered", "queued"])).order_by(FollowCandidate.is_blue_tick.desc(), FollowCandidate.reciprocity_score.desc()).limit(1))
        top_c = c_res.scalar_one_or_none()
        if top_c:
            target_to_follow = top_c.handle
            top_c.status = "followed"
            await db.commit()

    if target_to_follow:
        clean_f_handle = target_to_follow.lstrip("@")
        success = await tasks.FollowUser().execute(page, clean_f_handle)
        if success:
            from xbot.growth.f4f_engine import record_follow_action
            await record_follow_action(profile_id=profile_id, target_handle=clean_f_handle, db=db, is_blue_tick=True)
        return success
    return False


async def handle_simple_action(
    p_action: Any,
    tweet_url: str | None,
    username_target: str | None,
    page: Any,
) -> bool:
    """Dispatches simple browser actions (like, retweet, search, browse, unfollow, scrape)."""
    if p_action.type == "like":
        return await tasks.LikeTweet().execute(page, tweet_url=tweet_url)
    elif p_action.type == "retweet":
        return await Retweet().execute(page, tweet_url=tweet_url)
    elif p_action.type == "search" and p_action.target:
        results = await tasks.SearchQuery().execute(page, p_action.target)
        return len(results) > 0
    elif p_action.type == "browse":
        results = await tasks.BrowseFeed().execute(page, max_scrolls=1)
        return len(results) > 0
    elif p_action.type == "unfollow" and (username_target or p_action.target):
        return await UnfollowUser().execute(page, username_target or p_action.target)
    elif p_action.type == "scrape_trends":
        results = await ScrapeTrends().execute(page)
        return len(results) > 0
    elif p_action.type == "scrape_metrics" and p_action.target:
        results = await ScrapeProfileMetrics().execute(page, p_action.target)
        return len(results) > 0
    elif p_action.type == "unfollow_non_followers":
        return await UnfollowNonFollowers().execute(page, limit=10)
    elif p_action.type == "follow_engagers" and (tweet_url or p_action.target):
        return await FollowEngagers().execute(page, tweet_url=tweet_url or p_action.target, limit=5)
    return False
