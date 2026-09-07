"""
Unified Reply Pipeline for XBot Pro.

Runs every 5 minutes (during active hours: 6:00 AM - 2:00 AM IST):
Merges 3 high-impact reply engines:
1. Priority 1 (Sniper): Scans target KOL handles for fresh tweets (<30m), evaluates Phoenix opportunity score, crafts value-first debate catalyst replies (Priority 0 job).
2. Priority 2 (Fast Response Sentinel): Follows up on active conversations within the 15m window to capture the +150x author engagement multiplier (Priority 1 job).
3. Priority 3 (Feed Opportunities): Scans feed for high-leverage tweets and replies with structured archetypes (Priority 2 job).

Applies:
- Anti-AI Gatekeeper validation & quote stripping
- Dynamic Formatting Engine (archetype rotation, whitespace pacing, trailing emoji stripping)
- 48-hour deduplication and rate limits via CentralGuard
- Logs every cycle in PipelineRun.
"""

from __future__ import annotations

# Internal module symbols
from xbot.pipelines.reply_pipeline.evaluator import _get_persona_for_profile
from xbot.pipelines.reply_pipeline.generator import (
    execute_fast_response_replies,
    execute_feed_replies,
)
from xbot.pipelines.reply_pipeline.kol_sniper import execute_kol_sniper_replies
from xbot.pipelines.reply_pipeline.pipeline import (
    _run_reply_pipeline_async,
    run_reply_pipeline,
    run_reply_pipeline_for_profile,
)

# AI & browser queue helpers for backward compatibility & test patching
from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.formatting_engine import format_content
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.sniper import generate_sniper_reply
from xbot.pipelines.browser_queue import (
    enqueue_browser_job,
    get_browser_job_result,
)

__all__ = [
    "execute_kol_sniper_replies",
    "execute_fast_response_replies",
    "execute_feed_replies",
    "run_reply_pipeline_for_profile",
    "_run_reply_pipeline_async",
    "run_reply_pipeline",
    "_get_persona_for_profile",
    "generate_sniper_reply",
    "score_tweet_opportunity",
    "format_content",
    "strip_surrounding_quotes",
    "enqueue_browser_job",
    "get_browser_job_result",
]
