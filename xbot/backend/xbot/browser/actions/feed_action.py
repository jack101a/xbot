from __future__ import annotations
import logging
import random
import re
from typing import Any
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_mouse_move,
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

class BrowseFeed(BaseAction):
    """
    Browses the X home feed or search results by scrolling incrementally with inertia,
    mimicking natural reading pauses and occasional back-scrolls.
    """

    async def execute(self, page: Page, max_scrolls: int = 5, navigate_home: bool = True) -> list[dict[str, Any]]:
        try:
            if navigate_home:
                await _navigate_home_if_needed(page)
            logger.info("Starting feed browsing session (navigate_home=%s, current_url=%s).", navigate_home, page.url)
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
                        text = (await text_el.inner_text()).strip()
                        if not text:
                            continue

                        # Global Political Safety Filter
                        from xbot.ai.sniper import BANNED_POLITICS_REGEX
                        if BANNED_POLITICS_REGEX.search(text):
                            continue

                        # Extract author handle & name
                        author = ""
                        display_name = ""
                        is_blue_tick = False
                        user_el = await el.query_selector('[data-testid="User-Name"]')
                        if user_el:
                            user_text = await user_el.inner_text()
                            match = re.search(r"@([A-Za-z0-9_]+)", user_text)
                            if match:
                                author = match.group(1)
                            # Blue tick detection
                            verified_icon = await user_el.query_selector(
                                'svg[data-testid="icon-verified"], svg[aria-label*="Verified"]'
                            )
                            if verified_icon:
                                is_blue_tick = True

                        tweet_data: dict[str, Any] = {
                            "text": text,
                            "author": author or "creator",
                            "is_blue_tick": is_blue_tick,
                        }

                        # Scrape attached images
                        try:
                            img_el = await el.query_selector('[data-testid="tweetPhoto"] img, div[aria-label="Image"] img')
                            if img_el:
                                img_src = await img_el.get_attribute("src")
                                img_alt = await img_el.get_attribute("alt")
                                if img_src and img_src.startswith("http") and "profile_images" not in img_src and "emoji" not in img_src:
                                    tweet_data["media_urls"] = [img_src]
                                if img_alt and img_alt.strip() and img_alt != "Image":
                                    tweet_data["media_alts"] = [img_alt.strip()]
                        except Exception:
                            pass

                        # Check if this is an active growth or follow-back thread
                        if re.search(r"(follow\s*back|drop\s*your\s*handle|mutuals|f4f|verified\s*mutuals|connect)", text, re.IGNORECASE):
                            tweet_data["is_growth_thread"] = True

                        try:
                            link_el = await el.query_selector("a[href*='/status/']")
                            if link_el:
                                href = await link_el.get_attribute("href")
                                if href:
                                    tweet_data["url"] = f"https://x.com{href}" if href.startswith("/") else href
                                    tweet_data["tweet_id"] = _extract_tweet_id_from_url(tweet_data["url"])
                        except Exception:
                            pass

                        # Deduplicate by URL or text
                        if not any(t.get("url") == tweet_data.get("url") and t.get("text") == text for t in tweets):
                            tweets.append(tweet_data)

            logger.info("Browsed %d scrolls, gathered %d tweets", max_scrolls, len(tweets))
            return tweets
        except Exception as e:
            await self.capture_failure(page, "browse_feed")
            logger.error("Failed browsing feed: %s", e)
            raise e

class SearchQuery(BaseAction):
    """Performs a search query on X and browses results."""

    async def execute(self, page: Page, query: str) -> list[dict[str, Any]]:
        try:
            logger.info("Executing search query: %s", query)
            from urllib.parse import quote_plus
            search_url = f"https://x.com/search?q={quote_plus(query)}&f=live"
            await page.goto(search_url, wait_until="commit", timeout=20000)
            try:
                await page.wait_for_selector(SELECTORS["tweet"], timeout=15000)
            except Exception:
                pass
            await sleep_with_jitter(2000)

            # Browse search results without redirecting back to home
            browser = BrowseFeed(str(self.screenshot_dir))
            results = await browser.execute(page, max_scrolls=3, navigate_home=False)
            logger.info("Gathered %d search results for query '%s'.", len(results), query)
            return results
        except Exception as e:
            await self.capture_failure(page, "search")
            logger.error("Failed to perform search: %s", e)
            raise e

