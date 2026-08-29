"""
On-Demand Campaign Pipeline for XBot Pro (AI Creative Director & Prompt-to-Campaign).

Orchestrates:
1. Natural language prompt decomposition into typed deliverables via CampaignPlanner.
2. Real-time X deep search and sentiment extraction for each deliverable.
3. Live media scraping and downloading (actual viral photos/screenshots from X).
4. In-persona synthesis for threads, interactive polls, 4:5 visual memes, and hot takes.
5. Anti-AI and dynamic formatting enforcement (0 forced '?', no quotes).
6. Database staging in Content table and real-time status streaming.
7. Publishing execution: Instant live browser dispatch or staggered auto-scheduling.
"""

from __future__ import annotations

# Internal module symbols
from xbot.pipelines.on_demand_campaign_pipeline.executor import publish_campaign_deliverables
from xbot.pipelines.on_demand_campaign_pipeline.pipeline import execute_on_demand_campaign
from xbot.pipelines.on_demand_campaign_pipeline.prompts import (
    CAMPAIGN_TRACKER,
    _download_media_urls,
    _get_persona_for_profile,
    _search_and_scrape_x,
    get_campaign_status,
    update_campaign_status,
)

# Re-exports for mock compatibility & external callers
from xbot.ai.campaign_planner import plan_campaign_from_prompt
from xbot.ai.poll_generator import generate_poll
from xbot.ai.post_synthesizer import synthesize_creator_post
from xbot.ai.thread_generator import generate_thread
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.ai.hook_optimizer import optimize_post_for_virality

__all__ = [
    "CAMPAIGN_TRACKER",
    "get_campaign_status",
    "update_campaign_status",
    "execute_on_demand_campaign",
    "publish_campaign_deliverables",
    "_get_persona_for_profile",
    "_search_and_scrape_x",
    "_download_media_urls",
    "plan_campaign_from_prompt",
    "generate_thread",
    "generate_poll",
    "generate_visual_post_spec",
    "synthesize_creator_post",
    "optimize_post_for_virality",
]

from xbot.ai.client import get_ai_client
