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

from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

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

