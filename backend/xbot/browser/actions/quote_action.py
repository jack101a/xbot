from __future__ import annotations
import logging
import random
from typing import Any
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

from xbot.browser.actions.post_utils import (
    _attach_gif_if_requested,
    _attach_media_files,
    smart_truncate_tweet_text,
)
from xbot.browser.actions.utils import (
    check_target_tweet_status,
    _navigate_home_if_needed,
    _random_tab_detour,
    _post_action_cooldown_browse,
    _extract_tweet_id_from_url,
    human_scroll_to_tweet,
    check_daily_post_limit,
)

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
        captured_tweet_ids: list[str] = []

        async def _handle_quote_response(response: Any) -> None:
            try:
                if "CreateTweet" in response.url or "CreateDraft" in response.url:
                    if response.status == 200:
                        data = await response.json()
                        tweet_data = (
                            data.get("data", {})
                            .get("create_tweet", {})
                            .get("tweet_results", {})
                            .get("result", {})
                        )
                        rest_id = tweet_data.get("rest_id") or tweet_data.get("tweet", {}).get("rest_id")
                        if rest_id and rest_id not in captured_tweet_ids:
                            captured_tweet_ids.append(rest_id)
            except Exception:
                pass

        page.on("response", _handle_quote_response)

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

            # Wait for enabled Post button
            enabled_submit_sel = (
                '[role="dialog"] button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                '[role="dialog"] [data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                'button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled])'
            )
            post_btn = None
            try:
                post_btn = await page.wait_for_selector(enabled_submit_sel, timeout=10000)
            except Exception:
                # Fallback to general tweetButton if enabled selector timed out (e.g. in mock HTML)
                post_btn = await page.query_selector('[role="dialog"] [data-testid="tweetButton"], [data-testid="tweetButton"]')

            if not post_btn:
                logger.warning("Could not find Post button in quote composer.")
                return False

            # Check if modal is blocked by daily limit banner before clicking
            pre_limit = await check_daily_post_limit(page)
            if pre_limit:
                await self.capture_failure(page, "x_daily_limit_reached")
                logger.critical("Aborting quote: X Daily Post Limit detected (%s)", pre_limit)
                return {
                    "status": "failed",
                    "quoted": False,
                    "reason": "daily_post_limit_reached",
                    "error": f"You've hit the daily post limit on X ({pre_limit})",
                    "daily_limit_reached": True,
                }

            # Submit via direct DOM click to ensure submission through overlays
            if post_btn:
                logger.info("Clicking quote submit button...")
                try:
                    await post_btn.click(timeout=2500)
                except Exception:
                    try:
                        await post_btn.click(force=True, timeout=2500)
                    except Exception:
                        await page.evaluate('(btn) => btn.click()', post_btn)
            await sleep_with_jitter(1500)

            # Verification 1: If quote dialog is still open, check daily limit and try fallback shortcuts
            dialog_sel = '[role="dialog"]'
            dialog = await page.query_selector(dialog_sel)
            if dialog and await dialog.is_visible():
                limit_chk = await check_daily_post_limit(page)
                if limit_chk:
                    await self.capture_failure(page, "x_daily_limit_reached")
                    logger.critical("Quote tweet rejected: X Daily Post Limit detected (%s)", limit_chk)
                    return {
                        "status": "failed",
                        "quoted": False,
                        "reason": "daily_post_limit_reached",
                        "error": f"You've hit the daily post limit on X ({limit_chk})",
                        "daily_limit_reached": True,
                    }
                logger.info("Quote dialog still open; trying fallback shortcuts...")
                if post_btn:
                    try:
                        await post_btn.click(force=True)
                    except Exception:
                        try:
                            await page.evaluate('(btn) => btn.click()', post_btn)
                        except Exception:
                            pass
                try:
                    await editor.focus()
                    await page.keyboard.press("Meta+Enter")
                    await page.keyboard.press("Control+Enter")
                    await sleep_with_jitter(2000)
                except Exception:
                    pass

            # Verification 2: Check for error toast on X
            toast = await page.query_selector('[data-testid="toast"]')
            if toast:
                toast_text = (await toast.inner_text()).strip()
                if any(err_kw in toast_text.lower() for err_kw in ["wasn't sent", "error", "failed", "something went wrong"]):
                    logger.error("Quote tweet rejected by X with toast: %s", toast_text)
                    return False
                if "your post was sent" in toast_text.lower():
                    logger.info("Confirmed success toast on X: %s", toast_text)

            # Verification 3: Wait for dialog to close
            try:
                await page.wait_for_selector(dialog_sel, state="hidden", timeout=12000)
                logger.info("Quote modal confirmed closed.")
            except Exception:
                pass

            # If on live X and dialog is still visible and no tweet captured, fail
            if "x.com" in getattr(page, "url", ""):
                dialog = await page.query_selector(dialog_sel)
                if dialog and await dialog.is_visible() and not captured_tweet_ids:
                    final_limit = await check_daily_post_limit(page)
                    if final_limit:
                        await self.capture_failure(page, "x_daily_limit_reached")
                        return {
                            "status": "failed",
                            "quoted": False,
                            "reason": "daily_post_limit_reached",
                            "error": f"You've hit the daily post limit on X ({final_limit})",
                            "daily_limit_reached": True,
                        }
                    logger.error("Quote modal still open on live X and no tweet captured; aborting false success.")
                    return False

            await sleep_with_jitter(2000)
            await _post_action_cooldown_browse(page, scrolls=1)

            published_tweet_id = captured_tweet_ids[0] if captured_tweet_ids else None
            logger.info("Quote Tweet published successfully. Tweet ID: %s", published_tweet_id)
            return True
        except Exception as e:
            await self.capture_failure(page, "quote_tweet")
            logger.error("Failed to quote tweet: %s", e)
            return False
        finally:
            try:
                page.remove_listener("response", _handle_quote_response)
            except Exception:
                pass

