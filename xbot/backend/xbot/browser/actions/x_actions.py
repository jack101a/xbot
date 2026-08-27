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

import json
import logging
import os
import random
import re
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

async def check_target_tweet_status(page: Page, timeout: int = 15000) -> dict[str, Any]:
    """
    Checks if a target tweet page is loaded, or if it is deleted/suspended/unavailable.
    Returns: {"available": bool, "reason": str | None}
    """
    try:
        # Fast check for X error banners or deleted post indicators
        err_banner = await page.query_selector(
            '[data-testid="error-detail"], [data-testid="emptyState"], [data-testid="empty_timeline"]'
        )
        if err_banner:
            txt = (await err_banner.inner_text()).lower()
            if any(w in txt for w in ("deleted", "does not exist", "suspended", "protected", "not available", "something went wrong")):
                logger.warning("Target tweet unavailable banner: %s", txt.replace("\n", " ")[:100])
                return {"available": False, "reason": f"Tweet unavailable: {txt.splitlines()[0]}"}

        # Wait for tweet article element
        await page.wait_for_selector(
            SELECTORS["tweet"],
            timeout=timeout
        )
        return {"available": True, "reason": None}
    except Exception as e:
        # Fallback query
        articles = await page.query_selector_all(SELECTORS["tweet"])
        if articles:
            return {"available": True, "reason": None}
        return {"available": False, "reason": f"Tweet element not found: {e}"}


async def _navigate_home_if_needed(page: Page) -> None:
    """Navigate to the X home feed if not already there."""
    current = page.url
    if "x.com/home" not in current and "twitter.com/home" not in current:
        try:
            await page.goto("https://x.com/home", wait_until="commit", timeout=25000)
            await page.wait_for_selector(SELECTORS["tweet"], timeout=15000)
        except Exception:
            pass
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
    try:
        await page.goto(detour, wait_until="domcontentloaded", timeout=20000)
        await sleep_think_time(1500, 4000)  # Browse briefly
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector(SELECTORS["tweet"], timeout=8000)
    except Exception:
        pass
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
            return []


async def _attach_gif_if_requested(page: Page, gif_query: str | None) -> bool:
    """Helper to open X native GIF search, search for a query, and select a relevant GIF."""
    if not gif_query:
        return False
    try:
        logger.info("Attempting to search and attach GIF for query: '%s'", gif_query)
        gif_btn_sel = (
            'button[data-testid="gifSearchButton"], '
            'button[aria-label="Add a GIF"], '
            'button[aria-label*="GIF"], '
            '[data-testid="fileInput"] + div button'
        )
        gif_btn = await page.query_selector(gif_btn_sel)
        if not gif_btn:
            logger.debug("GIF search button not found in composer.")
            return False

        await human_click(page, gif_btn, 200, 500)
        await sleep_think_time(800, 1500)

        # Search input in GIF modal
        search_input_sel = (
            'input[data-testid="SearchBox_Search_Input"], '
            'input[placeholder*="Search for GIFs"], '
            'input[aria-label*="Search for GIFs"]'
        )
        search_input = await page.wait_for_selector(search_input_sel, timeout=6000)
        if search_input:
            await human_type(page, search_input_sel, gif_query)
            await sleep_think_time(1200, 2500)

            # Select top GIF result
            gif_result_sel = (
                '[data-testid="gifSearchResults"] [role="button"], '
                '[data-testid="gifCategory"], '
                'div[role="button"][data-testid*="gif"]'
            )
            gif_items = await page.query_selector_all(gif_result_sel)
            if gif_items:
                target_gif = gif_items[0] if len(gif_items) == 1 else random.choice(gif_items[:min(3, len(gif_items))])
                await human_click(page, target_gif, 300, 700)
                await sleep_think_time(1000, 2000)
                logger.info("Successfully attached GIF for query: '%s'", gif_query)
                return True
    except Exception as e:
        logger.warning("Could not attach GIF: %s", e)
    return False


