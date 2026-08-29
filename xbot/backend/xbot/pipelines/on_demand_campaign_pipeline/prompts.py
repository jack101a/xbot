"""
On-Demand Campaign Prompts Tracker, Search, and Media Utilities.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
from typing import Any
import uuid

import httpx

from xbot.config import settings
from xbot.persona import load_persona
from xbot.persona.loader import Persona
from xbot.pipelines.browser_queue import BrowserJob, enqueue_browser_job, get_browser_job_result

logger = logging.getLogger(__name__)

# In-memory status tracker for live campaign generation
CAMPAIGN_TRACKER: dict[str, dict[str, Any]] = {}


def get_campaign_status(campaign_id: str) -> dict[str, Any]:
    """Retrieves live generation status and preview payload for a campaign."""
    return CAMPAIGN_TRACKER.get(
        campaign_id,
        {
            "status": "not_found",
            "campaign_id": campaign_id,
            "current_step": "idle",
            "progress_percent": 0,
            "deliverables": [],
        },
    )


def update_campaign_status(campaign_id: str, **kwargs: Any) -> None:
    """Updates campaign generation status in tracker."""
    if campaign_id not in CAMPAIGN_TRACKER:
        CAMPAIGN_TRACKER[campaign_id] = {
            "campaign_id": campaign_id,
            "status": "initializing",
            "current_step": "Starting campaign planner...",
            "progress_percent": 0,
            "plan": None,
            "deliverables": [],
            "error": None,
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
    CAMPAIGN_TRACKER[campaign_id].update(kwargs)


async def _search_and_scrape_x(query: str, profile_slug: str) -> list[dict[str, Any]]:
    """Enqueues and awaits real-time X search results for a given query."""
    try:
        job = BrowserJob(
            action_type="search_and_scrape",
            profile_slug=profile_slug,
            params={"query": query},
            priority=1,  # High priority on-demand user task
        )
        job_id = enqueue_browser_job(job)
        res = await asyncio.to_thread(get_browser_job_result, job_id, 45.0)
        if res and res.get("status") == "success":
            return res.get("results", [])
    except Exception as e:
        logger.warning("OnDemandCampaign: Search query '%s' encountered error: %s", query, e)
    return []


async def _download_media_urls(media_urls: list[str], output_dir: Path) -> list[str]:
    """Downloads remote image URLs to local profile media storage."""
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths: list[str] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for idx, url in enumerate(media_urls):
            if not url or not url.startswith("http"):
                continue
            try:
                ext = ".jpg"
                if ".png" in url.lower():
                    ext = ".png"
                elif ".webp" in url.lower():
                    ext = ".webp"

                target_file = output_dir / f"asset_{idx + 1}_{uuid.uuid4().hex[:6]}{ext}"
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 1024:
                    target_file.write_bytes(resp.content)
                    downloaded_paths.append(str(target_file))
                    logger.info("Downloaded campaign media: %s", target_file)
            except Exception as dl_err:
                logger.warning("Failed to download media URL %s: %s", url, dl_err)

    return downloaded_paths


def _get_persona_for_profile(profile_slug: str) -> Persona | None:
    try:
        cfg_path = Path(settings.BASE_PROFILE_DIR) / profile_slug
        if (cfg_path / "persona.yaml").exists():
            return load_persona(cfg_path)
    except Exception:
        pass
    return None
