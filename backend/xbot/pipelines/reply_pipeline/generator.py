"""
Reply Pipeline Generators for Sentinel Fast-Response and Feed Opportunity replies.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.models.profile import Profile
from xbot.models.realgraph import ConversationThread
from xbot.pipelines.central_guard import CentralGuard
from xbot.pipelines.reply_pipeline.evaluator import _get_persona_for_profile

logger = logging.getLogger(__name__)


def _get_pkg():
    return sys.modules.get("xbot.pipelines.reply_pipeline") or sys.modules[__name__]


async def execute_fast_response_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
    container: Container | None = None,
) -> int:
    """Checks active conversation threads and executes follow-ups within 15m window via BrowserPort."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug
    c = container or get_container()
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

    _get_persona = getattr(pkg, "_get_persona_for_profile", _get_persona_for_profile)
    persona = _get_persona(profile_slug)
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
            sniper_res = await pkg.generate_sniper_reply(
                persona=persona,
                target_tweet=target_payload,
            )
            if sniper_res and (sniper_res.reply_text or sniper_res.gif_query):
                reply_text = sniper_res.reply_text
                gif_query = sniper_res.gif_query
                if sniper_res.response_mode in ("emoji_reaction", "pure_gif"):
                    formatted_reply = reply_text
                else:
                    formatted_reply = pkg.format_content(reply_text, profile_slug=profile_slug, content_type="reply")
                    formatted_reply = pkg.strip_surrounding_quotes(formatted_reply)
            else:
                reply_text = "Appreciate the perspective! How do you see this evolving over the next few months?"
                formatted_reply = pkg.format_content(reply_text, profile_slug=profile_slug, content_type="reply")
                formatted_reply = pkg.strip_surrounding_quotes(formatted_reply)
        else:
            reply_text = "Appreciate the perspective! How do you see this evolving over the next few months?"
            formatted_reply = pkg.format_content(reply_text, profile_slug=profile_slug, content_type="reply")
            formatted_reply = pkg.strip_surrounding_quotes(formatted_reply)

        reply_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.REPLY,
            params={
                "tweet_id": thread_id,
                "text": formatted_reply,
                "gif_query": gif_query,
            },
            timeout_seconds=25,
        )
        reply_res = await c.browser.execute(reply_req)

        if reply_res.status in ("success", "replied") or (reply_res.action_result and reply_res.action_result.status == "success"):
            thread.turn_count += 1
            thread.last_action_at = datetime.datetime.utcnow()
            await guard.record_action(db, profile_slug, "reply", target_id=target_key)
            replies_count += 1
            post_url = target_payload.get("url")
            if post_url:
                like_req = BrowserRequest(
                    profile_slug=profile_slug,
                    action=BrowserActionType.LIKE,
                    params={"tweet_url": post_url},
                    timeout_seconds=15,
                )
                await c.browser.execute(like_req)

    return replies_count


async def execute_feed_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
    container: Container | None = None,
) -> int:
    """Scrapes feed for high-opportunity viral posts and posts in-character replies via BrowserPort."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug
    c = container or get_container()
    _get_persona = getattr(pkg, "_get_persona_for_profile", _get_persona_for_profile)
    persona = _get_persona(profile_slug)

    scrape_req = BrowserRequest(
        profile_slug=profile_slug,
        action=BrowserActionType.SCRAPE_FEED,
        params={"scroll_count": 3, "collect_tweets": True},
        timeout_seconds=45,
    )
    scrape_res = await c.browser.execute(scrape_req)

    if scrape_res.status != "success":
        return 0

    feed_tweets: list[dict[str, Any]] = []
    if scrape_res.scrape and scrape_res.scrape.tweets:
        feed_tweets = [tw.model_dump() for tw in scrape_res.scrape.tweets]
    elif scrape_res.scrape and scrape_res.scrape.raw.get("tweets"):
        feed_tweets = scrape_res.scrape.raw["tweets"]
    elif scrape_res.action_result and scrape_res.action_result.raw.get("tweets"):
        feed_tweets = scrape_res.action_result.raw["tweets"]

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

        opp_score = pkg.score_tweet_opportunity(tw)
        if opp_score.recommended_action == "skip" and opp_score.score < 20.0:
            continue

        top_comments = tw.get("top_comments") or tw.get("metrics", {}).get("top_comments") or tw.get("comments") or tw.get("replies_sample") or []
        media_alts = tw.get("media_alts") or tw.get("metrics", {}).get("media_alts") or tw.get("image_descriptions") or []
        media_urls = tw.get("media_urls") or tw.get("metrics", {}).get("media_urls") or tw.get("images") or []
        views = tw.get("views") or tw.get("metrics", {}).get("views") or tw.get("impressions") or 0
        likes = tw.get("likes") or tw.get("metrics", {}).get("likes") or 0
        replies = tw.get("replies") or tw.get("metrics", {}).get("replies") or 0
        retweets = tw.get("retweets") or tw.get("metrics", {}).get("retweets") or 0

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
        sniper_res = await pkg.generate_sniper_reply(
            persona=persona,
            target_tweet=target_payload,
            opportunity_score=opp_score,
        )
        if not sniper_res or (not sniper_res.reply_text and not sniper_res.gif_query):
            continue

        if sniper_res.response_mode in ("emoji_reaction", "pure_gif"):
            formatted_reply = sniper_res.reply_text
        else:
            formatted_reply = pkg.format_content(
                raw_text=sniper_res.reply_text,
                profile_slug=profile_slug,
                content_type="reply",
                topic=tweet_text[:60],
            )
            formatted_reply = pkg.strip_surrounding_quotes(formatted_reply)

        reply_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.REPLY,
            params={
                "tweet_id": tweet_id,
                "tweet_url": tweet_url,
                "text": formatted_reply,
                "gif_query": sniper_res.gif_query,
            },
            timeout_seconds=25,
        )
        reply_res = await c.browser.execute(reply_req)

        if reply_res.status in ("success", "replied") or (reply_res.action_result and reply_res.action_result.status == "success"):
            await guard.record_action(db, profile_slug, "reply", target_id=tweet_id)
            replies_count += 1
            if tweet_url:
                like_req = BrowserRequest(
                    profile_slug=profile_slug,
                    action=BrowserActionType.LIKE,
                    params={"tweet_url": tweet_url},
                    timeout_seconds=15,
                )
                await c.browser.execute(like_req)

    return replies_count
