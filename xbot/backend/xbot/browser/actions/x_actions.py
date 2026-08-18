"""
X (Twitter) browser action implementations.

Every action in this module is designed to behave like a real human:
- Mouse movement via Bezier curves (timing.py)
- Hover before click (timing.py)
- Inertia-based scrolling (timing.py)
- Variable think-time pauses between interactions
- Post-action cool-down browsing after engagement actions
- Navigation randomness between actions to avoid linear fingerprint
"""
from __future__ import annotations

import logging
import random
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.actions.poll_action import CreatePoll
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.actions.sync_profile_action import SyncProfileFromX
from xbot.browser.timing import (
    human_click,
    human_click_selector,
    human_mouse_move,
    human_scroll,
    human_type,
    sleep_micro,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _navigate_home_if_needed(page: Page) -> None:
    """Navigate to the X home feed if not already there."""
    current = page.url
    if "x.com/home" not in current and "twitter.com/home" not in current:
        await page.goto("https://x.com/home")
        await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
        await sleep_with_jitter(2000)


async def _random_tab_detour(page: Page) -> None:
    """
    30% chance to detour to Notifications or own profile and back —
    simulating how real users casually check other tabs between actions.
    """
    import os
    import sys
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return
    if random.random() > 0.3:
        return
    detour_urls = [
        "https://x.com/notifications",
        "https://x.com/i/lists",
    ]
    detour = random.choice(detour_urls)
    logger.debug("Taking random tab detour to %s", detour)
    await page.goto(detour)
    await sleep_think_time(2000, 6000)  # Browse briefly
    await page.goto("https://x.com/home")
    await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
    await sleep_with_jitter(1500)


async def _post_action_cooldown_browse(page: Page, scrolls: int = 2) -> None:
    """
    After an engagement action (like, reply, post), humans typically
    scroll for a moment before doing the next thing.
    """
    for _ in range(scrolls):
        px = random.randint(200, 500)
        await human_scroll(page, px, "down")
        await sleep_think_time(800, 2500)
        # Occasionally back-scroll
        if random.random() < 0.3:
            await human_scroll(page, random.randint(80, 200), "up")
            await sleep_with_jitter(800)


def _extract_tweet_id_from_url(url: str) -> str | None:
    """Extract the numeric tweet ID from a URL like https://x.com/user/status/12345."""
    try:
        parts = urlparse(url).path.strip("/").split("/")
        if "status" in parts:
            idx = parts.index("status")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

class BrowseFeed(BaseAction):
    """
    Browses the X home feed by scrolling incrementally with inertia,
    mimicking natural reading pauses and occasional back-scrolls.
    """

    async def execute(self, page: Page, max_scrolls: int = 5) -> list[dict[str, Any]]:
        try:
            logger.info("Starting feed browsing session.")
            tweets: list[dict[str, Any]] = []

            # Random initial idle — as if just opening the app
            await sleep_think_time(500, 2000)

            for _ in range(max_scrolls):
                # Inertia-based scroll (300–700 px)
                scroll_px = random.randint(300, 700)
                await human_scroll(page, scroll_px, "down")
                await sleep_think_time(1500, 4000)  # Read pause

                # 20% chance of a back-scroll (scanning up after reading)
                if random.random() < 0.2:
                    back_px = random.randint(100, 250)
                    await human_scroll(page, back_px, "up")
                    await sleep_with_jitter(1000)

                # 10% chance to hover over a random tweet as if reading more carefully
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                if tweet_elements and random.random() < 0.1:
                    hover_target = random.choice(tweet_elements[:5])
                    box = await hover_target.bounding_box()
                    if box:
                        await human_mouse_move(
                            page,
                            box["x"] + box["width"] * 0.4,
                            box["y"] + box["height"] * 0.4,
                        )
                        await sleep_think_time(600, 1800)

                # Extract visible tweets
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                for el in tweet_elements:
                    text_el = await el.query_selector(SELECTORS["tweet_text"])
                    if text_el:
                        text = await text_el.inner_text()
                        # Also try to extract author and tweet URL
                        tweet_data: dict[str, Any] = {"text": text}
                        try:
                            link_el = await el.query_selector("a[href*='/status/']")
                            if link_el:
                                href = await link_el.get_attribute("href")
                                if href:
                                    tweet_data["url"] = f"https://x.com{href}" if href.startswith("/") else href
                                    tweet_data["tweet_id"] = _extract_tweet_id_from_url(tweet_data["url"])
                        except Exception:
                            pass
                        if tweet_data not in tweets:
                            tweets.append(tweet_data)

            logger.info("Browsed %d scrolls, gathered %d tweets", max_scrolls, len(tweets))
            return tweets
        except Exception as e:
            await self.capture_failure(page, "browse_feed")
            logger.error("Failed browsing feed: %s", e)
            return []


class ComposePost(BaseAction):
    """Composes and publishes a new post (tweet)."""

    async def execute(self, page: Page, text: str) -> bool:
        try:
            logger.info("Composing new post: %s...", text[:40])

            # Navigate home if needed
            await _navigate_home_if_needed(page)

            # Random detour before posting (realistic context switch)
            await _random_tab_detour(page)

            # Scroll slightly and pause as if deciding to post
            await human_scroll(page, random.randint(100, 300), "down")
            await sleep_think_time(1500, 4000)

            # Click compose button using human-like click
            await human_click_selector(page, SELECTORS["nav_post_button"], 400, 1000)

            # Wait for textarea
            await page.wait_for_selector(SELECTORS["tweet_textarea"], timeout=8000)
            await sleep_think_time(800, 2000)

            # Type text like a human
            await human_type(page, SELECTORS["tweet_textarea"], text)
            await sleep_think_time(1000, 2500)  # Review what was typed

            # Occasionally move mouse away and back (as if re-reading before posting)
            if random.random() < 0.4:
                await human_mouse_move(page, random.uniform(200, 600), random.uniform(100, 400))
                await sleep_think_time(500, 1500)

            # Submit post
            await human_click_selector(page, SELECTORS["tweet_submit_button"], 300, 700)
            await sleep_with_jitter(3000)

            # Post-action cool-down browse (check feed after posting)
            await _post_action_cooldown_browse(page, scrolls=random.randint(1, 3))

            logger.info("Post published successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "compose_post")
            logger.error("Failed to compose post: %s", e)
            return False


class LikeTweet(BaseAction):
    """
    Likes a specific tweet.
    Prefers a provided tweet URL. Falls back to a randomly selected
    visible tweet (NOT always index 0) if no URL is given.
    """

    async def execute(
        self,
        page: Page,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
    ) -> bool:
        try:
            # Navigate to specific tweet URL if provided
            if tweet_url:
                logger.info("Navigating to tweet URL to like: %s", tweet_url)
                await page.goto(tweet_url)
                await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
                await sleep_think_time(1500, 3500)  # Simulate reading the tweet
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                target_idx = 0
            else:
                await _navigate_home_if_needed(page)
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                if not tweet_elements:
                    return False
                # Pick a random tweet from visible ones (not always first)
                if tweet_index is not None:
                    target_idx = min(tweet_index, len(tweet_elements) - 1)
                else:
                    # Weighted random: prefer tweets 1–5 (more visible), not always 0
                    visible_count = min(len(tweet_elements), 8)
                    weights = [max(1, 8 - i) for i in range(visible_count)]
                    target_idx = random.choices(range(visible_count), weights=weights)[0]

                logger.info("Liking tweet at index %d (of %d visible)", target_idx, len(tweet_elements))

                # Scroll and pause as if reading that tweet first
                if target_idx > 0:
                    tweet_el = tweet_elements[target_idx]
                    await human_scroll_to_tweet(page, tweet_el)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            if target_idx >= len(tweet_elements):
                return False

            target_tweet = tweet_elements[target_idx]
            like_btn = await target_tweet.query_selector(SELECTORS["like_button"])

            if not like_btn:
                unlike_btn = await target_tweet.query_selector(SELECTORS["unlike_button"])
                if unlike_btn:
                    logger.info("Tweet already liked.")
                    return True
                return False

            # Hover over tweet first, then find and click like
            box = await target_tweet.bounding_box()
            if box:
                await human_mouse_move(page, box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.5)
                await sleep_think_time(600, 2000)  # Read tweet

            await human_click(page, like_btn, 200, 700)
            await sleep_with_jitter(1000)

            await _post_action_cooldown_browse(page, scrolls=1)

            logger.info("Liked tweet successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "like_tweet")
            logger.error("Failed to like tweet: %s", e)
            return False


async def human_scroll_to_tweet(page: Page, tweet_el: Any) -> None:
    """Scroll a tweet into view and add a read pause."""
    await tweet_el.scroll_into_view_if_needed()
    await sleep_think_time(800, 2500)


class ReplyToTweet(BaseAction):
    """
    Replies to a tweet. Uses tweet_url when available (from AI planner).
    Falls back to a randomly chosen visible tweet (not always index 0).
    """

    async def execute(
        self,
        page: Page,
        reply_text: str,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
    ) -> bool:
        try:
            if tweet_url:
                logger.info("Navigating to tweet URL to reply: %s", tweet_url)
                await page.goto(tweet_url)
                await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
                await sleep_think_time(2000, 5000)  # Read the tweet thread
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                target_idx = 0
            else:
                await _navigate_home_if_needed(page)
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                if not tweet_elements:
                    return False
                if tweet_index is not None:
                    target_idx = min(tweet_index, len(tweet_elements) - 1)
                else:
                    # Pick a random tweet from the first 6 visible
                    visible_count = min(len(tweet_elements), 6)
                    target_idx = random.randint(0, visible_count - 1)

            logger.info("Replying to tweet at index %d", target_idx)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            if target_idx >= len(tweet_elements):
                return False

            target_tweet = tweet_elements[target_idx]

            # Scroll to tweet and "read" it
            await human_scroll_to_tweet(page, target_tweet)

            reply_btn = await target_tweet.query_selector(SELECTORS["reply_button"])
            if not reply_btn:
                return False

            # Click reply button with human movement
            await human_click(page, reply_btn, 300, 800)

            # Wait for compose modal
            await page.wait_for_selector(SELECTORS["tweet_textarea"], timeout=8000)
            await sleep_think_time(1200, 3000)  # Formulate reply

            # Type reply
            await human_type(page, SELECTORS["tweet_textarea"], reply_text)
            await sleep_think_time(800, 2000)  # Review reply

            submit_sel = SELECTORS["tweet_submit_button"]
            if await page.query_selector(SELECTORS["inline_tweet_submit_button"]):
                submit_sel = SELECTORS["inline_tweet_submit_button"]
            await human_click_selector(page, submit_sel, 300, 700)
            await sleep_with_jitter(2500)

            await _post_action_cooldown_browse(page, scrolls=random.randint(1, 2))

            logger.info("Reply submitted successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "reply_tweet")
            logger.error("Failed to reply to tweet: %s", e)
            return False


class Retweet(BaseAction):
    """Retweets a tweet using URL or a randomly chosen visible tweet."""

    async def execute(
        self,
        page: Page,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
    ) -> bool:
        try:
            if tweet_url:
                await page.goto(tweet_url)
                await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
                await sleep_think_time(1500, 3500)
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                target_idx = 0
            else:
                await _navigate_home_if_needed(page)
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                if not tweet_elements:
                    return False
                visible_count = min(len(tweet_elements), 6)
                target_idx = tweet_index if tweet_index is not None else random.randint(0, visible_count - 1)

            logger.info("Retweeting tweet at index %d", target_idx)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            if target_idx >= len(tweet_elements):
                return False

            target_tweet = tweet_elements[target_idx]
            await human_scroll_to_tweet(page, target_tweet)

            rt_btn = await target_tweet.query_selector(SELECTORS["retweet_button"])
            if not rt_btn:
                return False

            await human_click(page, rt_btn, 300, 800)

            # Wait for confirmation dropdown
            confirm = await page.wait_for_selector(SELECTORS["retweet_confirm"], timeout=5000)
            if confirm:
                await sleep_think_time(400, 1200)
                await human_click(page, confirm, 200, 600)

            await sleep_with_jitter(1500)
            await _post_action_cooldown_browse(page, scrolls=1)
            logger.info("Retweet completed successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "retweet")
            logger.error("Failed to retweet: %s", e)
            return False


class FollowUser(BaseAction):
    """Follows a user by navigating to their profile."""

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            logger.info("Navigating to user profile to follow: %s", clean)
            await page.goto(f"https://x.com/{clean}")
            await page.wait_for_selector(
                SELECTORS.get("profile_avatar", "[data-testid*='UserAvatar']"), timeout=10000
            )

            # Human: scan profile for a moment
            await sleep_think_time(2000, 5000)
            await human_scroll(page, random.randint(100, 300), "down")
            await sleep_think_time(1000, 2500)
            await human_scroll(page, random.randint(100, 200), "up")
            await sleep_think_time(800, 2000)

            follow_btn = await page.query_selector(SELECTORS["profile_follow_button"])
            if not follow_btn:
                logger.warning("Could not locate follow button for: %s", username)
                return False

            btn_text = await follow_btn.inner_text()
            if "Following" in btn_text or "Unfollow" in btn_text:
                logger.info("Already following user: %s", username)
                return True

            await human_click(page, follow_btn, 500, 1500)
            await sleep_with_jitter(2000)
            logger.info("Followed user %s successfully.", username)
            return True
        except Exception as e:
            await self.capture_failure(page, f"follow_{username}")
            logger.error("Failed to follow user %s: %s", username, e)
            return False


class UnfollowUser(BaseAction):
    """Unfollows a user."""

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            logger.info("Navigating to profile to unfollow: %s", clean)
            await page.goto(f"https://x.com/{clean}")
            await page.wait_for_selector(
                SELECTORS.get("profile_avatar", "[data-testid*='UserAvatar']"), timeout=10000
            )
            await sleep_think_time(1500, 4000)

            unfollow_btn = await page.query_selector("[data-testid$='-unfollow']")
            if not unfollow_btn:
                logger.warning("Could not locate unfollow button for: %s (might not be following)", username)
                return False

            await human_click(page, unfollow_btn, 600, 1800)

            confirm_btn = await page.wait_for_selector("[data-testid='confirmationSheetConfirm']", timeout=5000)
            if confirm_btn:
                await sleep_with_jitter(1200)
                await human_click(page, confirm_btn, 300, 800)

            await sleep_with_jitter(2000)
            logger.info("Unfollowed user %s successfully.", username)
            return True
        except Exception as e:
            await self.capture_failure(page, f"unfollow_{username}")
            logger.error("Failed to unfollow user %s: %s", username, e)
            return False


class SearchQuery(BaseAction):
    """Performs a search query on X and browses results."""

    async def execute(self, page: Page, query: str) -> list[dict[str, Any]]:
        try:
            logger.info("Executing search query: %s", query)
            from urllib.parse import quote_plus
            search_url = f"https://x.com/search?q={quote_plus(query)}&f=live"
            await page.goto(search_url)
            await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
            await sleep_with_jitter(3000)

            # Browse search results like a human
            browser = BrowseFeed(str(self.screenshot_dir))
            results = await browser.execute(page, max_scrolls=3)
            logger.info("Gathered %d search results.", len(results))
            return results
        except Exception as e:
            await self.capture_failure(page, "search")
            logger.error("Failed to perform search: %s", e)
            return []


class ScrapeProfileMetrics(BaseAction):
    """Scrapes follower, following, and post counts from a profile."""

    async def execute(self, page: Page, username: str) -> dict[str, int]:
        try:
            logger.info("Scraping metrics for %s", username)
            clean = username.lstrip("@")
            await page.goto(f"https://x.com/{clean}")
            await page.wait_for_selector(
                SELECTORS.get("profile_avatar", "[data-testid*='UserAvatar']"), timeout=10000
            )
            await sleep_with_jitter(2000)

            metrics = {"followers": 0, "following": 0, "posts": 0}

            following_el = await page.query_selector(f"a[href='/{clean}/following'] span")
            if following_el:
                metrics["following"] = self._parse_count(await following_el.inner_text())

            followers_el = await page.query_selector(
                f"a[href='/{clean}/verified_followers'] span, a[href='/{clean}/followers'] span"
            )
            if followers_el:
                metrics["followers"] = self._parse_count(await followers_el.inner_text())

            # Also scrape avatar_url if present
            avatar_el = await page.query_selector("img[src*='pbs.twimg.com/profile_images']")
            if avatar_el:
                metrics["avatar_url"] = await avatar_el.get_attribute("src") or ""  # type: ignore[assignment]

            logger.info("Scraped metrics: %s", metrics)
            return metrics
        except Exception as e:
            await self.capture_failure(page, f"scrape_metrics_{username}")
            logger.error("Failed to scrape metrics: %s", e)
            return {"followers": 0, "following": 0, "posts": 0}

    def _parse_count(self, text: str) -> int:
        text = text.replace(",", "").replace(" ", "").upper()
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        if "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        try:
            return int(text)
        except Exception:
            return 0


class ScrapeTrends(BaseAction):
    """Scrapes trending topics from the X explore page."""

    async def execute(self, page: Page) -> list[dict[str, str]]:
        try:
            logger.info("Scraping X Trends")
            await page.goto("https://x.com/explore/tabs/trending")
            await page.wait_for_selector("[data-testid='trend']", timeout=10000)
            await sleep_with_jitter(2000)

            # Human-like scroll through trending section
            await human_scroll(page, random.randint(200, 400), "down")
            await sleep_think_time(1000, 2500)

            trends = []
            trend_elements = await page.query_selector_all("[data-testid='trend']")
            for el in trend_elements[:10]:
                text = await el.inner_text()
                lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
                if len(lines) >= 2:
                    trends.append({
                        "topic": lines[1] if len(lines) > 1 else lines[0],
                        "context": lines[0],
                        "volume": lines[2] if len(lines) > 2 else "",
                    })

            logger.info("Scraped %d trends.", len(trends))
            return trends
        except Exception as e:
            await self.capture_failure(page, "scrape_trends")
            logger.error("Failed to scrape trends: %s", e)
            return []


class ScrapeProfileTweets(BaseAction):
    """Scrapes recent tweets of a profile to calculate engagement metrics."""

    async def execute(self, page: Page, username: str, limit: int = 5) -> dict:
        try:
            logger.info("Scraping recent tweets for %s", username)
            clean = username.lstrip("@")
            await page.goto(f"https://x.com/{clean}")
            await page.wait_for_selector(
                SELECTORS.get("tweet", "article[data-testid='tweet']"), timeout=10000
            )
            await sleep_with_jitter(2000)

            followers = 0
            following = 0
            try:
                followers_el = await page.query_selector(
                    "a[href$='/followers'], a[href$='/verified_followers']"
                )
                if followers_el:
                    txt = await followers_el.inner_text()
                    followers = self._parse_abbrev(txt.split()[0])

                following_el = await page.query_selector("a[href$='/following']")
                if following_el:
                    txt = await following_el.inner_text()
                    following = self._parse_abbrev(txt.split()[0])
            except Exception as e:
                logger.error("Failed to parse follower/following counts: %s", e)

            tweets_data = []
            for _ in range(3):
                tweet_elements = await page.query_selector_all(
                    SELECTORS.get("tweet", "article[data-testid='tweet']")
                )
                for el in tweet_elements:
                    if len(tweets_data) >= limit:
                        break

                    text_el = await el.query_selector("[data-testid='tweetText']")
                    text = await text_el.inner_text() if text_el else ""
                    if not text or any(t.get("text") == text for t in tweets_data):
                        continue

                    def _pm(label: str) -> int:
                        if not label:
                            return 0
                        n = label.split()[0].upper().replace(",", "")
                        if "K" in n:
                            return int(float(n.replace("K", "")) * 1000)
                        if "M" in n:
                            return int(float(n.replace("M", "")) * 1000000)
                        try:
                            return int(float(n))
                        except Exception:
                            return 0

                    reply_el = await el.query_selector("[data-testid='reply']")
                    retweet_el = await el.query_selector("[data-testid='retweet']")
                    like_el = await el.query_selector("[data-testid='like']")
                    view_el = await el.query_selector("a[href*='/analytics']")

                    replies = _pm(await reply_el.get_attribute("aria-label") if reply_el else "")
                    retweets = _pm(await retweet_el.get_attribute("aria-label") if retweet_el else "")
                    likes = _pm(await like_el.get_attribute("aria-label") if like_el else "")
                    views = _pm(await view_el.get_attribute("aria-label") if view_el else "")

                    tweets_data.append({
                        "text": text,
                        "replies": replies,
                        "retweets": retweets,
                        "likes": likes,
                        "views": views,
                        "engagement_score": replies + retweets + likes,
                    })

                if len(tweets_data) >= limit:
                    break
                await human_scroll(page, random.randint(300, 600), "down")
                await sleep_with_jitter(1500)

            logger.info("Scraped %d tweets for %s", len(tweets_data), username)
            return {"tweets": tweets_data, "followers": followers, "following": following}
        except Exception as e:
            await self.capture_failure(page, f"scrape_tweets_{username}")
            logger.error("Failed to scrape profile tweets: %s", e)
            return {"tweets": [], "followers": 0, "following": 0}

    def _parse_abbrev(self, text: str) -> int:
        t = text.strip().upper().replace(",", "")
        if "K" in t:
            return int(float(t.replace("K", "")) * 1000)
        if "M" in t:
            return int(float(t.replace("M", "")) * 1000000)
        try:
            return int(float(t))
        except Exception:
            return 0


class UnfollowNonFollowers(BaseAction):
    """
    Finds users the profile follows who do not follow back,
    and unfollows them up to a safe limit.
    """

    async def execute(self, page: Page, limit: int = 10) -> bool:
        try:
            # 1. Identify logged-in username
            my_username = ""
            profile_link = await page.query_selector("a[data-testid='AppTabBar_Profile_Link']")
            if profile_link:
                href = await profile_link.get_attribute("href")
                if href:
                    my_username = href.strip("/")
            
            if not my_username:
                logger.warning("Could not identify logged-in username from sidebar. Trying home navigation...")
                await page.goto("https://x.com/home")
                await page.wait_for_selector("a[data-testid='AppTabBar_Profile_Link']", timeout=15000)
                profile_link = await page.query_selector("a[data-testid='AppTabBar_Profile_Link']")
                if profile_link:
                    href = await profile_link.get_attribute("href")
                    if href:
                        my_username = href.strip("/")
            
            if not my_username:
                logger.error("Failed to determine logged-in username.")
                return False

            logger.info("Unfollowing non-followers for @%s (limit: %d)", my_username, limit)
            await page.goto(f"https://x.com/{my_username}/following")
            await page.wait_for_selector("[data-testid='UserCell']", timeout=15000)
            await sleep_with_jitter(2000)

            unfollowed_count = 0
            seen_handles = set()

            # Scroll and process loop
            for scroll_attempt in range(5):
                if unfollowed_count >= limit:
                    break

                cells = await page.query_selector_all("[data-testid='UserCell']")
                logger.debug("Found %d user cells on page.", len(cells))
                
                for cell in cells:
                    if unfollowed_count >= limit:
                        break

                    # Get username handle
                    links = await cell.query_selector_all("a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if h and "/" not in h and h not in ["home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings"]:
                                handle = h
                                break
                    
                    if not handle or handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    # Check if they follow us back ("Follows you" badge)
                    follows_back = await cell.query_selector("[data-testid='userFollowIndicator']")
                    if follows_back:
                        logger.debug("@%s follows us back, skipping.", handle)
                        continue

                    # Non-follower! Locate the unfollow button
                    unfollow_btn = await cell.query_selector("[data-testid$='-unfollow']")
                    if unfollow_btn:
                        logger.info("Unfollowing non-follower: @%s", handle)
                        await human_click(page, unfollow_btn, 400, 1000)
                        
                        confirm_btn = await page.wait_for_selector("[data-testid='confirmationSheetConfirm']", timeout=5000)
                        if confirm_btn:
                            await sleep_with_jitter(1000)
                            await human_click(page, confirm_btn, 300, 800)
                        
                        unfollowed_count += 1
                        await sleep_think_time(3000, 6000)  # Human-like delay after clicking
                    
                # Scroll down to load more cells
                await human_scroll(page, random.randint(400, 700), "down")
                await sleep_with_jitter(2000)

            logger.info("Successfully unfollowed %d non-followers.", unfollowed_count)
            return True
        except Exception as e:
            await self.capture_failure(page, "unfollow_non_followers")
            logger.error("Error executing UnfollowNonFollowers: %s", e)
            return False


class FollowEngagers(BaseAction):
    """
    Navigates to a tweet URL, opens the likes/engagers list,
    and follows users up to a safe limit.
    """

    async def execute(self, page: Page, tweet_url: str, limit: int = 5) -> bool:
        try:
            if not tweet_url:
                logger.error("No tweet URL provided to FollowEngagers.")
                return False

            # Construct likes URL
            likes_url = tweet_url
            if "/likes" not in tweet_url:
                likes_url = f"{tweet_url.rstrip('/')}/likes"

            logger.info("Navigating to engagers list at %s (limit: %d)", likes_url, limit)
            await page.goto(likes_url)
            
            try:
                await page.wait_for_selector("[data-testid='UserCell']", timeout=12000)
            except Exception:
                logger.warning("No UserCell loaded for likes list. Tweet might have 0 likes or be private.")
                return False

            await sleep_with_jitter(2000)

            followed_count = 0
            seen_handles = set()

            # Scroll and process loop
            for scroll_attempt in range(5):
                if followed_count >= limit:
                    break

                cells = await page.query_selector_all("[data-testid='UserCell']")
                logger.debug("Found %d user cells on page.", len(cells))
                
                for cell in cells:
                    if followed_count >= limit:
                        break

                    # Get username handle
                    links = await cell.query_selector_all("a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if h and "/" not in h and h not in ["home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings"]:
                                handle = h
                                break
                    
                    if not handle or handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    # Look for follow button (ends with "-follow")
                    follow_btn = await cell.query_selector("[data-testid$='-follow']")
                    if follow_btn:
                        btn_text = await follow_btn.inner_text()
                        if "Following" in btn_text or "Pending" in btn_text:
                            continue

                        logger.info("Following engager user: @%s", handle)
                        await human_click(page, follow_btn, 400, 1000)
                        followed_count += 1
                        await sleep_think_time(3000, 6000)  # Human-like delay after following
                    
                # Scroll down slightly to load more cells
                await human_scroll(page, random.randint(300, 500), "down")
                await sleep_with_jitter(2000)

            logger.info("Successfully followed %d engagers.", followed_count)
            return True
        except Exception as e:
            await self.capture_failure(page, "follow_engagers")
            logger.error("Error executing FollowEngagers: %s", e)
            return False


class ScrapeFollowList(BaseAction):
    """
    Scrapes the list of followers or following handles for a given user.
    """

    async def execute(self, page: Page, username: str, list_type: str = "followers", limit: int = 100) -> list[str]:
        try:
            clean = username.lstrip("@")
            # Navigate to the appropriate tab
            url = f"https://x.com/{clean}/{list_type}"
            logger.info("Scraping %s list for @%s (limit: %d)", list_type, clean, limit)
            await page.goto(url)
            
            try:
                await page.wait_for_selector("[data-testid='UserCell']", timeout=15000)
            except Exception:
                logger.warning("No UserCell selector loaded on follow list page.")
                return []

            await sleep_with_jitter(2000)

            handles = []
            seen_handles = set()
            scroll_count = 0
            max_scrolls = 20  # Safeguard to prevent infinite loops

            while len(handles) < limit and scroll_count < max_scrolls:
                cells = await page.query_selector_all("[data-testid='UserCell']")
                new_found = False
                
                for cell in cells:
                    links = await cell.query_selector_all("a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if h and "/" not in h and h not in ["home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings"]:
                                handle = h
                                break
                    
                    if handle and handle not in seen_handles:
                        seen_handles.add(handle)
                        handles.append(handle)
                        new_found = True
                        if len(handles) >= limit:
                            break
                
                if len(handles) >= limit:
                    break

                # Scroll down to load more
                scroll_count += 1
                await human_scroll(page, random.randint(400, 700), "down")
                await sleep_with_jitter(1500)
                
            logger.info("Scraped %d handles from the %s list of @%s", len(handles), list_type, clean)
            return handles
        except Exception as e:
            await self.capture_failure(page, f"scrape_{list_type}_{username}")
            logger.error("Error scraping %s for %s: %s", list_type, username, e)
            return []


