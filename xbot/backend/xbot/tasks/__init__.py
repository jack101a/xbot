"""
Tasks package re-export facade.
Preserves 100% backward compatibility for imports, celery autodiscovery, and test patches.
"""
from __future__ import annotations

from xbot.celery_app import celery_app
app = celery_app

# Common symbols for tests and external callers
import redis
from xbot.config import settings
from xbot.database import AsyncSessionLocal
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.analytics import AnalyticsSnapshot, FollowerSnapshot, FollowerChangeLog
from xbot.models.realgraph import RealGraphEdge
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.persona import load_config
from xbot.persona.loader import load_persona
from xbot.safety.guard import SafetyGuard
from xbot.browser.manager import BrowserManager
from xbot.browser.timing import sleep_with_jitter, sleep_think_time
from xbot.browser.actions.x_actions import (
    BrowseFeed,
    CheckUserLatestTweet,
    ComposePost,
    CreatePoll,
    FollowEngagers,
    FollowUser,
    LikeTweet,
    QuoteTweet,
    ReplyToTweet,
    Retweet,
    ScrapeFollowList,
    ScrapeProfileMetrics,
    ScrapeTrends,
    SearchQuery,
    UnfollowNonFollowers,
    UnfollowUser,
)
from xbot.ai.sniper import generate_sniper_reply
from xbot.ai.planner import plan_session
from xbot.ai.trend_radar import fetch_rss_trends, fetch_multi_source_trends
from xbot.ai.trend_generator import generate_trend_take
from xbot.ai.visual_engine import generate_visual_post_spec
from xbot.ai.poll_generator import generate_poll
from xbot.ai.hook_optimizer import extract_links
from xbot.ai.growth_scorer import score_tweet_opportunity
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.generator import ContentGenerator

from .common import (
    extract_tweet_id_from_url,
    _parse_x_counts,
    has_already_acted,
    broadcast_session_log,
    _extract_or_generate_poll_data,
)
from .session_runner import _run_session_async
from .circadian_tasks import run_session, check_schedules
from .maintenance_tasks import _collect_analytics_snapshot_async, collect_analytics_snapshot
from .reflection_tasks import (
    _run_evergreen_recycling_async,
    run_evergreen_recycling,
    _run_persona_reflection_async,
    run_persona_reflection,
)
from .follower_audit import _run_follower_audit_async
from .sniper_tasks import _sniper_check_targets_async, sniper_check_targets
from .sentinel_tasks import _fast_response_sentinel_async, fast_response_sentinel
from .trend_tasks import _check_trend_radar_async, check_trend_radar
from .creator_sync_tasks import _sync_all_profiles_creator_studio_async, sync_all_profiles_creator_studio
from .publish_tasks import _auto_publish_pending_drafts_async, auto_publish_pending_drafts
from .growth_tasks import _run_growth_and_autofollowback_async, run_growth_and_autofollowback

__all__ = [
    "redis",
    "settings",
    "AsyncSessionLocal",
    "Profile",
    "ProfileStatus",
    "Action",
    "ActionStatus",
    "ActionType",
    "Session",
    "SessionStatus",
    "Content",
    "ContentStatus",
    "ContentType",
    "AnalyticsSnapshot",
    "FollowerSnapshot",
    "FollowerChangeLog",
    "RealGraphEdge",
    "FollowCandidate",
    "FollowRelationship",
    "load_config",
    "load_persona",
    "SafetyGuard",
    "BrowserManager",
    "sleep_with_jitter",
    "sleep_think_time",
    "BrowseFeed",
    "CheckUserLatestTweet",
    "ComposePost",
    "CreatePoll",
    "FollowEngagers",
    "FollowUser",
    "LikeTweet",
    "QuoteTweet",
    "ReplyToTweet",
    "Retweet",
    "ScrapeFollowList",
    "ScrapeProfileMetrics",
    "ScrapeTrends",
    "SearchQuery",
    "UnfollowNonFollowers",
    "UnfollowUser",
    "generate_sniper_reply",
    "plan_session",
    "fetch_rss_trends",
    "fetch_multi_source_trends",
    "generate_trend_take",
    "generate_visual_post_spec",
    "generate_poll",
    "extract_links",
    "score_tweet_opportunity",
    "extract_tweet_id_from_url",
    "_parse_x_counts",
    "has_already_acted",
    "broadcast_session_log",
    "_extract_or_generate_poll_data",
    "_run_session_async",
    "run_session",
    "check_schedules",
    "_collect_analytics_snapshot_async",
    "collect_analytics_snapshot",
    "_run_evergreen_recycling_async",
    "run_evergreen_recycling",
    "_run_persona_reflection_async",
    "run_persona_reflection",
    "_run_follower_audit_async",
    "_sniper_check_targets_async",
    "sniper_check_targets",
    "_fast_response_sentinel_async",
    "fast_response_sentinel",
    "_check_trend_radar_async",
    "check_trend_radar",
    "_sync_all_profiles_creator_studio_async",
    "sync_all_profiles_creator_studio",
    "_auto_publish_pending_drafts_async",
    "auto_publish_pending_drafts",
    "_run_growth_and_autofollowback_async",
    "run_growth_and_autofollowback",
]

from xbot.ai.client import get_ai_client
