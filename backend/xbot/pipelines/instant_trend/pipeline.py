from __future__ import annotations

from datetime import datetime
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from xbot.container import Container, get_container
from xbot.models.pipeline import InstantTrendCampaign
from xbot.models.profile import Profile
from xbot.persona import load_config
from xbot.pipelines.instant_trend.evaluator import evaluate_trend_candidates
from xbot.pipelines.instant_trend.executor import execute_trend_action
from xbot.pipelines.instant_trend.generator import generate_trend_commentary
from xbot.pipelines.instant_trend.types import InstantTrendCycleResult
from xbot.pipelines.instant_trend.x_searcher import search_x_for_trending_topic

logger = logging.getLogger(__name__)


async def run_instant_trend_cycle(
    campaign_id: str | uuid.UUID,
    db: AsyncSession,
    container: Container | None = None,
) -> InstantTrendCycleResult:
    """
    Executes a single end-to-end iteration of an instant trend campaign:
    1. Validates campaign status and 48-hour expiration.
    2. Searches X directly for trending topic tweets.
    3. Evaluates candidates and determines Quote vs Post action.
    4. Formulates persona take and submits through browser queue.
    """
    c = container or get_container()
    c_uuid = uuid.UUID(str(campaign_id)) if isinstance(campaign_id, str) else campaign_id

    campaign = await db.get(InstantTrendCampaign, c_uuid)
    if not campaign:
        return InstantTrendCycleResult(
            status="error",
            campaign_id=str(campaign_id),
            topic="",
            error=f"Campaign {campaign_id} not found in database",
        )

    now = datetime.utcnow()

    # 1. 48-Hour Lifecycle & Stop Check
    if now >= campaign.expires_at:
        logger.info("InstantTrend: Campaign %s reached 48h limit. Marking completed.", campaign.id)
        campaign.status = "completed"
        await db.commit()
        return InstantTrendCycleResult(
            status="completed",
            campaign_id=str(campaign.id),
            topic=campaign.topic,
        )

    if campaign.status != "active":
        logger.info("InstantTrend: Campaign %s is %s, skipping.", campaign.id, campaign.status)
        return InstantTrendCycleResult(
            status="skipped",
            campaign_id=str(campaign.id),
            topic=campaign.topic,
            error=f"Campaign is in '{campaign.status}' state",
        )

    # 2. Retrieve Profile & Persona
    profile = await db.get(Profile, campaign.profile_id)
    profile_slug = profile.profile_slug if profile else "test_profile1"

    persona_rules: list[str] = []
    try:
        from pathlib import Path
        prof_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "profiles" / profile_slug
        cfg = load_config(prof_dir)
        persona_rules = cfg.content_generation.formatting_rules or []
    except Exception:
        pass

    # 3. Search X Live DOM (X ONLY)
    candidates = await search_x_for_trending_topic(
        container=c,
        profile_slug=profile_slug,
        topic=campaign.topic,
    )

    # 4. Evaluate Candidates & Action Choice
    action_type, target_tweet = evaluate_trend_candidates(
        candidates=candidates,
        seen_tweet_ids=campaign.seen_tweet_ids or [],
        quote_percentage=campaign.quote_percentage,
    )

    # 5. Generate Persona Take with tone/sentiment guidance
    sentiment_tone = getattr(campaign, "sentiment_tone", "balanced") or "balanced"
    ragebait_percentage = getattr(campaign, "ragebait_percentage", 0) or 0

    commentary = await generate_trend_commentary(
        topic=campaign.topic,
        action_type=action_type,
        target_tweet=target_tweet,
        persona_rules=persona_rules,
        sentiment_tone=sentiment_tone,
        ragebait_percentage=ragebait_percentage,
    )

    # 6. Execute through QueuedBrowserAdapter
    result = await execute_trend_action(
        campaign=campaign,
        action_type=action_type,
        target_tweet=target_tweet,
        commentary=commentary,
        db=db,
        container=c,
        profile_slug=profile_slug,
    )

    return result
