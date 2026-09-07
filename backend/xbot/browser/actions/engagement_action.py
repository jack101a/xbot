from __future__ import annotations
import logging
import random
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_click,
    human_mouse_move,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

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
                await page.goto(tweet_url, wait_until="commit", timeout=20000)
                status_check = await check_target_tweet_status(page, timeout=15000)
                if not status_check["available"]:
                    logger.warning("Like target tweet unavailable: %s", status_check["reason"])
                    return False
                await sleep_think_time(1000, 2500)  # Simulate reading the tweet
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

            # Check if tweet is already liked on page
            unlike_btn_direct = await page.query_selector(SELECTORS["unlike_button"])
            if unlike_btn_direct and tweet_url:
                logger.info("Tweet already liked (detected unlike button).")
                return True

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            if not tweet_elements and tweet_url:
                # Direct like button fallback on page
                like_btn_direct = await page.query_selector(SELECTORS["like_button"])
                if like_btn_direct:
                    await human_click(page, like_btn_direct, 200, 600)
                    logger.info("Liked direct tweet element successfully.")
                    return True
                return False

            if target_idx >= len(tweet_elements):
                return False

            target_tweet = tweet_elements[target_idx]
            like_btn = await target_tweet.query_selector(SELECTORS["like_button"])

            if not like_btn:
                unlike_btn = await target_tweet.query_selector(SELECTORS["unlike_button"])
                if unlike_btn:
                    logger.info("Tweet already liked.")
                    return True
                # Fallback to page-level like button
                like_btn = await page.query_selector(SELECTORS["like_button"])
                if not like_btn:
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
                await page.goto(tweet_url, wait_until="commit", timeout=20000)
                status_check = await check_target_tweet_status(page, timeout=15000)
                if not status_check["available"]:
                    logger.warning("Retweet target tweet unavailable: %s", status_check["reason"])
                    return False
                await sleep_think_time(1000, 2500)
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

