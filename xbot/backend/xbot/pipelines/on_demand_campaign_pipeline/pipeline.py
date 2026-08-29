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

    # 2. Iterate through deliverables
    for idx, spec in enumerate(plan.deliverables):
        step_base = 25 + int((idx / max(1, total_delivs)) * 65)
        update_campaign_status(
            campaign_id,
            current_step=f"Searching X and scraping media for: '{spec.topic[:40]}'",
            progress_percent=step_base,
        )

        # Real-time search on X
        scraped_posts = await pkg._search_and_scrape_x(spec.search_query, profile_slug)
        media_urls_to_download: list[str] = []

        scraped_context_snippets = []
        for post in scraped_posts[:8]:
            text = post.get("text", "")
            if text:
                scraped_context_snippets.append(f"- @{post.get('author', 'user')}: {text}")
            if spec.target_media_count > 0 and len(media_urls_to_download) < spec.target_media_count:
                for u in post.get("media_urls", []):
                    if u not in media_urls_to_download:
                        media_urls_to_download.append(u)

        context_summary = "\n".join(scraped_context_snippets) if scraped_context_snippets else spec.topic

        # Download viral media ONLY IF target_media_count > 0 and media was found
        downloaded_media: list[str] = []
        if spec.target_media_count > 0 and media_urls_to_download:
            update_campaign_status(
                campaign_id,
                current_step=f"Downloading {len(media_urls_to_download)} viral media assets...",
                progress_percent=step_base + 5,
            )
            downloaded_media = await pkg._download_media_urls(media_urls_to_download[:spec.target_media_count], campaign_media_dir)

        # 3. Synthesize deliverable based on type
        update_campaign_status(
            campaign_id,
            current_step=f"Synthesizing in persona: [{spec.type.upper()}] '{spec.topic[:40]}'",
            progress_percent=step_base + 10,
        )

        base_preview: dict[str, Any] = {
            "deliverable_id": spec.id,
            "type": spec.type.value if hasattr(spec.type, "value") else str(spec.type),
            "topic": spec.topic,
            "media_paths": downloaded_media if spec.target_media_count > 0 else [],
        }

        if spec.type == DeliverableType.THREAD:
            content_record, preview_dict = await synthesize_thread_deliverable(
                db, profile, spec, persona, context_summary, downloaded_media, campaign_id, profile_slug, pkg
            )
        elif spec.type == DeliverableType.POLL:
            content_record, preview_dict = await synthesize_poll_deliverable(
                db, profile, spec, persona, campaign_id, pkg
            )
        elif spec.type == DeliverableType.VISUAL:
            content_record, preview_dict = await synthesize_visual_deliverable(
                db, profile, spec, persona, downloaded_media, campaign_id, profile_slug, pkg
            )
        else:
            content_record, preview_dict = await synthesize_post_deliverable(
                db, profile, spec, persona, context_summary, downloaded_media, campaign_id, profile_slug, pkg
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

    logger.info("OnDemandCampaign: Successfully generated campaign %s with %d deliverables", campaign_id, len(generated_deliverables))
    return {
        "status": "ready",
        "campaign_id": campaign_id,
        "plan": plan.model_dump(),
        "deliverables": generated_deliverables,
    }
