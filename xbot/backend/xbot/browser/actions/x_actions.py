"""
X (Twitter) browser action implementations facade.
Re-exports modular action classes and utilities for backward compatibility.
"""
from __future__ import annotations

from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.actions.utils import (
    check_target_tweet_status,
    _navigate_home_if_needed,
    _random_tab_detour,
    _post_action_cooldown_browse,
    _extract_tweet_id_from_url,
    human_scroll_to_tweet,
)
from xbot.browser.actions.post_utils import (
    _attach_gif_if_requested,
    _attach_media_files,
    smart_truncate_tweet_text,
)
from xbot.browser.actions.post_action import ComposePost
from xbot.browser.actions.thread_action import ComposeThread
from xbot.browser.actions.reply_action import ReplyToTweet, QuoteTweet
from xbot.browser.actions.tweet_context_scraper import scrape_target_tweet_context
from xbot.browser.actions.delete_action import DeleteTweet
from xbot.browser.actions.engagement_action import LikeTweet, Retweet
from xbot.browser.actions.follow_action import FollowUser, UnfollowUser, CheckProfileFollowsYou
from xbot.browser.actions.bulk_follow_action import UnfollowNonFollowers, FollowEngagers
from xbot.browser.actions.follow_scrape_action import ScrapeFollowList, HarvestFollowBackThread
from xbot.browser.actions.feed_action import BrowseFeed, SearchQuery
from xbot.browser.actions.metrics_action import ScrapeProfileMetrics, ScrapeTrends
from xbot.browser.actions.metrics_scrape_action import ScrapeProfileTweets, ScrapeCreatorStudioMetrics
from xbot.browser.actions.notification_action import ScrapeNotifications, NotificationItem

__all__ = [
    "BaseAction",
    "CheckUserLatestTweet",
    "CreatePoll",
    "SELECTORS",
    "SyncProfileFromX",
    "check_target_tweet_status",
    "_navigate_home_if_needed",
    "_random_tab_detour",
    "_post_action_cooldown_browse",
    "_extract_tweet_id_from_url",
    "human_scroll_to_tweet",
    "_attach_gif_if_requested",
    "_attach_media_files",
    "smart_truncate_tweet_text",
    "ComposePost",
    "ComposeThread",
    "ReplyToTweet",
    "QuoteTweet",
    "scrape_target_tweet_context",
    "DeleteTweet",
    "LikeTweet",
    "Retweet",
    "FollowUser",
    "UnfollowUser",
    "CheckProfileFollowsYou",
    "UnfollowNonFollowers",
    "FollowEngagers",
    "ScrapeFollowList",
    "HarvestFollowBackThread",
    "BrowseFeed",
    "SearchQuery",
    "ScrapeProfileMetrics",
    "ScrapeTrends",
    "ScrapeProfileTweets",
    "ScrapeCreatorStudioMetrics",
    "ScrapeNotifications",
    "NotificationItem",
]
