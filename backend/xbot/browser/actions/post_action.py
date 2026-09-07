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
        captured_tweet_ids: list[str] = []

        async def _handle_post_response(response: Any) -> None:
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

        page.on("response", _handle_post_response)

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

            # 1. Check if composer textarea is already visible on the current page.
            # If currently on a specific tweet/status URL, we MUST navigate to home or compose
            # because any textarea on /status/ is a reply box, not the main feed composer.
            current_url = getattr(page, "url", "")
            is_on_status_page = "/status/" in current_url or not current_url.startswith("https://x.com")

            textarea_el = None
            is_visible = False
            if not is_on_status_page:
                textarea_el = await page.query_selector(textarea_sel)
                if textarea_el:
                    try:
                        is_visible = await textarea_el.is_visible()
                    except Exception:
                        is_visible = False

            # 2. If not visible or on status page, ensure we navigate to home or click compose button
            if not is_visible or is_on_status_page:
                if is_on_status_page or "x.com" not in current_url:
                    logger.info("Navigating to https://x.com/home to open top-level composer...")
                    await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                    await sleep_think_time(3000, 5000)

                # Check for X reload/retry banner
                try_again_btn = await page.query_selector('button:has-text("Try again"), div[role="button"]:has-text("Try again"), span:has-text("Try again")')
                if try_again_btn:
                    logger.info("Detected 'Try again' prompt on X. Clicking retry button...")
                    await human_click(page, try_again_btn, 200, 500)
                    await sleep_think_time(3000, 5000)

                # Check if composer appeared after navigating home
                textarea_el = await page.query_selector(textarea_sel)
                if textarea_el:
                    try:
                        is_visible = await textarea_el.is_visible()
                    except Exception:
                        is_visible = False

                if not is_visible:
                    # Click sidebar compose button
                    side_nav_btn = await page.query_selector('a[href="/compose/post"], a[href="/compose/tweet"], [data-testid="SideNav_NewTweet_Button"]')
                    if side_nav_btn:
                        logger.info("Clicking SideNav compose post button...")
                        await human_click(page, side_nav_btn, 300, 700)
                        await sleep_think_time(1500, 2500)
                    else:
                        logger.info("Navigating to https://x.com/compose/post to open composer...")
                        await page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=30000)
                        await sleep_think_time(2000, 3500)

            # 3. Wait for composer textarea
            textarea_el = await page.wait_for_selector(textarea_sel, timeout=30000)
            if not textarea_el:
                raise RuntimeError("Could not locate tweet composer textarea")

            # Click textarea to focus
            await human_click(page, textarea_el, 200, 500)
            await sleep_think_time(600, 1200)

            # Type text via human_type if text is provided
            if text:
                from xbot.browser.timing import human_type
                await human_type(page, textarea_sel, text)
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
                try:
                    await submit_btn.click(timeout=2500)
                except Exception:
                    try:
                        await submit_btn.click(force=True, timeout=2500)
                    except Exception:
                        await page.evaluate('(btn) => btn.click()', submit_btn)
                await sleep_with_jitter(2000)

            # Verification 1: If composer is still visible, try direct click and keyboard shortcuts
            composer_check = await page.query_selector(textarea_sel)
            if composer_check and await composer_check.is_visible():
                logger.info("Composer modal still open; attempting fallback direct click and shortcuts...")
                if submit_btn:
                    try:
                        await submit_btn.click(force=True)
                    except Exception:
                        try:
                            await page.evaluate('(btn) => btn.click()', submit_btn)
                        except Exception:
                            pass
                await sleep_with_jitter(1000)

                if composer_check and await composer_check.is_visible():
                    try:
                        await composer_check.focus()
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
                    logger.error("Post rejected by X with toast: %s", toast_text)
                    return False
                if "your post was sent" in toast_text.lower():
                    logger.info("Confirmed success toast on X: %s", toast_text)

            # Final check: Wait for composer modal / textarea to close
            try:
                await page.wait_for_selector(textarea_sel, state="hidden", timeout=12000)
                logger.info("Post published and composer closed successfully.")
            except Exception:
                # If home timeline composer or already submitted
                logger.info("Composer closed or post submitted on timeline.")

            # If on live X and composer is still visible and no tweet captured, fail
            if "x.com" in getattr(page, "url", ""):
                composer_check = await page.query_selector(textarea_sel)
                if composer_check and await composer_check.is_visible() and not captured_tweet_ids:
                    logger.error("Post composer still open on live X and no tweet captured; aborting false success.")
                    return False

            published_tweet_id = captured_tweet_ids[0] if captured_tweet_ids else None
            logger.info("Post published successfully. Tweet ID: %s", published_tweet_id)
            return {
                "status": "success",
                "posted": True,
                "tweet_id": published_tweet_id,
            }
        except Exception as e:
            await self.capture_failure(page, "compose_post")
            logger.error("Failed to compose post: %s", e)
            return False
        finally:
            try:
                page.remove_listener("response", _handle_post_response)
            except Exception:
                pass