async def _attach_media_files(page: Page, media_paths: list[str] | None) -> bool:
    """Helper to upload local image/video files into X composer using input[type=file]."""
    if not media_paths:
        return False
    valid_paths = [p for p in media_paths if os.path.exists(p)]
    if not valid_paths:
        logger.warning("No valid media files found in paths: %s", media_paths)
        return False

    try:
        logger.info("Uploading %d media files to X composer: %s", len(valid_paths), valid_paths)
        file_input_sel = (
            'input[data-testid="fileInput"], '
            'input[type="file"][accept*="image"], '
            'input[type="file"]'
        )
        file_input = await page.query_selector(file_input_sel)
        if not file_input:
            file_input = await page.wait_for_selector(file_input_sel, state="attached", timeout=6000)

        if file_input:
            await file_input.set_input_files(valid_paths)
            await sleep_think_time(1500, 3000)
            
            # Wait for upload thumbnail preview to appear
            attachment_sel = (
                '[data-testid="attachments"], '
                '[data-testid="tweetPhoto"], '
                'div[role="group"][aria-label*="Media"], '
                'img[alt*="Image"]'
            )
            try:
                await page.wait_for_selector(attachment_sel, timeout=10000)
                logger.info("Media attachment preview loaded successfully.")
            except Exception:
                logger.warning("Attachment thumbnail selector timed out, proceeding.")

            return True
    except Exception as e:
        logger.warning("Could not upload media files: %s", e)
    return False


class ComposePost(BaseAction):
    """Composes and publishes a new post (tweet), optionally with attached images/GIF."""

    async def execute(
        self,
        page: Page,
        text: str,
        media_paths: list[str] | None = None,
        gif_query: str | None = None,
    ) -> bool:
        try:
            # Ensure text is strictly <= 260 chars for free tier X accounts
            if len(text) > 260:
                text = text[:257].rstrip() + "..."

            logger.info("Composing new post (%d chars, media=%s, gif=%s): %s...", len(text), media_paths, gif_query, text[:40])

            textarea_sel = (
                'div[data-testid="tweetTextarea_0"], '
                'textarea[data-testid="tweetTextarea_0"], '
                'div[role="textbox"][data-testid*="tweetTextarea"], '
                'div[contenteditable="true"][role="textbox"]'
            )

            # 1. Check if composer textarea is already visible on the current page
            textarea_el = await page.query_selector(textarea_sel)
            is_visible = False
            if textarea_el:
                try:
                    is_visible = await textarea_el.is_visible()
                except Exception:
                    is_visible = False

            # 2. If not visible, ensure we are on https://x.com or click SideNav_NewTweet_Button
            if not is_visible:
                side_nav_btn = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
                if side_nav_btn:
                    await human_click(page, side_nav_btn, 300, 700)
                    await sleep_think_time(800, 1500)
                else:
                    logger.info("Navigating to https://x.com to open composer...")
                    await page.goto("https://x.com", wait_until="load", timeout=25000)
                    await sleep_think_time(1500, 3000)

            # 3. Wait for composer textarea
            textarea_el = await page.wait_for_selector(textarea_sel, timeout=15000)
            if not textarea_el:
                raise RuntimeError("Could not locate tweet composer textarea")

            # Click textarea to focus
            await human_click(page, textarea_el, 200, 500)
            await sleep_think_time(600, 1200)

            # Type text via keyboard
            for ch in text:
                await page.keyboard.type(ch, delay=15)
            await sleep_think_time(1000, 2000)

            # Attach media files (images/videos) if provided
            if media_paths:
                await _attach_media_files(page, media_paths)
                await sleep_think_time(1500, 3000)

            # Attach GIF if requested
            if gif_query and not media_paths:
                await _attach_gif_if_requested(page, gif_query)
                await sleep_think_time(1000, 2000)

            # Submit post
            submit_sel = (
                'button[data-testid="tweetButtonInline"], '
                'button[data-testid="tweetButton"], '
                '[data-testid="tweetButtonContainer"] button, '
                'button[data-testid*="tweetButton"], '
                'button:not([data-testid*="SideNav"]):not(#nav-post-btn):has-text("Post")'
            )
            submit_btn = await page.wait_for_selector(submit_sel, timeout=10000)
            if submit_btn:
                await human_click(page, submit_btn, 300, 700)
            await sleep_with_jitter(4000)

            logger.info("Post published successfully.")
            return True
        except Exception as e:
            await self.capture_failure(page, "compose_post")
            logger.error("Failed to compose post: %s", e)
            return False


