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

from xbot.models.profile import Profile
from xbot.models.realgraph import ConversationThread
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result
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
) -> int:
    """Checks active conversation threads and executes follow-ups within 15m window."""
    pkg = _get_pkg()
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

        _enqueue = getattr(pkg, "enqueue_browser_job", enqueue_browser_job)
        _get_res = getattr(pkg, "get_browser_job_result", get_browser_job_result)

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
        reply_job_id = _enqueue(reply_job)
        reply_res = await asyncio.to_thread(_get_res, reply_job_id, 25.0)

        if reply_res and reply_res.get("status") in ("success", "replied"):
            thread.turn_count += 1
            thread.last_action_at = datetime.datetime.utcnow()
            await guard.record_action(db, profile_slug, "reply", target_id=target_key)
            replies_count += 1
            post_url = target_payload.get("url")
            if post_url:
                like_job = BrowserJob(
                    action_type="like",
                    profile_slug=profile_slug,
                    params={"tweet_url": post_url},
                    priority=3,
                )
                _enqueue(like_job)

    return replies_count


async def execute_feed_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
) -> int:
    """Scrapes feed for high-opportunity viral posts and posts in-character replies."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug
    _get_persona = getattr(pkg, "_get_persona_for_profile", _get_persona_for_profile)
    persona = _get_persona(profile_slug)
    _enqueue = getattr(pkg, "enqueue_browser_job", enqueue_browser_job)
    _get_res = getattr(pkg, "get_browser_job_result", get_browser_job_result)

    scrape_job = BrowserJob(
        action_type="scrape_feed",
        profile_slug=profile_slug,
        params={"scroll_count": 3, "collect_tweets": True},
        priority=2,
    )
    job_id = _enqueue(scrape_job)
    scrape_res = await asyncio.to_thread(_get_res, job_id, 45.0)

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

        opp_score = pkg.score_tweet_opportunity(tw)
        if opp_score.recommended_action == "skip" and opp_score.score < 20.0:
            continue

        top_comments = tw.get("top_comments") or tw.get("comments") or tw.get("replies_sample") or []
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
        reply_job_id = _enqueue(reply_job)
        reply_res = await asyncio.to_thread(_get_res, reply_job_id, 25.0)

        if reply_res and reply_res.get("status") in ("success", "replied"):
            await guard.record_action(db, profile_slug, "reply", target_id=tweet_id)
            replies_count += 1
            if tweet_url:
                like_job = BrowserJob(
                    action_type="like",
                    profile_slug=profile_slug,
                    params={"tweet_url": tweet_url},
                    priority=3,
                )
                _enqueue(like_job)

    return replies_count
