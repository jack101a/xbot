from __future__ import annotations
import logging
import random
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_click,
    human_type,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.post_utils import (_attach_gif_if_requested, _attach_media_files, smart_truncate_tweet_text)
from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)
from xbot.browser.actions.tweet_context_scraper import (scrape_target_tweet_context)

class ReplyToTweet(BaseAction):

    async def scrape_target_tweet_context(
        self, page: Page, target_idx: int = 0, tweet_url: str | None = None
    ) -> dict[str, Any]:
        """
        Scrapes full live text, author, metrics, media URLs/alts, and top visible comment replies
        from the current tweet thread.
        """
        return await scrape_target_tweet_context(page, target_idx=target_idx, tweet_url=tweet_url)
    """
    Replies to a tweet. Uses tweet_url when available (from AI planner).
    Falls back to a randomly chosen visible tweet (not always index 0).
    Supports optional reaction GIF attachment.
    """

    async def execute(
        self,
        page: Page,
        reply_text: str,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
        gif_query: str | None = None,
        media_paths: list[str] | None = None,
    ) -> bool:
        try:
            if tweet_url:
                if page.url != tweet_url and not page.url.startswith(tweet_url.split("?")[0]):
                    logger.info("Navigating to tweet URL to reply: %s", tweet_url)
                    await page.goto(tweet_url, wait_until="commit", timeout=20000)
                    status_check = await check_target_tweet_status(page, timeout=15000)
                    if not status_check["available"]:
                        logger.warning("Reply target tweet unavailable: %s", status_check["reason"])
                        return False
                    await sleep_think_time(1000, 2500)  # Read the tweet thread
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

            logger.info("Replying to tweet at index %d (gif=%s, media=%s)", target_idx, gif_query, media_paths)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            target_tweet = tweet_elements[target_idx] if tweet_elements and target_idx < len(tweet_elements) else None

            # Scroll to tweet and "read" it
            if target_tweet:
                await human_scroll_to_tweet(page, target_tweet)

            reply_btn = await target_tweet.query_selector(SELECTORS["reply_button"]) if target_tweet else None
            if not reply_btn:
                reply_btn = await page.query_selector(SELECTORS["reply_button"])
            if not reply_btn:
                logger.warning("Could not find reply button on tweet.")
                return False

            # Click reply button with human movement
            await human_click(page, reply_btn, 300, 800)

            # Wait for compose modal
            textarea_sel = SELECTORS["tweet_textarea"]
            await page.wait_for_selector(textarea_sel, timeout=12000)
            await sleep_think_time(1000, 2500)  # Formulate reply

            # Ensure reply_text is cleanly <= 260 chars with smart boundary truncation
            if reply_text:
                reply_text = smart_truncate_tweet_text(reply_text, 260)
                # Type reply
                await human_type(page, textarea_sel, reply_text)
                await sleep_think_time(800, 2000)  # Review reply

            # Attach media files if provided
            if media_paths:
                await _attach_media_files(page, media_paths)
                await sleep_think_time(1500, 3000)

            # Attach GIF if requested
            if gif_query and not media_paths:
                await _attach_gif_if_requested(page, gif_query)
                await sleep_think_time(1000, 2000)

            submit_btn = await page.wait_for_selector(
                '[data-testid="tweetButtonInline"], [data-testid="tweetButton"], button[data-testid*="tweetButton"]',
                timeout=5000
            )
            if submit_btn:
                await human_click(page, submit_btn, 300, 700)
            await sleep_with_jitter(2500)

            await _post_action_cooldown_browse(page, scrolls=random.randint(1, 2))

            logger.info("Reply submitted successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "reply_tweet")
            logger.error("Failed to reply to tweet: %s", e)
            return False

class QuoteTweet(BaseAction):
    """Quote-tweets a tweet with custom commentary text."""

    async def execute(
        self,
        page: Page,
        quote_text: str,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
        gif_query: str | None = None,
        media_paths: list[str] | None = None,
    ) -> bool:
        try:
            if tweet_url:
                await page.goto(tweet_url, wait_until="commit", timeout=20000)
                status_check = await check_target_tweet_status(page, timeout=15000)
                if not status_check["available"]:
                    logger.warning("Quote target tweet unavailable: %s", status_check["reason"])
                    return False
                await sleep_think_time(1000, 2500)
                target_idx = 0
            else:
                await _navigate_home_if_needed(page)
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                if not tweet_elements:
                    return False
                visible_count = min(len(tweet_elements), 6)
                target_idx = tweet_index if tweet_index is not None else random.randint(0, visible_count - 1)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            if target_idx >= len(tweet_elements):
                return False

            target_tweet = tweet_elements[target_idx]
            await human_scroll_to_tweet(page, target_tweet)

            rt_btn = await target_tweet.query_selector(SELECTORS["retweet_button"])
            if not rt_btn:
                return False

            await human_click(page, rt_btn, 300, 800)

            # Wait for quote option in dropdown menu
            quote_item = await page.wait_for_selector(
                '[data-testid="Dropdown"] [role="menuitem"]:has-text("Quote"), [role="menuitem"]:has-text("Quote"), [role="menuitem"]:has-text("Quote post"), [data-testid="quoteTweet"], div[role="menuitem"] span:has-text("Quote"), a[href*="/compose/post?quote="]',
                timeout=5000,
            )
            if not quote_item and tweet_url:
                logger.info("Quote dropdown item not found; falling back to direct compose quote URL: %s", tweet_url)
                await page.goto(f"https://x.com/compose/post?quote={tweet_url}", wait_until="domcontentloaded", timeout=15000)
            elif quote_item:
                await sleep_think_time(400, 1000)
                await human_click(page, quote_item, 200, 500)
            else:
                logger.warning("Could not find Quote Tweet dropdown item and no tweet_url fallback.")
                return False

            # Wait for modal composer
            composer_sel = '[role="dialog"] [data-testid="tweetTextarea_0"], [data-testid="tweetTextarea_0"], [role="textbox"][data-testid*="tweetTextarea"]'
            editor = await page.wait_for_selector(composer_sel, timeout=8000)
            if not editor:
                logger.warning("Could not locate quote composer textarea.")
                return False

            if quote_text:
                quote_text = smart_truncate_tweet_text(quote_text, 260)
                await sleep_think_time(600, 1500)
                await human_type(page, composer_sel, quote_text)
                await sleep_think_time(1000, 2500)

            # Attach media files (images/videos) if provided
            if media_paths:
                await _attach_media_files(page, media_paths)
                await sleep_think_time(1500, 3000)

            # Attach GIF if requested
            if gif_query and not media_paths:
                await _attach_gif_if_requested(page, gif_query)
                await sleep_think_time(1000, 2000)

            post_btn = await page.wait_for_selector(
                '[role="dialog"] [data-testid="tweetButton"], [data-testid="tweetButton"]',
                timeout=5000,
            )
            if not post_btn:
                return False

            await human_click(page, post_btn, 300, 700)
            await sleep_with_jitter(2000)
            await _post_action_cooldown_browse(page, scrolls=1)
            logger.info("Quote Tweet published successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "quote_tweet")
            logger.error("Failed to quote tweet: %s", e)
            return False