class ComposeThread(BaseAction):
    """
    Publishes a multi-tweet thread atomically using X's native composer 'Add Tweet' (+) button.
    Emulates realistic human typing, think time between tweets, and captures created tweet IDs.
    """

    SELECTORS = {
        "nav_post_btn": '[data-testid="SideNav_NewTweet_Button"]',
        "add_tweet_btn": (
            'button[data-testid="addButton"], '
            'button[aria-label="Add Tweet"], '
            'button[aria-label="Add another tweet"], '
            '[data-testid="tweetButtonInline"] ~ button'
        ),
        "post_all_btn": (
            'button[data-testid="tweetButton"], '
            'button[data-testid="tweetButtonInline"], '
            'button:has-text("Post all"), '
            'button:not([data-testid*="SideNav"]):not(#nav-post-btn):has-text("Post")'
        ),
    }

    async def execute(
        self,
        page: Page,
        tweets: list[str],
        media_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        if not tweets or len(tweets) < 2:
            return {"status": "failed", "error": "Threads must contain at least 2 tweets."}

        # Truncate any tweet exceeding free-tier limits
        clean_tweets = []
        for text in tweets:
            if len(text) > 280:
                clean_tweets.append(text[:277].rstrip() + "...")
            else:
                clean_tweets.append(text)

        captured_tweet_ids: list[str] = []

        async def handle_response(response: Any) -> None:
            try:
                if "CreateTweet" in response.url or "CreateDraft" in response.url:
                    if response.status == 200:
                        data = await response.json()
                        tweet_data = data.get("data", {}).get("create_tweet", {}).get("tweet_results", {}).get("result", {})
                        rest_id = tweet_data.get("rest_id") or tweet_data.get("tweet", {}).get("rest_id")
                        if rest_id and rest_id not in captured_tweet_ids:
                            captured_tweet_ids.append(rest_id)
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            logger.info("Composing %d-tweet thread on X (media_paths=%s)...", len(clean_tweets), media_paths)

            # 1. Start from /home feed to ensure hydrated React DOM
            await _navigate_home_if_needed(page)
            await sleep_think_time(1000, 2000)

            # 2. Click SideNav New Post button to open compose modal
            side_nav_btn = await page.query_selector(self.SELECTORS["nav_post_btn"])
            if not side_nav_btn:
                side_nav_btn = await page.query_selector('a[href="/compose/post"], a[href="/compose/tweet"], [data-testid="SideNav_NewTweet_Button"]')

            if side_nav_btn:
                await human_click(page, side_nav_btn, 300, 700)
                await sleep_think_time(1000, 2000)

            textarea_sel = (
                'div[role="dialog"] div[data-testid^="tweetTextarea_"], '
                'div[role="dialog"] div[role="textbox"], '
                'div[data-testid="tweetTextarea_0"], '
                'div[role="textbox"][data-testid*="tweetTextarea"], '
                'div[contenteditable="true"][role="textbox"]'
            )

            try:
                first_textarea = await page.wait_for_selector(textarea_sel, state="visible", timeout=12000)
            except Exception:
                # Fallback to inline home composer
                first_textarea = await page.wait_for_selector(
                    'div[role="textbox"][data-testid*="tweetTextarea"], div[contenteditable="true"][role="textbox"]',
                    timeout=10000
                )

            if not first_textarea:
                raise RuntimeError("Could not locate tweet composer textarea for thread.")

            # Focus and type Tweet 1
            await human_click(page, first_textarea, 200, 400)
            await sleep_micro(200, 500)
            for ch in clean_tweets[0]:
                await page.keyboard.type(ch, delay=random.uniform(12, 30))
            await sleep_think_time(1000, 2000)

            # Attach media to Tweet 1 if provided
            if media_paths:
                await _attach_media_files(page, media_paths)
                await sleep_think_time(1000, 2000)

            # Sequentially add subsequent tweets via Add Tweet (+) button
            for idx in range(1, len(clean_tweets)):
                tweet_text = clean_tweets[idx]
                add_btn = await page.query_selector(self.SELECTORS["add_tweet_btn"])
                if not add_btn:
                    add_btn = await page.query_selector('button[aria-label*="Add" i], button[data-testid="addButton"], [data-testid="tweetButtonInline"] ~ button')

                if add_btn:
                    await human_click(page, add_btn, 250, 550)
                    await sleep_with_jitter(1500)

                all_textareas = await page.query_selector_all('div[role="dialog"] div[role="textbox"], div[data-testid^="tweetTextarea_"]')
                target_el = all_textareas[idx] if idx < len(all_textareas) else (all_textareas[-1] if all_textareas else None)

                if target_el:
                    await human_click(page, target_el, 200, 400)
                    await sleep_micro(200, 500)
                    for ch in tweet_text:
                        await page.keyboard.type(ch, delay=random.uniform(12, 30))
                    await sleep_think_time(1000, 2500)

            # 3. Submit post all
            logger.info("Submitting entire thread via 'Post all'...")
            submit_btn = await page.wait_for_selector(self.SELECTORS["post_all_btn"], timeout=10000)
            if submit_btn:
                await human_click(page, submit_btn, 300, 800)

            await sleep_with_jitter(5000)

            root_id = captured_tweet_ids[0] if captured_tweet_ids else None
            logger.info("Thread published successfully. Root ID: %s, Total: %d", root_id, len(clean_tweets))
            return {
                "status": "success",
                "root_tweet_id": root_id,
                "tweet_ids": captured_tweet_ids,
                "total_tweets": len(clean_tweets),
            }

        except Exception as e:
            await self.capture_failure(page, "compose_thread")
            logger.error("Failed to compose thread: %s", e)
            return {"status": "failed", "error": str(e), "tweet_ids": captured_tweet_ids}
        finally:
            try:
                page.remove_listener("response", handle_response)
            except Exception:
                pass


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


async def human_scroll_to_tweet(page: Page, tweet_el: Any) -> None:
    """Scroll a tweet into view and add a read pause."""
    await tweet_el.scroll_into_view_if_needed()
    await sleep_think_time(800, 2500)


class ReplyToTweet(BaseAction):
    """
    Replies to a tweet. Uses tweet_url when available (from AI planner).
    Falls back to a randomly chosen visible tweet (not always index 0).
    Supports optional reaction GIF attachment.
    """

    async def scrape_target_tweet_context(
        self, page: Page, target_idx: int = 0, tweet_url: str | None = None
    ) -> dict[str, Any]:
        """
        Scrapes full live text, author, metrics, media URLs/alts, and top visible comment replies
        from the current tweet thread.
        """
        try:
            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            if not tweet_elements or target_idx >= len(tweet_elements):
                return {}

            target_tweet = tweet_elements[target_idx]

            # Author handle
            author = ""
            user_el = await target_tweet.query_selector('[data-testid="User-Name"]')
            if user_el:
                user_text = await user_el.inner_text()
                match = re.search(r"@([A-Za-z0-9_]+)", user_text)
                if match:
                    author = match.group(1)

            # Main tweet text
            text = ""
            text_el = await target_tweet.query_selector(SELECTORS.get("tweet_text", '[data-testid="tweetText"]'))
            if text_el:
                text = (await text_el.inner_text()).strip()

            # Helper to parse metric numbers like "1.2K", "450", "2M", "1,200"
            def _parse_metric(val_str: str | None) -> int:
                if not val_str:
                    return 0
                val = str(val_str).replace(",", "").replace("\u00a0", " ").strip()
                m = re.search(r'([\d\.]+)\s*([KkMmBbtT]?)', val)
                if not m:
                    return 0
                try:
                    num = float(m.group(1))
                    unit = m.group(2).upper()
                    if unit == "K":
                        return int(num * 1000)
                    elif unit == "M":
                        return int(num * 1000000)
                    elif unit == "B" or unit == "T":
                        return int(num * 1000000000)
                    return int(num)
                except Exception:
                    return 0

            # Scrape top comments in thread (filtered & sorted by popularity/likes)
            collected_comments: list[dict[str, Any]] = []
            seen_texts: set[str] = set()

            async def _collect_comments():
                nonlocal collected_comments, seen_texts
                all_tweets = await page.query_selector_all(SELECTORS["tweet"])
                comment_elements = all_tweets[target_idx + 1:] if len(all_tweets) > target_idx else []
                for comment_el in comment_elements:
                    c_text_el = await comment_el.query_selector(SELECTORS.get("tweet_text", '[data-testid="tweetText"]'))
                    if not c_text_el:
                        continue
                    c_text = (await c_text_el.inner_text()).strip()
                    if not c_text or c_text == text or c_text in seen_texts:
                        continue
                    seen_texts.add(c_text)

                    # Commenter handle
                    c_author = ""
                    c_user_el = await comment_el.query_selector('[data-testid="User-Name"]')
                    if c_user_el:
                        c_user_text = await c_user_el.inner_text()
                        c_match = re.search(r"@([A-Za-z0-9_]+)", c_user_text)
                        if c_match:
                            c_author = c_match.group(1)

                    # Extract like count / popularity
                    c_likes = 0
                    try:
                        like_el = await comment_el.query_selector('[data-testid="like"], button[aria-label*="Like"], div[data-testid="like"]')
                        if like_el:
                            aria_label = await like_el.get_attribute("aria-label") or ""
                            like_text = await like_el.inner_text() or ""
                            c_likes = _parse_metric(aria_label) or _parse_metric(like_text)
                    except Exception:
                        pass

                    collected_comments.append({
                        "author": c_author,
                        "text": c_text,
                        "likes": c_likes,
                    })

            # First pass
            await _collect_comments()

            # Scroll gently down to load 15-20 comments to find the most popular/top-liked
            try:
                if len(collected_comments) < 8:
                    await page.evaluate("window.scrollBy(0, 600)")
                    await sleep_with_jitter(1000)
                    await _collect_comments()

                if len(collected_comments) < 15:
                    await page.evaluate("window.scrollBy(0, 800)")
                    await sleep_with_jitter(1000)
                    await _collect_comments()
            except Exception:
                pass

            # Sort descending by likes / popularity (most popular first)
            collected_comments.sort(key=lambda c: c["likes"], reverse=True)
            top_comments = collected_comments[:10]

            # Scrape attached media images, videos, and alt text
            media_urls: list[str] = []
            media_alts: list[str] = []
            try:
                # 1. Images
                img_elements = await target_tweet.query_selector_all(
                    '[data-testid="tweetPhoto"] img, div[aria-label="Image"] img, img[alt*="Image"], img'
                )
                for img in img_elements:
                    src = await img.get_attribute("src")
                    alt = await img.get_attribute("alt")
                    if src and src.startswith("http") and not any(ignored in src for ignored in ("profile_images", "emoji", "svg", "twemoji", "avatar")):
                        if src not in media_urls:
                            media_urls.append(src)
                    if alt and alt.strip():
                        alt_clean = alt.strip()
                        if alt_clean.lower() not in ("image", "embedded video", "profile image", "avatar") and alt_clean not in media_alts:
                            media_alts.append(alt_clean)

                # 2. Videos
                video_elements = await target_tweet.query_selector_all(
                    '[data-testid="videoPlayer"] video, [data-testid="videoComponent"] video, video'
                )
                for vid in video_elements:
                    v_src = await vid.get_attribute("src")
                    if not v_src:
                        source_el = await vid.query_selector("source")
                        if source_el:
                            v_src = await source_el.get_attribute("src")
                    if v_src and v_src.startswith("http") and v_src not in media_urls:
                        media_urls.append(v_src)
                    elif not v_src:
                        v_poster = await vid.get_attribute("poster")
                        if v_poster and v_poster.startswith("http") and v_poster not in media_urls:
                            media_urls.append(v_poster)
            except Exception:
                pass

            # Extract root tweet engagement metrics (views/impressions, likes, replies, retweets)
            views_count = 0
            likes_count = 0
            replies_count = 0
            retweets_count = 0
            try:
                # 1. Views / Analytics
                view_el = await target_tweet.query_selector(
                    'a[href*="/analytics"], [data-testid="app-text-transition-container"], [aria-label*="Views"], [aria-label*="views"], [aria-label*="Impressions"], [aria-label*="impressions"]'
                )
                if view_el:
                    v_aria = await view_el.get_attribute("aria-label") or ""
                    v_text = await view_el.inner_text() or ""
                    views_count = _parse_metric(v_aria) or _parse_metric(v_text)

                # 2. Likes
                like_el = await target_tweet.query_selector('[data-testid="like"], button[aria-label*="Like"], div[data-testid="like"]')
                if like_el:
                    l_aria = await like_el.get_attribute("aria-label") or ""
                    l_text = await like_el.inner_text() or ""
                    likes_count = _parse_metric(l_aria) or _parse_metric(l_text)

                # 3. Replies
                reply_el = await target_tweet.query_selector('[data-testid="reply"], button[aria-label*="Reply"], div[data-testid="reply"]')
                if reply_el:
                    r_aria = await reply_el.get_attribute("aria-label") or ""
                    r_text = await reply_el.inner_text() or ""
                    replies_count = _parse_metric(r_aria) or _parse_metric(r_text)

                # 4. Retweets
                rt_el = await target_tweet.query_selector('[data-testid="retweet"], button[aria-label*="Repost"], button[aria-label*="Retweet"], div[data-testid="retweet"]')
                if rt_el:
                    rt_aria = await rt_el.get_attribute("aria-label") or ""
                    rt_text = await rt_el.inner_text() or ""
                    retweets_count = _parse_metric(rt_aria) or _parse_metric(rt_text)
            except Exception:
                pass

            logger.info(
                "Scraped live thread context on page: author=@%s, text_preview='%s', views=%d, likes=%d, captured_comments=%d, media=%d",
                author,
                text[:40],
                views_count,
                likes_count,
                len(top_comments),
                len(media_urls),
            )
            return {
                "author": author,
                "text": text,
                "views": views_count,
                "impressions": views_count,
                "likes": likes_count,
                "replies": replies_count,
                "retweets": retweets_count,
                "top_comments": top_comments,
                "media_urls": media_urls[:4],
                "media_alts": media_alts[:4],
            }
        except Exception as e:
            logger.debug("Error scraping target tweet context: %s", e)
            return {}

    async def execute(
        self,
        page: Page,
        reply_text: str,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
        gif_query: str | None = None,
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

            logger.info("Replying to tweet at index %d (gif=%s)", target_idx, gif_query)

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

            # Ensure reply_text is strictly <= 260 chars
            if len(reply_text) > 260:
                reply_text = reply_text[:257].rstrip() + "..."

            # Type reply
            await human_type(page, textarea_sel, reply_text)
            await sleep_think_time(800, 2000)  # Review reply

            # Attach GIF if requested
            if gif_query:
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


class QuoteTweet(BaseAction):
    """Quote-tweets a tweet with custom commentary text."""

    async def execute(
        self,
        page: Page,
        quote_text: str,
        tweet_url: str | None = None,
        tweet_index: int | None = None,
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
                '[data-testid="Dropdown"] [role="menuitem"]:has-text("Quote"), [role="menuitem"]:has-text("Quote"), a[href*="/compose/post?quote="]',
                timeout=5000,
            )
            if not quote_item:
                logger.warning("Could not find Quote Tweet dropdown item.")
                return False

            await sleep_think_time(400, 1000)
            await human_click(page, quote_item, 200, 500)

            # Wait for modal composer
            composer_sel = '[role="dialog"] [data-testid="tweetTextarea_0"], [data-testid="tweetTextarea_0"]'
            editor = await page.wait_for_selector(composer_sel, timeout=8000)
            if not editor:
                logger.warning("Could not locate quote composer textarea.")
                return False

            await sleep_think_time(600, 1500)
            await human_type(page, composer_sel, quote_text)
            await sleep_think_time(1000, 2500)

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



class FollowUser(BaseAction):
    """Follows a user by navigating to their profile."""

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            logger.info("Navigating to user profile to follow: %s", clean)
            await page.goto(f"https://x.com/{clean}", wait_until="commit", timeout=20000)
            
            # Wait for profile header or follow button
            try:
                await page.wait_for_selector('[data-testid="UserName"], [data-testid*="UserAvatar"], [data-testid*="follow"], h2', timeout=15000)
            except Exception:
                pass

            # Check for account suspended / non-existent banners
            err_banner = await page.query_selector('[data-testid="error-detail"], [data-testid="emptyState"]')
            if err_banner:
                txt = (await err_banner.inner_text()).lower()
                if any(w in txt for w in ("suspended", "does not exist", "blocked", "protected", "not available")):
                    logger.warning("Target user @%s unavailable: %s", clean, txt.replace("\n", " ")[:80])
                    return False

            # Human: scan profile for a moment
            await sleep_think_time(1500, 3500)
            await human_scroll(page, random.randint(100, 250), "down")
            await sleep_think_time(800, 1800)
            await human_scroll(page, random.randint(50, 150), "up")
            await sleep_think_time(600, 1500)

            # Check already-following via case-insensitive aria-label or inner text
            already_following = await page.query_selector(
                f'button[aria-label*="Following @" i], button[aria-label*="Unfollow @" i], button:has-text("Following"), button:has-text("Unfollow")'
            )
            if already_following:
                logger.info("Already following user: %s", username)
                return True

            # Follow button — try flexible case-insensitive aria-label, dynamic testids, and text
            follow_btn = await page.query_selector(f'button[aria-label*="Follow @{clean}" i]')
            if not follow_btn:
                follow_btn = await page.query_selector('button[aria-label*="Follow @" i]')
            if not follow_btn:
                follow_btn = await page.query_selector('button[data-testid*="-follow"], button[data-testid$="-follow"], [data-testid="placementTracking"]')
            if not follow_btn:
                # Text fallback
                for btn in await page.query_selector_all("button"):
                    txt = (await btn.inner_text()).strip()
                    if txt == "Follow":
                        follow_btn = btn
                        break

            if not follow_btn:
                logger.warning("Could not locate follow button for: %s", username)
                return False

            btn_text = (await follow_btn.inner_text()).strip()
            if btn_text in ("Following", "Unfollow"):
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
            await page.goto(f"https://x.com/{clean}", wait_until="domcontentloaded", timeout=20000)
            try:
                await page.wait_for_selector('[data-testid="UserName"], [data-testid*="UserAvatar"], h2', timeout=12000)
            except Exception:
                pass
            await sleep_think_time(1500, 4000)

            # X uses dynamic testid e.g. '1605-unfollow' — use aria-label first, then testid
            unfollow_btn = await page.query_selector(f'button[aria-label="Following @{clean}"]')
            if not unfollow_btn:
                unfollow_btn = await page.query_selector(f'button[aria-label="Unfollow @{clean}"]')
            if not unfollow_btn:
                unfollow_btn = await page.query_selector("[data-testid$='-unfollow'], [data-testid='placementTracking']")
            if not unfollow_btn:
                # Text check
                for btn in await page.query_selector_all("button"):
                    txt = (await btn.inner_text()).strip()
                    if txt in ("Following", "Unfollow"):
                        unfollow_btn = btn
                        break

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
            await page.goto(search_url, wait_until="commit", timeout=20000)
            try:
                await page.wait_for_selector(SELECTORS["tweet"], timeout=15000)
            except Exception:
                pass
            await sleep_with_jitter(2000)

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
            await page.goto(f"https://x.com/{clean}", wait_until="commit", timeout=20000)
            try:
                await page.wait_for_selector(
                    SELECTORS.get("profile_avatar", "[data-testid*='UserAvatar']"), timeout=15000
                )
            except Exception:
                pass
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
            await page.goto("https://x.com/explore/tabs/trending", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_selector("[data-testid='trend']", timeout=10000)
            await sleep_with_jitter(2000)

            # Human-like scroll through trending section
            await human_scroll(page, random.randint(200, 400), "down")
            await sleep_think_time(1000, 2500)

            from xbot.ai.sniper import BANNED_POLITICS_REGEX
            trends = []
            trend_elements = await page.query_selector_all("[data-testid='trend']")
            for el in trend_elements[:15]:
                text = await el.inner_text()
                if BANNED_POLITICS_REGEX.search(text):
                    continue
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
            await page.goto(f"https://x.com/{clean}", wait_until="domcontentloaded", timeout=20000)
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
                await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
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
            await page.goto(f"https://x.com/{my_username}/following", wait_until="domcontentloaded", timeout=20000)
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
            await page.goto(likes_url, wait_until="domcontentloaded", timeout=20000)
            
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
    Scrapes the list of followers or following handles for a given user,
    with built-in detection and filtering for Verified Blue-Tick / Gold-Tick accounts.
    """

    async def execute(
        self,
        page: Page,
        username: str,
        list_type: str = "followers",
        limit: int = 100,
        verified_only: bool = False,
    ) -> list[str]:
        try:
            clean = username.lstrip("@")
            url = f"https://x.com/{clean}/{list_type}"
            logger.info("Scraping %s list for @%s (limit: %d, verified_only: %s)", list_type, clean, limit, verified_only)
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            try:
                await page.wait_for_selector("[data-testid='UserCell']", timeout=15000)
            except Exception:
                logger.warning("No UserCell selector loaded on follow list page.")
                return []

            await sleep_with_jitter(2000)

            handles = []
            seen_handles = set()
            scroll_count = 0
            max_scrolls = 20

            while len(handles) < limit and scroll_count < max_scrolls:
                cells = await page.query_selector_all("[data-testid='UserCell']")
                for cell in cells:
                    # Check verified badge
                    is_verified = bool(
                        await cell.query_selector(
                            "svg[data-testid='icon-verified'], [aria-label*='Verified'], svg[aria-label*='Verified']"
                        )
                    )

                    if verified_only and not is_verified:
                        continue

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
                        if len(handles) >= limit:
                            break
                
                if len(handles) >= limit:
                    break

                scroll_count += 1
                await human_scroll(page, random.randint(400, 700), "down")
                await sleep_with_jitter(1500)
                
            logger.info("Scraped %d %s handles from @%s (verified_only=%s)", len(handles), list_type, clean, verified_only)
            return handles
        except Exception as e:
            await self.capture_failure(page, f"scrape_{list_type}_{username}")
            logger.error("Error scraping %s for %s: %s", list_type, username, e)
            return []


class HarvestFollowBackThread(BaseAction):
    """
    Navigates to an active follow-back / mutuals thread URL,
    analyzes the post and its comment section, and extracts high-reciprocity Blue Tick candidates.
    """

    async def execute(self, page: Page, tweet_url: str, max_candidates: int = 8) -> list[dict[str, Any]]:
        candidates = []
        try:
            logger.info("Harvesting active follow-back thread: %s", tweet_url)
            await page.goto(tweet_url, wait_until="commit", timeout=20000)
            status_check = await check_target_tweet_status(page, timeout=15000)
            if not status_check["available"]:
                logger.warning("Thread harvest target tweet unavailable: %s", status_check["reason"])
                return []
            await sleep_think_time(1000, 2500)

            # Scroll down to load thread comments
            for _ in range(2):
                await human_scroll(page, random.randint(300, 600), "down")
                await sleep_think_time(1000, 2000)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            seen_handles: set[str] = set()

            # Skip root tweet (index 0), inspect comment replies (index 1+)
            for el in tweet_elements[1:]:
                try:
                    user_el = await el.query_selector('[data-testid="User-Name"]')
                    if not user_el:
                        continue
                    u_text = await user_el.inner_text()
                    m = re.search(r"@([A-Za-z0-9_]+)", u_text)
                    if not m:
                        continue
                    handle = m.group(1)
                    if handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    # Check verified / blue tick
                    verified_el = await user_el.query_selector(
                        'svg[data-testid="icon-verified"], svg[aria-label="Verified account"], svg[aria-label="Blue tick"]'
                    )
                    is_blue_tick = verified_el is not None

                    # Comment text
                    c_text_el = await el.query_selector(SELECTORS.get("tweet_text", '[data-testid="tweetText"]'))
                    comment_body = (await c_text_el.inner_text()).strip() if c_text_el else ""

                    # Check for mutuals/f4f intent
                    f4f_intent = bool(re.search(r"(drop|f4f|follow|mutual|following|connect|back)", comment_body, re.IGNORECASE))
                    score = 90.0 if (is_blue_tick and f4f_intent) else (75.0 if is_blue_tick else (60.0 if f4f_intent else 45.0))

                    display_name = u_text.split("@")[0].strip() or handle

                    candidates.append({
                        "handle": handle,
                        "display_name": display_name,
                        "is_blue_tick": is_blue_tick,
                        "comment": comment_body[:100],
                        "source_tweet_url": tweet_url,
                        "reciprocity_score": score,
                    })
                    if len(candidates) >= max_candidates:
                        break
                except Exception:
                    continue

            logger.info("Harvested %d candidate peers from follow-back thread %s", len(candidates), tweet_url)
            return candidates
        except Exception as ex:
            logger.warning("Error harvesting follow-back thread %s: %s", tweet_url, ex)
            return []


class CheckProfileFollowsYou(BaseAction):
    """
    Navigates to a profile and checks if the 'Follows you' badge is present.
    """

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            await page.goto(f"https://x.com/{clean}", wait_until="domcontentloaded", timeout=15000)
            await sleep_think_time(1000, 2500)

            # Check for 'Follows you' badge
            indicator = await page.query_selector(
                '[data-testid="userFollowIndicator"], span:has-text("Follows you"), div:has-text("Follows you")'
            )
            return indicator is not None
        except Exception as e:
            logger.debug("Error checking follows-you badge for @%s: %s", username, e)
            return False


class ScrapeCreatorStudioMetrics(BaseAction):
    """
    Navigates to https://x.com/i/jf/creators/studio, clicks into Original Content Rewards eligibility,
    and extracts official live account-wide metrics:
    - Verified Followers (out of 500)
    - 90-Day Verified Home Timeline Impressions (out of 500,000)
    """

    async def execute(self, page: Page) -> dict[str, Any]:
        try:
            logger.info("Opening X Creator Studio to scrape official monetization & impression metrics...")
            await page.goto("https://x.com/i/jf/creators/studio", wait_until="domcontentloaded", timeout=25000)
            await sleep_think_time(1500, 3000)

            btn1 = await page.query_selector("text=Original Content Rewards")
            if btn1:
                await human_click(page, btn1, 200, 500)
                await sleep_think_time(1000, 2000)

            btn2 = await page.query_selector("text=Check Original Content Rewards eligibility")
            if btn2:
                await human_click(page, btn2, 200, 500)
                await sleep_think_time(1500, 3000)

            body_text = await page.inner_text("body")

            # Extract verified followers (e.g. "16")
            vf_match = re.search(r"Have at least 500 Verified followers\s+([0-9,]+)", body_text)
            verified_followers = int(vf_match.group(1).replace(",", "")) if vf_match else 0

            # Extract 90-day impressions (e.g. "0" or "45K" or "1.2M")
            imp_match = re.search(r"Have at least 500K Verified Home Timeline impressions.*?\n+([0-9,KMkm.]+)", body_text)
            imp_str = imp_match.group(1).strip() if imp_match else "0"
            
            verified_impressions_90d = 0
            if imp_str:
                clean_imp = imp_str.upper().replace(",", "")
                if "M" in clean_imp:
                    verified_impressions_90d = int(float(clean_imp.replace("M", "")) * 1000000)
                elif "K" in clean_imp:
                    verified_impressions_90d = int(float(clean_imp.replace("K", "")) * 1000)
                else:
                    try:
                        verified_impressions_90d = int(float(clean_imp))
                    except Exception:
                        verified_impressions_90d = 0

            from datetime import datetime as dt
            logger.info("Successfully scraped Creator Studio: %d verified followers, %d 90-day verified impressions", verified_followers, verified_impressions_90d)
            return {
                "status": "success",
                "verified_followers": verified_followers,
                "verified_impressions_90d": verified_impressions_90d,
                "scraped_at": dt.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning("Failed to scrape Creator Studio metrics: %s", e)
            return {
                "status": "failed",
                "error": str(e),
                "verified_followers": 0,
                "verified_impressions_90d": 0,
            }



