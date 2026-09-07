"""
xbot.browser.actions.prune_action: Stream-scrolls profile timeline and prunes underperforming tweets in-place.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import re
from typing import Any
from playwright.async_api import Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.timing import human_click, sleep_with_jitter

logger = logging.getLogger(__name__)


def _parse_metric(txt: str | None) -> int:
    """
    Robust metric parser that extracts numeric counts from strings like:
    - '16 Views. View post analytics' -> 16
    - '1.2K Likes' -> 1200
    - '5 Replies. Reply' -> 5
    - 'Like' -> 0
    - '1,450 Reposts' -> 1450
    """
    if not txt:
        return 0
    clean = txt.strip()
    m = re.search(r"([\d,.]+\s*[KkMmBb]?)", clean)
    if not m:
        return 0
    token = m.group(1).upper().replace(",", "").replace(" ", "")
    try:
        if "K" in token:
            return int(float(token.replace("K", "")) * 1_000)
        if "M" in token:
            return int(float(token.replace("M", "")) * 1_000_000)
        if "B" in token:
            return int(float(token.replace("B", "")) * 1_000_000_000)
        return int(float(token))
    except Exception:
        return 0


class StreamAndPruneTimeline(BaseAction):
    """
    Stream-scrolls the profile timeline from top to bottom.
    Evaluates posts one by one and deletes matching underperforming tweets in-place.
    Supports dry-run preview mode and provides detailed skipped/evaluated diagnostics.
    """

    async def execute(
        self,
        page: Page,
        username: str,
        criteria: dict[str, Any] | None = None,
        max_scrolls: int = 40,
    ) -> dict[str, Any]:
        criteria = criteria or {}
        min_views = int(criteria.get("min_views", 200))
        min_likes = int(criteria.get("min_likes", 5))
        min_comments = int(criteria.get("min_comments", 2))
        min_age_hours = float(criteria.get("min_age_hours", 24))
        max_posts_to_delete = int(criteria.get("max_posts_to_delete", 10))
        match_mode = criteria.get("match_mode", "all")
        dry_run = bool(criteria.get("dry_run", False))

        clean_user = username.lstrip("@")
        url = f"https://x.com/{clean_user}"
        logger.info(
            "StreamAndPruneTimeline: Navigating to %s (dry_run=%s, grace=%sh, match=%s, max_del=%d)",
            url,
            dry_run,
            min_age_hours,
            match_mode,
            max_posts_to_delete,
        )

        is_rate_limited = False

        def handle_response(res):
            nonlocal is_rate_limited
            if res.status == 429 and ("UserOriginalsTimeline" in res.url or "UserTweets" in res.url or "graphql" in res.url):
                logger.warning("StreamAndPruneTimeline: HTTP 429 Rate limit detected from %s", res.url)
                is_rate_limited = True

        page.on("response", handle_response)

        seen_ids: set[str] = set()
        deleted_posts: list[dict[str, Any]] = []
        candidate_posts: list[dict[str, Any]] = []
        evaluated_posts: list[dict[str, Any]] = []
        skipped_summary: dict[str, int] = {
            "too_recent": 0,
            "pinned": 0,
            "reply": 0,
            "retweet": 0,
            "passed_metrics": 0,
        }
        scanned_count = 0
        last_scroll_height = 0
        no_new_content_count = 0

        try:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            except Exception as nav_err:
                logger.warning("StreamAndPruneTimeline: Navigation warning for %s: %s", url, nav_err)

            # Explicit wait for timeline tweet elements to render
            try:
                await page.wait_for_selector('article[data-testid="tweet"], article', timeout=15000)
            except Exception:
                logger.warning("StreamAndPruneTimeline: Timeout waiting for initial tweet articles on %s", url)

            await sleep_with_jitter(1500)

            # Check initial rate-limit or error state
            retry_btn = await page.query_selector('button:has-text("Retry"), [role="button"]:has-text("Retry")')
            page_html = await page.content()
            if is_rate_limited or (retry_btn and "Something went wrong" in page_html):
                existing = await page.query_selector_all('article[data-testid="tweet"], article')
                if not existing:
                    logger.warning("StreamAndPruneTimeline: X profile timeline is currently rate limited (HTTP 429).")
                    return {
                        "status": "failed",
                        "error": "X rate limited profile timeline queries (HTTP 429). Please allow 10-15 minutes cooldown.",
                        "dry_run": dry_run,
                        "scanned_count": 0,
                        "deleted_count": 0,
                        "candidate_count": 0,
                        "criteria": criteria,
                        "deleted_posts": [],
                        "candidate_posts": [],
                        "skipped_summary": skipped_summary,
                        "evaluated_posts": [],
                    }

            for scroll_i in range(max_scrolls):
                if is_rate_limited:
                    logger.warning("StreamAndPruneTimeline: Rate limit encountered during scrolling after %d deletions.", len(deleted_posts))
                    break
                if not dry_run and len(deleted_posts) >= max_posts_to_delete:
                    logger.info("Reached max deletions limit (%d). Stopping stream.", max_posts_to_delete)
                    break
                if dry_run and len(candidate_posts) >= max_posts_to_delete:
                    logger.info("Reached max candidates preview limit (%d). Stopping stream.", max_posts_to_delete)
                    break

                tweet_elements = await page.query_selector_all('article[data-testid="tweet"], article')
                new_tweets_in_batch = 0
                break_batch = False

                for tw in tweet_elements:
                    if break_batch:
                        break
                    if not dry_run and len(deleted_posts) >= max_posts_to_delete:
                        break
                    if dry_run and len(candidate_posts) >= max_posts_to_delete:
                        break

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

                    txt_el = await tw.query_selector('[data-testid="tweetText"]')
                    text = await txt_el.inner_text() if txt_el else ""

                    sc_el = await tw.query_selector('[data-testid="socialContext"]')
                    sc_text = (await sc_el.inner_text() if sc_el else "").lower()
                    is_pinned = "pinned" in sc_text
                    is_retweet = "reposted" in sc_text or "retweeted" in sc_text

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

                    reply_el = await tw.query_selector('[data-testid="reply"]')
                    retweet_el = await tw.query_selector('[data-testid="retweet"], [data-testid="unretweet"]')
                    like_el = await tw.query_selector('[data-testid="like"], [data-testid="unlike"]')
                    view_el = await tw.query_selector('a[href*="/analytics"], [data-testid="app-text-transition-container"]')

                    reply_raw = (await reply_el.get_attribute("aria-label") if reply_el else "") or ""
                    replies = _parse_metric(reply_raw)
                    if replies == 0 and reply_el:
                        replies = _parse_metric(await reply_el.inner_text())

                    retweet_raw = (await retweet_el.get_attribute("aria-label") if retweet_el else "") or ""
                    retweets = _parse_metric(retweet_raw)
                    if retweets == 0 and retweet_el:
                        retweets = _parse_metric(await retweet_el.inner_text())

                    like_raw = (await like_el.get_attribute("aria-label") if like_el else "") or ""
                    likes = _parse_metric(like_raw)
                    if likes == 0 and like_el:
                        likes = _parse_metric(await like_el.inner_text())

                    view_raw = (await view_el.get_attribute("aria-label") if view_el else "") or ""
                    views = _parse_metric(view_raw)
                    if views == 0 and view_el:
                        views = _parse_metric(await view_el.inner_text())

                    is_reply = False
                    user_name_el = await tw.query_selector('[data-testid="User-Name"]')
                    user_name_text = await user_name_el.inner_text() if user_name_el else ""
                    if "replying to" in user_name_text.lower() or "replying to" in text.lower():
                        is_reply = True

                    metrics_dict = {
                        "views": views,
                        "likes": likes,
                        "comments": replies,
                        "retweets": retweets,
                        "age_hours": round(age_hours, 1),
                    }

                    # Safe exemptions: Pinned, Retweets, Replies
                    if is_pinned:
                        skipped_summary["pinned"] += 1
                        evaluated_posts.append({
                            "tweet_id": tweet_id,
                            "tweet_url": tweet_url,
                            "text": text[:240],
                            "status": "pinned",
                            "reason": "Pinned tweet is protected",
                            "metrics": metrics_dict,
                        })
                        continue

                    if is_retweet:
                        skipped_summary["retweet"] += 1
                        evaluated_posts.append({
                            "tweet_id": tweet_id,
                            "tweet_url": tweet_url,
                            "text": text[:240],
                            "status": "retweet",
                            "reason": "Retweets are protected",
                            "metrics": metrics_dict,
                        })
                        continue

                    if is_reply:
                        skipped_summary["reply"] += 1
                        evaluated_posts.append({
                            "tweet_id": tweet_id,
                            "tweet_url": tweet_url,
                            "text": text[:240],
                            "status": "reply",
                            "reason": "Replies and thread comments are protected",
                            "metrics": metrics_dict,
                        })
                        continue

                    # Grace period evaluation
                    if min_age_hours > 0 and age_hours < min_age_hours:
                        skipped_summary["too_recent"] += 1
                        evaluated_posts.append({
                            "tweet_id": tweet_id,
                            "tweet_url": tweet_url,
                            "text": text[:240],
                            "status": "too_recent",
                            "reason": f"Within grace period ({age_hours:.1f}h < {min_age_hours}h)",
                            "metrics": metrics_dict,
                        })
                        continue

                    # Threshold criteria evaluation
                    failed_parts: list[str] = []
                    if min_views > 0:
                        views_failed = views < min_views
                        if views_failed:
                            failed_parts.append(f"views {views}<{min_views}")
                    else:
                        views_failed = True if match_mode == "all" else False

                    if min_likes > 0:
                        likes_failed = likes < min_likes
                        if likes_failed:
                            failed_parts.append(f"likes {likes}<{min_likes}")
                    else:
                        likes_failed = True if match_mode == "all" else False

                    if min_comments > 0:
                        comments_failed = replies < min_comments
                        if comments_failed:
                            failed_parts.append(f"replies {replies}<{min_comments}")
                    else:
                        comments_failed = True if match_mode == "all" else False

                    should_delete = (
                        (views_failed and likes_failed and comments_failed)
                        if match_mode == "all"
                        else (views_failed or likes_failed or comments_failed)
                    )

                    if not should_delete:
                        skipped_summary["passed_metrics"] += 1
                        evaluated_posts.append({
                            "tweet_id": tweet_id,
                            "tweet_url": tweet_url,
                            "text": text[:240],
                            "status": "passed_metrics",
                            "reason": "Met engagement criteria",
                            "metrics": metrics_dict,
                        })
                        continue

                    # Tweet qualifies for pruning
                    fail_reason = ", ".join(failed_parts) if failed_parts else "underperforming criteria"
                    item_entry = {
                        "tweet_id": tweet_id,
                        "tweet_url": tweet_url,
                        "text": text[:280],
                        "reason": f"Underperforming: {fail_reason}",
                        "metrics": metrics_dict,
                    }
                    candidate_posts.append(item_entry)

                    if dry_run:
                        evaluated_posts.append({**item_entry, "status": "candidate"})
                        continue

                    # Execute Deletion
                    deleted = False
                    try:
                        caret_btn = await tw.query_selector(
                            "[data-testid='caret'], button[aria-label='More'], button[aria-label='More actions']"
                        )
                        if caret_btn:
                            await caret_btn.scroll_into_view_if_needed()
                            await human_click(page, caret_btn)
                            await sleep_with_jitter(800)

                            del_menu_item = await page.wait_for_selector(
                                "[role='menuitem']:has-text('Delete'), [data-testid='Dropdown'] span:has-text('Delete')",
                                timeout=3500,
                            )
                            if del_menu_item:
                                await human_click(page, del_menu_item)
                                await sleep_with_jitter(800)

                                confirm_btn = await page.wait_for_selector(
                                    "[data-testid='confirmationSheetConfirm']",
                                    timeout=4500,
                                )
                                if confirm_btn:
                                    await human_click(page, confirm_btn)
                                    await sleep_with_jitter(1500)
                                    deleted = True
                                    logger.info("Successfully deleted tweet %s in-place", tweet_id)
                    except Exception as del_err:
                        logger.warning("In-place deletion failed for tweet %s: %s. Attempting fallback...", tweet_id, del_err)

                    # Fallback to isolated direct deletion if in-place was interrupted
                    if not deleted:
                        try:
                            from xbot.browser.actions.delete_action import DeleteTweet
                            fallback_act = DeleteTweet()
                            fallback_res = await fallback_act.execute(
                                page,
                                tweet_url=tweet_url,
                                tweet_id=tweet_id,
                                username=clean_user,
                            )
                            if fallback_res.get("deleted"):
                                deleted = True
                                logger.info("Successfully deleted tweet %s via DeleteTweet fallback", tweet_id)
                                # Navigate back to user timeline to resume stream
                                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                                await sleep_with_jitter(1500)
                                break_batch = True
                        except Exception as fb_err:
                            logger.error("Fallback deletion failed for tweet %s: %s", tweet_id, fb_err)

                    if deleted:
                        deleted_posts.append(item_entry)
                        evaluated_posts.append({**item_entry, "status": "deleted"})
                    else:
                        evaluated_posts.append({**item_entry, "status": "delete_failed", "reason": "Deletion attempt failed"})

                # Scroll down
                await page.evaluate("window.scrollBy(0, 900)")
                await asyncio.sleep(1.5)

                new_scroll_height = await page.evaluate("() => document.body.scrollHeight")
                if new_tweets_in_batch == 0 and new_scroll_height == last_scroll_height:
                    no_new_content_count += 1
                    await asyncio.sleep(2.0)
                    if no_new_content_count >= 5:
                        logger.info("Stream reached end of timeline or no new content after 5 scrolls.")
                        break
                else:
                    no_new_content_count = 0
                last_scroll_height = new_scroll_height
        except Exception as stream_err:
            logger.warning("Timeline pruning stream concluded: %s", stream_err)
        finally:
            try:
                page.remove_listener("response", handle_response)
            except Exception:
                pass

        return {
            "status": "success",
            "dry_run": dry_run,
            "scanned_count": scanned_count,
            "deleted_count": len(deleted_posts),
            "candidate_count": len(candidate_posts),
            "criteria": criteria,
            "deleted_posts": deleted_posts,
            "candidate_posts": candidate_posts,
            "skipped_summary": skipped_summary,
            "evaluated_posts": evaluated_posts,
        }
