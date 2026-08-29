"""
Central Browser Queue & Worker for XBot.

Serializes browser operations across all independent pipelines:
- Pipelines create lightweight BrowserJob descriptors and push them to the Redis queue.
- A single Browser Worker processes queued jobs in priority order.
- Guarantees zero lock collisions, no browser crashes from competing sessions, and full visibility.
"""

from __future__ import annotations

from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    ComposePost,
    ComposeThread,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    ScrapeCreatorStudioMetrics,
    ScrapeTrends,
    SearchQuery,
    UnfollowUser,
    scrape_target_tweet_context,
)
from xbot.pipelines.browser_queue.queue import (
    BrowserJob,
    JOB_PREFIX,
    QUEUE_KEY,
    QUEUE_LOCK_KEY,
    RESULT_PREFIX,
    enqueue_browser_job,
    get_browser_job_result,
    get_queue_depth,
    get_redis_client,
    pop_next_job,
    set_browser_job_result,
)
from xbot.pipelines.browser_queue.worker import (
    _process_browser_queue_async,
    execute_browser_action,
    process_browser_queue,
    process_single_job,
)

__all__ = [
    "BrowserJob",
    "QUEUE_KEY",
    "JOB_PREFIX",
    "RESULT_PREFIX",
    "QUEUE_LOCK_KEY",
    "get_redis_client",
    "enqueue_browser_job",
    "get_browser_job_result",
    "set_browser_job_result",
    "get_queue_depth",
    "pop_next_job",
    "execute_browser_action",
    "process_single_job",
    "_process_browser_queue_async",
    "process_browser_queue",
    "scrape_target_tweet_context",
    "LikeTweet",
    "ReplyToTweet",
    "QuoteTweet",
    "ComposePost",
    "ComposeThread",
    "CreatePoll",
    "FollowUser",
    "UnfollowUser",
    "BrowseFeed",
    "ScrapeTrends",
    "CheckUserLatestTweet",
    "SyncProfileFromX",
    "SearchQuery",
    "ScrapeCreatorStudioMetrics",
]
