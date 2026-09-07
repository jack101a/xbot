from __future__ import annotations

import asyncio
import datetime
import logging
from pathlib import Path
import re
from typing import Any, Literal
import uuid

from pydantic import BaseModel, Field
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.config import settings
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.pipelines.browser_queue.queue import get_redis_client
from xbot.browser.timing import human_click, sleep_with_jitter

logger = logging.getLogger(__name__)


class PrunerFilterCriteria(BaseModel):
    min_views: int = Field(default=200, ge=0, description="Delete if impressions/views are below this threshold")
    min_likes: int = Field(default=5, ge=0, description="Delete if likes are below this threshold")
    min_comments: int = Field(default=2, ge=0, description="Delete if replies/comments are below this threshold")
    min_age_hours: int = Field(default=24, ge=0, description="Minimum post age in hours before evaluation (grace period)")
    max_posts_to_delete: int = Field(default=10, ge=1, le=500, description="Maximum number of posts to delete per run")
    match_mode: Literal["all", "any"] = Field(
        default="all",
        description="'all' = strict (all criteria must fail); 'any' = aggressive (any criterion failure triggers delete)",
    )
    dry_run: bool = Field(default=False, description="Dry-run scan without deleting")


class ScrapedProfileTweet(BaseModel):
    tweet_id: str
    tweet_url: str
    text: str = ""
    views: int = 0
    likes: int = 0
    retweets: int = 0
    comments: int = 0
    is_reply: bool = False
    is_retweet: bool = False
    is_pinned: bool = False
    created_at: datetime.datetime | None = None
    age_hours: float | None = None


def evaluate_tweet_for_pruning(
    tweet: ScrapedProfileTweet,
    criteria: PrunerFilterCriteria,
) -> tuple[bool, str]:
    """
    Evaluates whether an individual tweet on a profile should be pruned.
    Guarantees:
    - Never deletes replies, retweets, or pinned posts.
    - Respects grace period (min_age_hours).
    - Applies strict ('all') or aggressive ('any') metric matching.
    """
    if tweet.is_reply:
        return False, "skipped_reply"
    if tweet.is_retweet:
        return False, "skipped_retweet"
    if tweet.is_pinned:
        return False, "skipped_pinned_post"
    if criteria.min_age_hours > 0 and tweet.age_hours is not None and tweet.age_hours < criteria.min_age_hours:
        return False, f"skipped_too_recent ({tweet.age_hours:.1f}h < {criteria.min_age_hours}h)"

    active_filters: list[str] = []
    failed_parts: list[str] = []

    # Views threshold
    if criteria.min_views > 0:
        views_failed = tweet.views < criteria.min_views
        active_filters.append("views")
        if views_failed:
            failed_parts.append(f"views {tweet.views}<{criteria.min_views}")
    else:
        views_failed = True if criteria.match_mode == "all" else False

    # Likes threshold
    if criteria.min_likes > 0:
        likes_failed = tweet.likes < criteria.min_likes
        active_filters.append("likes")
        if likes_failed:
            failed_parts.append(f"likes {tweet.likes}<{criteria.min_likes}")
    else:
        likes_failed = True if criteria.match_mode == "all" else False

    # Comments threshold
    if criteria.min_comments > 0:
        comments_failed = tweet.comments < criteria.min_comments
        active_filters.append("comments")
        if comments_failed:
            failed_parts.append(f"comments {tweet.comments}<{criteria.min_comments}")
    else:
        comments_failed = True if criteria.match_mode == "all" else False

    if not active_filters:
        return False, "no_active_metric_filters"

    if criteria.match_mode == "all":
        should_delete = views_failed and likes_failed and comments_failed
        reason = f"all_active_metrics_below ({', '.join(failed_parts)})" if failed_parts else "all_active_metrics_below"
    else:  # "any"
        should_delete = views_failed or likes_failed or comments_failed
        reason = f"metric_below_threshold ({', '.join(failed_parts)})" if failed_parts else "metric_below_threshold"

    return should_delete, reason


from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest


