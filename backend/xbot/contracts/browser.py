"""
xbot.contracts.browser: Universal DTO contracts for BrowserPort requests & responses.
Replaces live Playwright Page instances across pipelines and tasks.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class BrowserActionType(str, Enum):
    LIKE = "like"
    REPLY = "reply"
    QUOTE = "quote"
    POST = "post"
    THREAD = "thread"
    POLL = "poll"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    DELETE_TWEET = "delete_tweet"
    PRUNE_TIMELINE = "prune_timeline"
    SCRAPE_FEED = "scrape_feed"
    SCRAPE_TRENDING = "scrape_trending"
    SCRAPE_NOTIFICATIONS = "scrape_notifications"
    SCRAPE_FOLLOW_LIST = "scrape_follow_list"
    SCRAPE_PROFILE_TWEETS = "scrape_profile_tweets"
    SCRAPE_TWEET_CONTEXT = "scrape_tweet_context"
    CHECK_USER_LATEST = "check_user_latest"
    SYNC_PROFILE = "sync_profile"
    SYNC_CREATOR_STUDIO = "sync_creator_studio"
    SEARCH = "search"
    HARVEST_THREAD = "harvest_thread"

    @property
    def is_write_action(self) -> bool:
        return self in {
            BrowserActionType.LIKE,
            BrowserActionType.REPLY,
            BrowserActionType.QUOTE,
            BrowserActionType.POST,
            BrowserActionType.THREAD,
            BrowserActionType.POLL,
            BrowserActionType.FOLLOW,
            BrowserActionType.UNFOLLOW,
            BrowserActionType.DELETE_TWEET,
            BrowserActionType.PRUNE_TIMELINE,
        }

    @property
    def is_read_action(self) -> bool:
        return not self.is_write_action


class BrowserRequest(BaseModel):
    """Universal envelope submitted to BrowserPort."""
    profile_slug: str
    action: BrowserActionType
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 120
    idempotency_key: Optional[str] = None


class ActionResult(BaseModel):
    """Result payload for state-modifying browser actions."""
    status: Literal["success", "failed", "skipped", "expired", "error"]
    detail: Optional[str] = None
    target_id: Optional[str] = None
    url: Optional[str] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class TweetData(BaseModel):
    """Normalized representation of a single scraped tweet."""
    tweet_id: str
    url: str
    handle: str
    text: str = ""
    created_at: Optional[str] = None
    is_pinned: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
    top_comments: list[dict[str, Any]] = Field(default_factory=list)
    media_alts: list[str] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    has_video: bool = False


class NotificationData(BaseModel):
    """Normalized notification item."""
    kind: str
    actor_handle: str
    text: str = ""
    tweet_url: Optional[str] = None


class FollowListResult(BaseModel):
    """Normalized list of handles from followers/following/verified_followers tab."""
    list_type: str
    handles: list[str] = Field(default_factory=list)
    unreciprocated_handles: list[str] = Field(default_factory=list)
    verified_unreciprocated_handles: list[str] = Field(default_factory=list)
    following_handles: list[str] = Field(default_factory=list)


class ScrapeResult(BaseModel):
    """Normalized aggregation payload for read actions."""
    tweets: list[TweetData] = Field(default_factory=list)
    trends: list[dict[str, Any]] = Field(default_factory=list)
    notifications: list[NotificationData] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    follow_list: Optional[FollowListResult] = None
    profile_data: Optional[dict[str, Any]] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class BrowserResponse(BaseModel):
    """Universal envelope returned by BrowserPort."""
    status: Literal["success", "failed", "skipped", "expired", "error"]
    action: BrowserActionType
    error: Optional[str] = None
    action_result: Optional[ActionResult] = None
    scrape: Optional[ScrapeResult] = None
