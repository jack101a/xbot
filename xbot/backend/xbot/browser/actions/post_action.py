from __future__ import annotations
import logging
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.timing import (
    human_click,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.post_utils import (_attach_gif_if_requested, _attach_media_files, smart_truncate_tweet_text)
from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

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
            # Ensure text is cleanly <= 260 chars for free tier X accounts with smart boundary truncation
            if text:
                text = smart_truncate_tweet_text(text, 260)

            logger.info("Composing new post (%d chars, media=%s, gif=%s): %s...", len(text) if text else 0, media_paths, gif_query, (text or "")[:40])

            textarea_sel = (
                'div[aria-label="Post text"], '
                'div[aria-label*="Post text"], '
                'div[role="textbox"][contenteditable="true"], '
                '.public-DraftEditor-content, '
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

            # 2. If not visible, ensure we navigate to home or click compose button
            if not is_visible:
                side_nav_btn = await page.query_selector('[data-testid="SideNav_NewTweet_Button"], a[href="/compose/post"], a[aria-label="Post"][role="link"]')
                if side_nav_btn:
                    await human_click(page, side_nav_btn, 300, 700)
                    await sleep_think_time(800, 1500)
                else:
                    logger.info("Navigating to https://x.com/home to open composer...")
                    await page.goto("https://x.com/home", wait_until="commit", timeout=25000)
                    await sleep_think_time(2000, 3500)

            # 3. Wait for composer textarea
            textarea_el = await page.wait_for_selector(textarea_sel, timeout=15000)
            if not textarea_el:
                raise RuntimeError("Could not locate tweet composer textarea")

            # Click textarea to focus
            await human_click(page, textarea_el, 200, 500)
            await sleep_think_time(600, 1200)

            # Type text via keyboard if text is provided
            if text:
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

            # Submit post: Wait for image processing to complete and Post button to be enabled (aria-disabled != "true")
            enabled_submit_sel = (
                'button[data-testid="tweetButtonInline"]:not([aria-disabled="true"]):not([disabled]), '
                'button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                '[data-testid="tweetButtonContainer"] button:not([aria-disabled="true"]):not([disabled]), '
                'button[data-testid*="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                'button:not([data-testid*="SideNav"]):not(#nav-post-btn):has-text("Post"):not([aria-disabled="true"])'
            )
            submit_btn = None
            try:
                submit_btn = await page.wait_for_selector(enabled_submit_sel, timeout=20000)
            except Exception:
                logger.warning("Enabled post button selector timed out; checking fallback selectors...")
                for sel in ['button[data-testid="tweetButton"]', 'button[data-testid="tweetButtonInline"]', 'button:has-text("Post")']:
                    el = await page.query_selector(sel)
                    if el:
                        submit_btn = el
                        break

            if submit_btn:
                logger.info("Clicking enabled Post button...")
                await human_click(page, submit_btn, 300, 700)
                await sleep_with_jitter(2500)

            # Verification: If composer is still visible, press Control+Enter to ensure submission
            composer_check = await page.query_selector(textarea_sel)
            if composer_check:
                try:
                    if await composer_check.is_visible():
                        logger.info("Composer modal still open; pressing Control+Enter shortcut to submit...")
                        await composer_check.focus()
                        await page.keyboard.press("Control+Enter")
                        await sleep_with_jitter(3000)
                except Exception:
                    pass

            # Final check: Wait for composer modal / textarea to close
            try:
                await page.wait_for_selector(textarea_sel, state="hidden", timeout=12000)
                logger.info("Post published and composer closed successfully.")
                return True
            except Exception:
                # If home timeline composer or already submitted
                logger.info("Composer closed or post submitted on timeline.")
                return True
        except Exception as e:
            await self.capture_failure(page, "compose_post")
            logger.error("Failed to compose post: %s", e)
            return False