async def run_post_pruner_for_profile(
    profile_id: uuid.UUID,
    criteria: PrunerFilterCriteria,
    db: AsyncSession,
    r: redis.Redis | None = None,
    custom_scraped_tweets: list[dict[str, Any]] | None = None,
    container: Container | None = None,
) -> dict[str, Any]:
    """Executes the Post Pruner for a profile using BrowserPort."""
    if r is None:
        r = get_redis_client()
    c = container or get_container()

    profile_stmt = select(Profile).where(Profile.id == profile_id)
    p_res = await db.execute(profile_stmt)
    profile = p_res.scalar_one_or_none()
    if not profile:
        raise ValueError(f"Profile {profile_id} not found")

    username = (profile.x_handle or profile.profile_slug or "").lstrip("@")
    profile_slug = profile.profile_slug

    deleted_posts: list[dict[str, Any]] = []
    total_scanned = 0

    if custom_scraped_tweets is not None:
        total_scanned = len(custom_scraped_tweets)
        for raw in custom_scraped_tweets:
            tw_obj = ScrapedProfileTweet(
                tweet_id=str(raw.get("tweet_id") or raw.get("id") or ""),
                tweet_url=str(raw.get("tweet_url") or raw.get("url") or f"https://x.com/{username}/status/{raw.get('tweet_id', '')}"),
                text=str(raw.get("text") or ""),
                views=int(raw.get("views") or raw.get("impressions") or 0),
                likes=int(raw.get("likes") or 0),
                retweets=int(raw.get("retweets") or 0),
                comments=int(raw.get("comments") or raw.get("replies") or 0),
                is_reply=bool(raw.get("is_reply", False)),
                is_retweet=bool(raw.get("is_retweet", False)),
                is_pinned=bool(raw.get("is_pinned", False)),
                age_hours=float(raw.get("age_hours")) if raw.get("age_hours") is not None else 48.0,
            )
            should_del, reason = evaluate_tweet_for_pruning(tw_obj, criteria)
            if should_del:
                del_req = BrowserRequest(
                    profile_slug=profile_slug,
                    action=BrowserActionType.DELETE_TWEET,
                    params={"tweet_url": tw_obj.tweet_url, "tweet_id": tw_obj.tweet_id, "username": username},
                    timeout_seconds=30,
                )
                del_res = await c.browser.execute(del_req)
                if del_res.status in ("success", "deleted") or (del_res.action_result and del_res.action_result.status == "success"):
                    deleted_posts.append({
                        "tweet_id": tw_obj.tweet_id,
                        "tweet_url": tw_obj.tweet_url,
                        "text": tw_obj.text,
                        "reason": reason,
                        "metrics": {
                            "views": tw_obj.views,
                            "likes": tw_obj.likes,
                            "comments": tw_obj.comments,
                            "age_hours": tw_obj.age_hours,
                        },
                    })
                if len(deleted_posts) >= criteria.max_posts_to_delete:
                    break
    else:
        # Stream-scroll profile timeline and prune in-place via BrowserPort
        calculated_scrolls = max(60, min(500, int(criteria.max_posts_to_delete * 2.5)))
        calculated_timeout = max(300, min(1600, criteria.max_posts_to_delete * 10))
        prune_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.PRUNE_TIMELINE,
            params={
                "username": username,
                "criteria": criteria.model_dump(),
                "max_scrolls": calculated_scrolls,
            },
            timeout_seconds=calculated_timeout,
        )
        prune_res = await c.browser.execute(prune_req)
        raw_data: dict[str, Any] = {}
        if prune_res.scrape and prune_res.scrape.raw:
            raw_data = prune_res.scrape.raw
        elif prune_res.action_result and prune_res.action_result.raw:
            raw_data = prune_res.action_result.raw

        if raw_data.get("status") in ("failed", "rate_limited") and raw_data.get("error"):
            return {
                "status": "rate_limited" if "rate limit" in raw_data.get("error", "").lower() else "failed",
                "error": raw_data.get("error"),
                "dry_run": criteria.dry_run,
                "profile_id": str(profile_id),
                "username": username,
                "scanned_count": 0,
                "deleted_count": 0,
                "candidate_count": 0,
                "criteria": criteria.model_dump(),
                "deleted_posts": [],
                "candidate_posts": [],
                "skipped_summary": {},
                "evaluated_posts": [],
            }

        total_scanned = raw_data.get("scanned_count", 0)
        deleted_posts = raw_data.get("deleted_posts", [])
        candidate_posts = raw_data.get("candidate_posts", [])
        skipped_summary = raw_data.get("skipped_summary", {})
        evaluated_posts = raw_data.get("evaluated_posts", [])

    if criteria.dry_run:
        return {
            "status": "success",
            "dry_run": True,
            "profile_id": str(profile_id),
            "username": username,
            "scanned_count": total_scanned,
            "deleted_count": 0,
            "candidate_count": len(candidate_posts),
            "criteria": criteria.model_dump(),
            "deleted_posts": [],
            "candidate_posts": candidate_posts,
            "skipped_summary": skipped_summary,
            "evaluated_posts": evaluated_posts,
        }

    # Record Session in DB
    session = Session(
        profile_id=profile_id,
        started_at=datetime.datetime.utcnow(),
        ended_at=datetime.datetime.utcnow(),
        status=SessionStatus.COMPLETED,
        actions_planned=len(deleted_posts),
        actions_completed=len(deleted_posts),
        actions_failed=0,
    )
    db.add(session)
    await db.flush()

    for item in deleted_posts:
        act = Action(
            session_id=session.id,
            profile_id=profile_id,
            action_type=ActionType.DELETE,
            target_url=item.get("tweet_url"),
            content=item.get("text", "")[:280],
            status=ActionStatus.SUCCESS,
            result={
                "tweet_id": item.get("tweet_id"),
                "reason": item.get("reason"),
                "metrics": item.get("metrics"),
                "criteria": criteria.model_dump(),
            },
            executed_at=datetime.datetime.utcnow(),
        )
        db.add(act)

        # Update Content if tracked in DB
        tweet_id = item.get("tweet_id")
        if tweet_id:
            c_stmt = select(Content).where(Content.tweet_id == tweet_id)
            c_res = await db.execute(c_stmt)
            c_record = c_res.scalar_one_or_none()
            if c_record and isinstance(c_record, Content):
                c_record.status = ContentStatus.DELETED
                meta = c_record.ai_metadata or {}
                meta["pruned_at"] = datetime.datetime.utcnow().isoformat()
                meta["prune_reason"] = item.get("reason")
                c_record.ai_metadata = meta

    await db.commit()

    return {
        "status": "success",
        "dry_run": False,
        "profile_id": str(profile_id),
        "username": username,
        "scanned_count": total_scanned,
        "deleted_count": len(deleted_posts),
        "candidate_count": len(candidate_posts),
        "criteria": criteria.model_dump(),
        "deleted_posts": deleted_posts,
        "candidate_posts": candidate_posts,
        "skipped_summary": skipped_summary,
        "evaluated_posts": evaluated_posts,
    }
