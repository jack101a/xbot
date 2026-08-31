"""
Reply Pipeline KOL Sniper Reply Generator.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.models.profile import Profile
from xbot.persona import load_config
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result
from xbot.pipelines.central_guard import CentralGuard
from xbot.pipelines.reply_pipeline.evaluator import _get_persona_for_profile

logger = logging.getLogger(__name__)


def _get_pkg():
    return sys.modules.get("xbot.pipelines.reply_pipeline") or sys.modules[__name__]


async def execute_kol_sniper_replies(
    db: AsyncSession,
    profile: Profile,
    guard: CentralGuard,
    max_replies: int = 2,
) -> int:
    """Checks KOL handles and executes sniper replies with enriched thread context."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug
    config = None
    try:
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "config.yaml").exists() or (cfg_path / "persona.yaml").exists():
            config = load_config(cfg_path)
    except Exception:
        pass

    persona = _get_persona_for_profile(profile_slug)
    target_kols = getattr(config, "target_kols", []) if config else []
    if not target_kols and persona and hasattr(persona, "target_kols"):
        target_kols = persona.target_kols
    if not target_kols and profile.config:
        target_kols = profile.config.get("target_kols", [])

    if not target_kols:
        return 0

    replies_count = 0

    # Build active channel lookup
    active_channels: set[str] = set()
    if persona and hasattr(persona, "kol_channels") and persona.kol_channels:
        active_channels = {ch.name for ch in persona.kol_channels if getattr(ch, "is_active", True)}

    # Rotate and sample up to 4 active KOLs per cycle to keep pipeline latency under 30s
    candidate_kols = list(target_kols)
    if len(candidate_kols) > 4:
        import random
        random.shuffle(candidate_kols)
        candidate_kols = candidate_kols[:4]

    for kol in candidate_kols:
        if replies_count >= max_replies:
            break

        username = ""
        category = "general"
        preferred_angle = "insight"
        is_active = True

        if isinstance(kol, str):
            username = kol.lstrip("@").strip()
        elif isinstance(kol, dict):
            username = str(kol.get("handle") or "").lstrip("@").strip()
            category = str(kol.get("category") or "general")
            preferred_angle = str(kol.get("preferred_angle") or "insight")
            is_active = bool(kol.get("is_active", True))
        elif hasattr(kol, "handle"):
            username = getattr(kol, "handle", "").lstrip("@").strip()
            category = getattr(kol, "category", "general")
            preferred_angle = getattr(kol, "preferred_angle", "insight")
            is_active = getattr(kol, "is_active", True)

        if not username or not is_active:
            continue

        # Skip if category belongs to an explicitly deactivated channel
        if active_channels and category not in active_channels and category != "general":
            logger.info("ReplyPipeline: Skipping KOL @%s (channel '%s' is inactive)", username, category)
            continue

        _enqueue = getattr(pkg, "enqueue_browser_job", enqueue_browser_job)
        _get_res = getattr(pkg, "get_browser_job_result", get_browser_job_result)

        check_job = BrowserJob(
            action_type="check_user_tweets",
            profile_slug=profile_slug,
            params={"username": username, "max_age_minutes": 35},
            priority=0,
        )
        job_id = _enqueue(check_job)
        check_res = await asyncio.to_thread(_get_res, job_id, 35.0)

        if not check_res or not check_res.get("found_fresh_tweet"):
            continue

        tweet_data = check_res.get("tweet_data") or check_res.get("context") or check_res.get("result") or {}
        tweet_id = str(tweet_data.get("id") or tweet_data.get("tweet_id") or "")
        tweet_text = tweet_data.get("text", "")
        tweet_url = tweet_data.get("url") or tweet_data.get("tweet_url")

        if not tweet_id or not tweet_text:
            continue

        from xbot.safety.topic_blacklist import topic_blacklist_filter
        is_blocked, block_reason = topic_blacklist_filter.is_blocked(tweet_text, persona)
        if is_blocked:
            logger.info("ReplyPipeline: Sniper skipped tweet %s due to topic blacklist: %s", tweet_id, block_reason)
            continue

        if guard.is_target_acted_upon(profile_slug, "reply", tweet_id):
            continue

        opp_score = pkg.score_tweet_opportunity(tweet_data)
        if opp_score.recommended_action == "skip" and opp_score.score < 25.0:
            logger.info("ReplyPipeline: Sniper skipped tweet %s (score %.1f)", tweet_id, opp_score.score)
            continue

        top_comments = (
            tweet_data.get("top_comments")
            or tweet_data.get("comments")
            or tweet_data.get("replies_sample")
            or check_res.get("top_comments")
            or []
        )
        media_alts = tweet_data.get("media_alts") or tweet_data.get("image_descriptions") or check_res.get("media_alts") or []
        media_urls = tweet_data.get("media_urls") or tweet_data.get("images") or check_res.get("media_urls") or []
        views = tweet_data.get("views") or tweet_data.get("impressions") or check_res.get("views") or 0
        likes = tweet_data.get("likes") or check_res.get("likes") or 0
        replies = tweet_data.get("replies") or check_res.get("replies") or 0
        retweets = tweet_data.get("retweets") or check_res.get("retweets") or 0

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
        sniper_res = await pkg.generate_sniper_reply(
            persona=persona,
            target_tweet=target_payload,
            profile_slug=profile_slug,
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
            priority=0,
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
