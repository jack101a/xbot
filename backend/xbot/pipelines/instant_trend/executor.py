from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from xbot.container import Container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.pipeline import InstantTrendCampaign
from xbot.pipelines.instant_trend.types import InstantTrendCycleResult, TrendCandidateTweet

logger = logging.getLogger(__name__)


async def execute_trend_action(
    campaign: InstantTrendCampaign,
    action_type: str,
    target_tweet: TrendCandidateTweet | None,
    commentary: str,
    db: AsyncSession,
    container: Container,
    profile_slug: str,
) -> InstantTrendCycleResult:
    """
    Dispatches a quote or post action through the QueuedBrowserAdapter,
    records the action in the database, and schedules the next execution window.
    """
    now = datetime.utcnow()
    target_url = target_tweet.url if target_tweet else None
    target_id = target_tweet.tweet_id if target_tweet else None

    # Formulate BrowserRequest
    if action_type == "quote" and target_url:
        logger.info("InstantTrend: Executing QUOTE for target: %s (media=%s, hashtags=%s)",
                    target_url, target_tweet.media_urls if target_tweet else [], target_tweet.hashtags if target_tweet else [])
        browser_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.QUOTE,
            params={"text": commentary, "tweet_url": target_url},
            timeout_seconds=90,
        )
    else:
        logger.info("InstantTrend: Executing STANDALONE POST: %s", commentary[:40])
        action_type = "post"
        media_to_attach = target_tweet.media_urls if target_tweet and target_tweet.media_urls else None
        browser_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.POST,
            params={"text": commentary, "media_urls": media_to_attach},
            timeout_seconds=90,
        )

    res = await container.browser.execute(browser_req)
    is_success = res.status in ("success", "ok")

    # Record Content entry in DB
    try:
        content_item = Content(
            id=uuid.uuid4(),
            profile_id=campaign.profile_id,
            content_type=ContentType.ORIGINAL if action_type == "post" else ContentType.REPLY,
            body=commentary,
            status=ContentStatus.POSTED if is_success else ContentStatus.FAILED,
            posted_at=now if is_success else None,
            ai_metadata={
                "campaign_id": str(campaign.id),
                "topic": campaign.topic,
                "action_type": action_type,
                "target_url": target_url,
            },
        )
        db.add(content_item)
    except Exception as db_err:
        logger.warning("InstantTrend: Could not record Content row: %s", db_err)

    # Update Campaign Ledger & Next Cadence
    seen_list = list(campaign.seen_tweet_ids or [])
    if target_id and target_id not in seen_list:
        seen_list.append(target_id)
    campaign.seen_tweet_ids = seen_list

    actions_list = list(campaign.posted_actions or [])
    actions_list.append({
        "timestamp": now.isoformat(),
        "action_type": action_type,
        "target_url": target_url,
        "target_author": target_tweet.author if target_tweet else None,
        "commentary": commentary,
        "success": is_success,
        "error": res.error,
    })
    campaign.posted_actions = actions_list

    campaign.last_run_at = now
    campaign.next_run_at = now + timedelta(minutes=campaign.interval_minutes)

    await db.commit()
    await db.refresh(campaign)

    return InstantTrendCycleResult(
        status="success" if is_success else "error",
        campaign_id=str(campaign.id),
        topic=campaign.topic,
        action_type=action_type,
        tweet_id=target_id,
        target_tweet_url=target_url,
        content_posted=commentary,
        error=res.error if not is_success else None,
        executed_at=now,
    )
