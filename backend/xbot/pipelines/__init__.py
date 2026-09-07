"""
XBot Autonomous Pipelines Package.

Contains independent, decoupled execution pipelines for:
- Like Pipeline (like_pipeline.py)
- Reply Pipeline (reply_pipeline.py)
- Quote Pipeline (quote_pipeline.py)
- Follow Pipeline (follow_pipeline.py)
- Trend Researcher Pipeline (trend_researcher_pipeline.py)
- Trend Generator Pipeline (trend_generator_pipeline.py)
- Central Browser Queue Worker (browser_queue.py)
- Central Guard & Rate Limiter (central_guard.py)
"""

from xbot.pipelines.browser_queue import (
    BrowserJob,
    enqueue_browser_job,
    get_browser_job_result,
    get_queue_depth,
    process_browser_queue,
    set_browser_job_result,
)
from xbot.pipelines.central_guard import CentralGuard, get_current_ist_time, is_within_active_hours
from xbot.pipelines.follow_pipeline import run_follow_pipeline
from xbot.pipelines.like_pipeline import run_like_pipeline
from xbot.pipelines.quote_pipeline import run_quote_pipeline
from xbot.pipelines.reply_pipeline import run_reply_pipeline
from xbot.pipelines.trend_generator_pipeline import run_trend_generator
from xbot.pipelines.trend_researcher_pipeline import run_trend_researcher
from xbot.pipelines.post_pruner_pipeline import (
    PrunerFilterCriteria,
    ScrapedProfileTweet,
    evaluate_tweet_for_pruning,
    run_post_pruner_for_profile,
)

__all__ = [
    "BrowserJob",
    "enqueue_browser_job",
    "get_browser_job_result",
    "get_queue_depth",
    "process_browser_queue",
    "set_browser_job_result",
    "CentralGuard",
    "get_current_ist_time",
    "is_within_active_hours",
    "run_like_pipeline",
    "run_reply_pipeline",
    "run_quote_pipeline",
    "run_follow_pipeline",
    "run_trend_researcher",
    "run_trend_generator",
    "PrunerFilterCriteria",
    "ScrapedProfileTweet",
    "evaluate_tweet_for_pruning",
    "run_post_pruner_for_profile",
]
