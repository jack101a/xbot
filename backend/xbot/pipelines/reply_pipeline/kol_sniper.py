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
from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.models.profile import Profile
from xbot.persona import load_config
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
    container: Container | None = None,
) -> int:
    """Checks KOL handles and executes sniper replies with enriched thread context via BrowserPort."""
    pkg = _get_pkg()
    profile_slug = profile.profile_slug
    c = container or get_container()

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

    # Rotate and sample up to 4 active KOLs per cycle
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

        if active_channels and category not in active_channels and category != "general":
            logger.info("ReplyPipeline: Skipping KOL @%s (channel '%s' is inactive)", username, category)
            continue

        check_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.CHECK_USER_LATEST,
            params={"username": username, "max_age_minutes": 35},
            timeout_seconds=35,
        )
        check_res = await c.browser.execute(check_req)
        raw_check = check_res.action_result.raw if (check_res.action_result and check_res.action_result.raw) else (check_res.scrape.raw if (check_res.scrape and check_res.scrape.raw) else {})

        if not raw_check.get("found_fresh_tweet") and check_res.status != "success":
            continue

        tweet_data = raw_check.get("tweet_data") or raw_check.get("context") or raw_check.get("result") or {}
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
            or raw_check.get("top_comments")
            or []
        )
        media_alts = tweet_data.get("media_alts") or tweet_data.get("image_descriptions") or raw_check.get("media_alts") or []
        media_urls = tweet_data.get("media_urls") or tweet_data.get("images") or raw_check.get("media_urls") or []
        views = tweet_data.get("views") or tweet_data.get("impressions") or raw_check.get("views") or 0
        likes = tweet_data.get("likes") or raw_check.get("likes") or 0
        replies = tweet_data.get("replies") or raw_check.get("replies") or 0
        retweets = tweet_data.get("retweets") or raw_check.get("retweets") or 0

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
