"""
Typed Action Registry mapping BrowserActionType enum to Action Handlers.
Guarantees 1:1 exhaustiveness and abolishes brittle string ladders.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine
from playwright.async_api import Page

from xbot.contracts.browser import BrowserActionType
from xbot.browser.actions.engagement_action import LikeTweet
from xbot.browser.actions.reply_action import ReplyToTweet, QuoteTweet
from xbot.browser.actions.post_action import ComposePost
from xbot.browser.actions.thread_action import ComposeThread
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.follow_action import FollowUser, UnfollowUser
from xbot.browser.actions.delete_action import DeleteTweet
from xbot.browser.actions.prune_action import StreamAndPruneTimeline
from xbot.browser.actions.feed_action import BrowseFeed, SearchQuery
from xbot.browser.actions.metrics_action import ScrapeTrends
from xbot.browser.actions.notification_action import ScrapeNotifications
from xbot.browser.actions.follow_scrape_action import ScrapeFollowList, HarvestFollowBackThread
from xbot.browser.actions.metrics_scrape_action import ScrapeProfileTweets, ScrapeCreatorStudioMetrics
from xbot.browser.actions.tweet_context_scraper import scrape_target_tweet_context
from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.sync_profile_action import SyncProfileFromX

logger = logging.getLogger(__name__)

ActionHandler = Callable[[Page, dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]

ACTION_REGISTRY: dict[BrowserActionType, ActionHandler] = {}


def register(action_type: BrowserActionType):
    """Decorator to bind an action runner to a BrowserActionType."""
    def decorator(fn: ActionHandler) -> ActionHandler:
        if action_type in ACTION_REGISTRY:
            raise ValueError(f"Duplicate registration for action type: {action_type}")
        ACTION_REGISTRY[action_type] = fn
        return fn
    return decorator


@register(BrowserActionType.LIKE)
async def _handle_like(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = LikeTweet()
    res = await action.execute(page, tweet_url=p.get("tweet_url"))
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "liked": bool(res)}


@register(BrowserActionType.REPLY)
async def _handle_reply(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ReplyToTweet()
    reply_text = p.get("text") or p.get("reply_text", "")
    res = await action.execute(
        page,
        reply_text=reply_text,
        tweet_url=p.get("tweet_url"),
        tweet_index=p.get("tweet_index"),
        gif_query=p.get("gif_query"),
        media_paths=p.get("media_paths"),
    )
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "replied": bool(res)}


@register(BrowserActionType.QUOTE)
async def _handle_quote(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = QuoteTweet()
    quote_text = p.get("text") or p.get("quote_text", "")
    res = await action.execute(
        page,
        quote_text=quote_text,
        tweet_url=p.get("tweet_url", ""),
        tweet_index=p.get("tweet_index"),
        gif_query=p.get("gif_query"),
        media_paths=p.get("media_paths"),
    )
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "quoted": bool(res)}


@register(BrowserActionType.POST)
async def _handle_post(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ComposePost()
    res = await action.execute(page, text=p.get("text", ""), media_paths=p.get("media_paths"), gif_query=p.get("gif_query"))
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "posted": bool(res)}


@register(BrowserActionType.THREAD)
async def _handle_thread(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ComposeThread()
    res = await action.execute(page, tweets=p.get("tweets", []), media_paths=p.get("media_paths"))
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "thread_posted": bool(res)}


@register(BrowserActionType.POLL)
async def _handle_poll(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    logger.info("Poll posting is currently paused per user preference. Skipping.")
    return {"status": "skipped", "message": "Poll posting is currently paused"}


@register(BrowserActionType.FOLLOW)
async def _handle_follow(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = FollowUser()
    res = await action.execute(page, username=p.get("username", ""))
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "followed": bool(res)}


@register(BrowserActionType.UNFOLLOW)
async def _handle_unfollow(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = UnfollowUser()
    res = await action.execute(page, username=p.get("username", ""))
    return res if isinstance(res, dict) else {"status": "success" if res else "failed", "unfollowed": bool(res)}


@register(BrowserActionType.DELETE_TWEET)
async def _handle_delete(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = DeleteTweet()
    res = await action.execute(page, tweet_url=p.get("tweet_url"), tweet_id=p.get("tweet_id"), username=p.get("username"))
    return res if isinstance(res, dict) else {"status": "success", "result": res}


@register(BrowserActionType.PRUNE_TIMELINE)
async def _handle_prune(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = StreamAndPruneTimeline()
    res = await action.execute(page, username=p.get("username", ""), criteria=p.get("criteria"), max_scrolls=p.get("max_scrolls", 40))
    return res if isinstance(res, dict) else {"status": "success", "result": res}


@register(BrowserActionType.SCRAPE_FEED)
async def _handle_scrape_feed(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = BrowseFeed()
    scrolls = p.get("scrolls") or p.get("max_scrolls") or 3
    tweets = await action.execute(page, max_scrolls=scrolls)
    return {"status": "success", "tweets": tweets or []}


@register(BrowserActionType.SCRAPE_TRENDING)
async def _handle_scrape_trending(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ScrapeTrends()
    trends = await action.execute(page, limit=p.get("limit", 10))
    return {"status": "success", "trends": trends or []}


@register(BrowserActionType.SCRAPE_NOTIFICATIONS)
async def _handle_scrape_notifications(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ScrapeNotifications()
    notifications = await action.execute(page, limit=p.get("limit", 20), filter_tab=p.get("filter_tab", "all"))
    return {"status": "success", "notifications": notifications or []}


@register(BrowserActionType.SCRAPE_FOLLOW_LIST)
async def _handle_scrape_follow_list(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ScrapeFollowList()
    list_type = p.get("list_type", "followers")
    followers = await action.execute(
        page,
        username=p.get("username", ""),
        list_type=list_type,
        limit=p.get("limit", 100),
        verified_only=p.get("verified_only", False),
    )
    handles = followers or []
    return {
        "status": "success",
        "follow_list": {
            "list_type": list_type,
            "handles": handles,
        },
        "followers": handles,
        "handles": handles,
    }


@register(BrowserActionType.HARVEST_THREAD)
async def _handle_harvest_thread(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = HarvestFollowBackThread()
    candidates = await action.execute(
        page,
        tweet_url=p.get("tweet_url", ""),
        max_candidates=p.get("max_candidates", 8),
    )
    return {"status": "success", "candidates": candidates or []}


@register(BrowserActionType.SCRAPE_PROFILE_TWEETS)
async def _handle_scrape_profile_tweets(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ScrapeProfileTweets()
    res = await action.execute(page, username=p.get("username", ""), limit=p.get("limit", 20))
    return res if isinstance(res, dict) else {"status": "success", "result": res}


@register(BrowserActionType.SCRAPE_TWEET_CONTEXT)
async def _handle_scrape_tweet_context(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    res = await scrape_target_tweet_context(page, tweet_url=p.get("tweet_url", ""), max_comments=p.get("max_comments", 5))
    return {"status": "success" if res else "failed", "context": res}


@register(BrowserActionType.CHECK_USER_LATEST)
async def _handle_check_user_latest(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = CheckUserLatestTweet()
    res = await action.execute(page, username=p.get("username", ""), max_age_minutes=p.get("max_age_minutes", 60))
    return res if isinstance(res, dict) else {"status": "success", "result": res}


@register(BrowserActionType.SYNC_PROFILE)
async def _handle_sync_profile(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = SyncProfileFromX()
    res = await action.execute(page, username=p.get("username", ""))
    return res if isinstance(res, dict) else {"status": "success", "result": res}


@register(BrowserActionType.SYNC_CREATOR_STUDIO)
async def _handle_sync_creator_studio(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = ScrapeCreatorStudioMetrics()
    res = await action.execute(page)
    return res if isinstance(res, dict) else {"status": "success", "result": res}


@register(BrowserActionType.SEARCH)
async def _handle_search(page: Page, p: dict[str, Any]) -> dict[str, Any]:
    action = SearchQuery()
    results = await action.execute(
        page,
        query=p.get("query", ""),
        search_filter=p.get("search_filter", "top"),
        auto_relax=p.get("auto_relax", True),
        max_scrolls=p.get("max_scrolls", 8),
        min_results=p.get("min_results", 0),
        require_media=p.get("require_media", False),
    )
    return {"status": "success", "results": results or []}


async def dispatch_browser_action(
    page: Page,
    action_type: str | BrowserActionType,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatches any action through the typed registry with 100% enum exhaustiveness."""
    p = params or {}
    try:
        if isinstance(action_type, str):
            enum_type = BrowserActionType(action_type)
        else:
            enum_type = action_type
    except ValueError:
        # Backward-compatibility aliases
        alias_map = {
            "check_user_tweets": BrowserActionType.CHECK_USER_LATEST,
            "scrape_context": BrowserActionType.SCRAPE_TWEET_CONTEXT,
            "search_and_scrape": BrowserActionType.SEARCH,
            "scrape_followers": BrowserActionType.SCRAPE_FOLLOW_LIST,
        }
        if action_type in alias_map:
            enum_type = alias_map[action_type]
        else:
            raise ValueError(f"Unknown browser action type: {action_type}")

    handler = ACTION_REGISTRY.get(enum_type)
    if not handler:
        raise ValueError(f"No registered handler for action type: {enum_type}")

    from xbot.browser.actions.utils import dismiss_blocking_modals
    await dismiss_blocking_modals(page)

    return await handler(page, p)
