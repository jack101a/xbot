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
    max_posts_to_delete: int = Field(default=10, ge=1, le=100, description="Maximum number of posts to delete per run")
    match_mode: Literal["all", "any"] = Field(
        default="all",
        description="'all' = strict (all criteria must fail); 'any' = aggressive (any criterion failure triggers delete)",
    )


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


async def stream_and_prune_timeline(
    profile_slug: str,
    username: str,
    criteria: PrunerFilterCriteria,
    max_scrolls: int = 40,
) -> tuple[int, list[dict[str, Any]]]:
    """
    Stream-scrolls the profile timeline from top to bottom.
    Evaluates posts one by one and deletes matching underperforming tweets in-place
    until criteria.max_posts_to_delete is satisfied or end of timeline is reached.
    """
    from xbot.browser.manager import BrowserManager

    mgr = BrowserManager(base_profile_dir=Path(settings.BASE_PROFILE_DIR))
    await mgr.start()
    ctx = await mgr.get_context(profile_slug)
    page = await ctx.new_page()

    seen_ids: set[str] = set()
    deleted_posts: list[dict[str, Any]] = []
    scanned_count = 0

    try:
        clean_user = username.lstrip("@")
        url = f"https://x.com/{clean_user}"
        logger.info("Streaming timeline for pruning: %s (target deletions: %d)", url, criteria.max_posts_to_delete)
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)

        no_new_content_count = 0
        last_scroll_height = await page.evaluate("() => document.body.scrollHeight")

        for scroll_step in range(max_scrolls):
            if len(deleted_posts) >= criteria.max_posts_to_delete:
                logger.info("Target deletion limit reached (%d/%d)", len(deleted_posts), criteria.max_posts_to_delete)
                break

            tweets = await page.query_selector_all('[data-testid="tweet"], article')
            new_tweets_in_batch = 0

            for tw in tweets:
                if len(deleted_posts) >= criteria.max_posts_to_delete:
                    break

                # Extract Tweet URL & ID
                link_el = await tw.query_selector('a[href*="/status/"]')
                href = await link_el.get_attribute("href") if link_el else ""
                tweet_url = f"https://x.com{href}" if href.startswith("/") else href
                tweet_id = ""
                if "/status/" in tweet_url:
                    m = re.search(r"/status/(\d+)", tweet_url)
                    if m:
                        tweet_id = m.group(1)

                if not tweet_id or tweet_id in seen_ids:
                    continue

                seen_ids.add(tweet_id)
                new_tweets_in_batch += 1
                scanned_count += 1

                # Extract Text
                txt_el = await tw.query_selector('[data-testid="tweetText"]')
                text = await txt_el.inner_text() if txt_el else ""

                # Context (Pinned / Retweet)
                sc_el = await tw.query_selector('[data-testid="socialContext"]')
                sc_text = await sc_el.inner_text() if sc_el else ""
                is_pinned = "pinned" in sc_text.lower()
                is_retweet = "reposted" in sc_text.lower() or "retweeted" in sc_text.lower()

                # Timestamp / Age
                time_el = await tw.query_selector("time")
                dt_str = await time_el.get_attribute("datetime") if time_el else ""
                age_hours = 48.0
                if dt_str:
                    try:
                        dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                        now = datetime.datetime.now(datetime.timezone.utc)
                        age_hours = (now - dt).total_seconds() / 3600.0
                    except Exception:
                        pass

                def _parse_metric(txt: str | None) -> int:
                    if not txt:
                        return 0
                    n = txt.split()[0].upper().replace(",", "")
                    if "K" in n:
                        return int(float(n.replace("K", "")) * 1000)
                    if "M" in n:
                        return int(float(n.replace("M", "")) * 1000000)
                    try:
                        return int(float(n))
                    except Exception:
                        return 0

                reply_el = await tw.query_selector('[data-testid="reply"]')
                retweet_el = await tw.query_selector('[data-testid="retweet"], [data-testid="unretweet"]')
                like_el = await tw.query_selector('[data-testid="like"], [data-testid="unlike"]')
                view_el = await tw.query_selector('a[href*="/analytics"]')

                replies = _parse_metric(await reply_el.get_attribute("aria-label") if reply_el else "")
                retweets = _parse_metric(await retweet_el.get_attribute("aria-label") if retweet_el else "")
                likes = _parse_metric(await like_el.get_attribute("aria-label") if like_el else "")
                views = _parse_metric(await view_el.get_attribute("aria-label") if view_el else "")

                is_reply = False
                user_name_el = await tw.query_selector('[data-testid="User-Name"]')
                user_name_text = await user_name_el.inner_text() if user_name_el else ""
                if "Replying to" in user_name_text or "Replying to" in text:
                    is_reply = True

                tw_obj = ScrapedProfileTweet(
                    tweet_id=tweet_id,
                    tweet_url=tweet_url,
                    text=text,
                    views=views,
                    likes=likes,
                    retweets=retweets,
                    comments=replies,
                    is_reply=is_reply,
                    is_retweet=is_retweet,
                    is_pinned=is_pinned,
                    age_hours=age_hours,
                )

                should_del, reason = evaluate_tweet_for_pruning(tw_obj, criteria)
                if should_del:
                    logger.info("Found prune candidate: %s (%s). Executing in-place deletion...", tweet_id, reason)
                    try:
                        caret_btn = await tw.query_selector(
                            "[data-testid='caret'], button[aria-label='More'], button[aria-label='More actions']"
                        )
                        if caret_btn:
                            await human_click(page, caret_btn)
                            await sleep_with_jitter(1000)

                            del_menu_item = await page.wait_for_selector(
                                "[role='menuitem']:has-text('Delete'), [data-testid='Dropdown'] span:has-text('Delete')",
                                timeout=4000,
                            )
                            if del_menu_item:
                                await human_click(page, del_menu_item)
                                await sleep_with_jitter(1000)

                                confirm_btn = await page.wait_for_selector(
                                    "[data-testid='confirmationSheetConfirm']",
                                    timeout=5000,
                                )
                                if confirm_btn:
                                    await human_click(page, confirm_btn)
                                    await sleep_with_jitter(2000)

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
                                    logger.info("Successfully deleted tweet %s in-place (%d/%d)", tweet_id, len(deleted_posts), criteria.max_posts_to_delete)
                    except Exception as del_err:
                        logger.error("Failed to delete tweet %s in-place: %s", tweet_id, del_err)

            # Scroll down to stream more tweets
            await page.evaluate("window.scrollBy(0, 900)")
            await asyncio.sleep(1.5)

            new_scroll_height = await page.evaluate("() => document.body.scrollHeight")
            if new_tweets_in_batch == 0 and new_scroll_height == last_scroll_height:
                no_new_content_count += 1
                if no_new_content_count >= 3:
                    logger.info("Reached end of timeline.")
                    break
            else:
                no_new_content_count = 0
            last_scroll_height = new_scroll_height

    except Exception as e:
        logger.error("Error during streaming timeline prune: %s", e, exc_info=True)
    finally:
        await ctx.close()
        await mgr.stop()

    return scanned_count, deleted_posts


async def run_post_pruner_for_profile(
    profile_id: uuid.UUID,
    criteria: PrunerFilterCriteria,
    db: AsyncSession,
    r: redis.Redis | None = None,
    custom_scraped_tweets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Executes the streaming Post Pruner for a profile.
    1. Scrolls the profile timeline streamingly, evaluating and deleting in-place.
    2. Continues until criteria.max_posts_to_delete is satisfied or timeline ends.
    3. Records Session, Action & Content updates in the database.
    """
    if r is None:
        r = get_redis_client()

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
        # Stream-scroll profile timeline and prune in-place
        total_scanned, deleted_posts = await stream_and_prune_timeline(
            profile_slug=profile_slug,
            username=username,
            criteria=criteria,
            max_scrolls=50,
        )

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
        "profile_id": str(profile_id),
        "username": username,
        "scanned_count": total_scanned,
        "deleted_count": len(deleted_posts),
        "criteria": criteria.model_dump(),
        "deleted_posts": deleted_posts,
    }
