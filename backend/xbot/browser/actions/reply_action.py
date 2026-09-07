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
        captured_tweet_ids: list[str] = []

        async def _handle_reply_response(response: Any) -> None:
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

        page.on("response", _handle_reply_response)

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

            enabled_submit_sel = (
                '[data-testid="tweetButtonInline"]:not([aria-disabled="true"]):not([disabled]), '
                '[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                'button[data-testid*="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                '[data-testid="tweetButtonInline"], [data-testid="tweetButton"], button[data-testid*="tweetButton"]'
            )
            submit_btn = None
            try:
                submit_btn = await page.wait_for_selector(enabled_submit_sel, timeout=8000)
            except Exception:
                pass

            # Submit via direct DOM click to ensure submission through overlays
            if submit_btn:
                logger.info("Clicking reply submit button...")
                try:
                    await submit_btn.click(timeout=2500)
                except Exception:
                    try:
                        await submit_btn.click(force=True, timeout=2500)
                    except Exception:
                        await page.evaluate('(btn) => btn.click()', submit_btn)
            await sleep_with_jitter(1500)

            # Verification 1: If reply textarea or modal is still visible, try direct click and shortcuts
            reply_check = await page.query_selector(textarea_sel)
            if reply_check and await reply_check.is_visible():
                logger.info("Reply box still open; attempting fallback shortcuts...")
                if submit_btn:
                    try:
                        await submit_btn.click(force=True)
                    except Exception:
                        try:
                            await page.evaluate('(btn) => btn.click()', submit_btn)
                        except Exception:
                            pass
                try:
                    await reply_check.focus()
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
                    logger.error("Reply rejected by X with toast: %s", toast_text)
                    return False
                if "your post was sent" in toast_text.lower() or "your reply was sent" in toast_text.lower():
                    logger.info("Confirmed success toast on X: %s", toast_text)

            # Verification 3: Wait for reply modal/textarea to close/clear
            try:
                await page.wait_for_selector(textarea_sel, state="hidden", timeout=10000)
            except Exception:
                pass

            # If on live X and textarea is still visible and no tweet captured, fail
            if "x.com" in getattr(page, "url", ""):
                reply_check = await page.query_selector(textarea_sel)
                if reply_check and await reply_check.is_visible() and not captured_tweet_ids:
                    logger.error("Reply composer still open on live X and no tweet captured; aborting false success.")
                    return False

            await sleep_with_jitter(2000)
            await _post_action_cooldown_browse(page, scrolls=random.randint(1, 2))

            published_reply_id = captured_tweet_ids[0] if captured_tweet_ids else None
            logger.info("Reply submitted successfully. Tweet ID: %s", published_reply_id)
            return True
        except Exception as e:
            await self.capture_failure(page, "reply_tweet")
            logger.error("Failed to reply to tweet: %s", e)
            return False
        finally:
            try:
                page.remove_listener("response", _handle_reply_response)
            except Exception:
                pass


# Re-export QuoteTweet from quote_action for canonical definition and backward compatibility
from xbot.browser.actions.quote_action import QuoteTweet

