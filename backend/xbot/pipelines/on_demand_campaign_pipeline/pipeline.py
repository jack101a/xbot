"""
On-Demand Campaign Pipeline Main Execution Engine.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
import sys
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.campaign_planner import DeliverableType, plan_campaign_from_prompt
from xbot.config import settings
from xbot.models.content import Content
from xbot.models.profile import Profile
from xbot.pipelines.on_demand_campaign_pipeline.prompts import (
    _download_media_urls,
    _get_persona_for_profile,
    _search_and_scrape_x,
    update_campaign_status,
)
from xbot.pipelines.on_demand_campaign_pipeline.synthesizers import (
    synthesize_poll_deliverable,
    synthesize_post_deliverable,
    synthesize_thread_deliverable,
    synthesize_visual_deliverable,
)

logger = logging.getLogger(__name__)


def _get_pkg():
    return sys.modules.get("xbot.pipelines.on_demand_campaign_pipeline") or sys.modules[__name__]


async def execute_on_demand_campaign(
    profile_id: uuid.UUID | str,
    prompt: str,
    campaign_id: str,
    db: AsyncSession,
    duration_hours: int = 0,
    interval_minutes: int = 60,
    source_type: str = "on_demand",
    media_preference: str = "x_official",
) -> dict[str, Any]:
    """
    Executes full end-to-end on-demand campaign generation from a user prompt.
    """
    pkg = _get_pkg()
    if isinstance(profile_id, str):
        profile_id = uuid.UUID(profile_id)

    profile = (await db.execute(select(Profile).where(Profile.id == profile_id))).scalar_one_or_none()
    if not profile:
        raise ValueError(f"Profile {profile_id} not found in database.")

    profile_slug = profile.profile_slug
    persona = _get_persona_for_profile(profile_slug)

    update_campaign_status(
        campaign_id,
        status="decomposing",
        current_step="Decomposing natural-language prompt into deliverables...",
        progress_percent=10,
    )

    # 1. Decompose prompt into CampaignPlan
    plan = await pkg.plan_campaign_from_prompt(prompt=prompt, persona=persona)
    update_campaign_status(
        campaign_id,
        status="researching",
        plan=plan.model_dump(),
        current_step=f"Planned {len(plan.deliverables)} deliverables. Initiating research...",
        progress_percent=25,
    )

    campaign_media_dir = Path(settings.BASE_PROFILE_DIR) / profile_slug / "media" / f"campaign_{campaign_id}"
    generated_deliverables: list[dict[str, Any]] = []

    total_delivs = len(plan.deliverables)

    # 2. Master Campaign Research & Authentic Media Scraping
    primary_query = prompt[:60]
    if plan.deliverables and plan.deliverables[0].search_query:
        primary_query = plan.deliverables[0].search_query

    update_campaign_status(
        campaign_id,
        status="researching",
        current_step=f"Searching X for authentic media & verified discourse: '{primary_query[:40]}'",
        progress_percent=30,
    )

    # Scrape top posts from X
    scraped_posts = await pkg._search_and_scrape_x(primary_query, profile_slug, search_filter="top")
    
    # Collect media URLs from top search
    media_urls_to_download: list[str] = []
    for post in scraped_posts:
        for u in post.get("media_urls", []):
            if u not in media_urls_to_download:
                media_urls_to_download.append(u)

    # If media is preferred and we have fewer than 4 images, also search the media tab for authentic stills
    if len(media_urls_to_download) < 4 and media_preference == "x_official":
        media_posts = await pkg._search_and_scrape_x(primary_query, profile_slug, search_filter="media")
        if media_posts:
            scraped_posts = scraped_posts + media_posts
            for post in media_posts:
                for u in post.get("media_urls", []):
                    if u not in media_urls_to_download:
                        media_urls_to_download.append(u)

    # Prioritize verified / blue tick accounts (studios, journalists, creators)
    sorted_posts = sorted(scraped_posts, key=lambda p: 1 if p.get("is_blue_tick") else 0, reverse=True)

    master_context_snippets = []
    for post in sorted_posts[:15]:
        text = post.get("text", "")
        if text:
            verified_tag = " [VERIFIED]" if post.get("is_blue_tick") else ""
            master_context_snippets.append(f"- @{post.get('author', 'user')}{verified_tag}: {text}")
            for c in post.get("top_comments", [])[:5]:
                c_text = c.get("text", "").strip()
                if c_text:
                    likes_badge = f" ({c.get('likes')} likes)" if c.get("likes") else ""
                    master_context_snippets.append(f"   [Community Debate Reply from @{c.get('author', 'fan')}{likes_badge}]: {c_text}")

    master_context_summary = "\n".join(master_context_snippets) if master_context_snippets else prompt

    # Download authentic high-res media pool from X (up to 8 assets)
    downloaded_media_pool: list[str] = []
    if media_urls_to_download and media_preference == "x_official":
        update_campaign_status(
            campaign_id,
            current_step=f"Downloading {len(media_urls_to_download[:8])} authentic media assets from X...",
            progress_percent=45,
        )
        downloaded_media_pool = await pkg._download_media_urls(media_urls_to_download[:8], campaign_media_dir)

    # Track used media paths to prevent repeating any image across deliverables
    used_media_paths: set[str] = set()
    try:
        from datetime import datetime, timedelta
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_recs = (await db.execute(
            select(Content.ai_metadata).where(
                Content.profile_id == profile.id,
                Content.created_at >= seven_days_ago,
            )
        )).scalars().all()
        for meta in recent_recs:
            if isinstance(meta, dict):
                for p in meta.get("media_paths", []):
                    used_media_paths.add(p)
                for u in meta.get("media_urls", []):
                    used_media_paths.add(u)
    except Exception as db_err:
        logger.warning("Could not load recent media history for deduplication: %s", db_err)

    # 3. Iterate through deliverables and synthesize with persona
    for idx, spec in enumerate(plan.deliverables):
        step_base = 50 + int((idx / max(1, total_delivs)) * 45)
        update_campaign_status(
            campaign_id,
            current_step=f"Synthesizing [{spec.type.upper()}] '{spec.topic[:35]}'",
            progress_percent=step_base,
        )

        context_summary = master_context_summary

        base_preview: dict[str, Any] = {
            "deliverable_id": spec.id,
            "type": spec.type.value if hasattr(spec.type, "value") else str(spec.type),
            "topic": spec.topic,
            "media_paths": [],
        }

        if spec.type == DeliverableType.THREAD:
            content_record, preview_dict = await synthesize_thread_deliverable(
                db, profile, spec, persona, context_summary, downloaded_media_pool, campaign_id, profile_slug, pkg, used_media_paths
            )
        elif spec.type == DeliverableType.POLL:
            content_record, preview_dict = await synthesize_poll_deliverable(
                db, profile, spec, persona, campaign_id, pkg
            )
        elif spec.type == DeliverableType.VISUAL:
            content_record, preview_dict = await synthesize_visual_deliverable(
                db, profile, spec, persona, downloaded_media_pool, campaign_id, profile_slug, pkg, used_media_paths
            )
        else:
            content_record, preview_dict = await synthesize_post_deliverable(
                db, profile, spec, persona, context_summary, downloaded_media_pool, campaign_id, profile_slug, pkg, used_media_paths
            )

        base_preview.update(preview_dict)
        await db.commit()
        await db.refresh(content_record)

        base_preview["content_id"] = str(content_record.id)
        base_preview["status"] = content_record.status.value if hasattr(content_record.status, "value") else str(content_record.status)
        generated_deliverables.append(base_preview)

    # 4. Finalize campaign state
    update_campaign_status(
        campaign_id,
        status="ready",
        current_step="All campaign deliverables synthesized and ready for publishing!",
        progress_percent=100,
        deliverables=generated_deliverables,
    )

    # 5. Persist campaign to database so it survives server restarts
    try:
        from xbot.models.pipeline import Campaign
        from datetime import datetime, timedelta

        c_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, campaign_id) if not isinstance(campaign_id, uuid.UUID) else campaign_id
        camp_duration = duration_hours if duration_hours and duration_hours > 0 else 24
        camp_interval = interval_minutes if interval_minutes and interval_minutes > 0 else 60

        existing_c = await db.get(Campaign, c_uuid)
        if existing_c:
            existing_c.status = "ready"
            existing_c.plan_metadata = plan.model_dump()
            existing_c.deliverables = generated_deliverables
            existing_c.media_preference = media_preference
        else:
            campaign_db = Campaign(
                id=c_uuid,
                profile_id=profile_id,
                topic=prompt[:250],
                status="ready",
                campaign_type="on_demand" if duration_hours == 0 else "continuous",
                source_type=source_type,
                duration_hours=camp_duration,
                interval_minutes=camp_interval,
                media_preference=media_preference,
                plan_metadata=plan.model_dump(),
                deliverables=generated_deliverables,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=camp_duration),
                next_run_at=datetime.utcnow() + timedelta(minutes=camp_interval),
            )
            db.add(campaign_db)
        await db.commit()
    except Exception as db_err:
        logger.warning("Could not persist campaign %s to database: %s", campaign_id, db_err)

    logger.info("OnDemandCampaign: Successfully generated campaign %s with %d deliverables", campaign_id, len(generated_deliverables))
    return {
        "status": "ready",
        "campaign_id": campaign_id,
        "plan": plan.model_dump(),
        "deliverables": generated_deliverables,
    }
