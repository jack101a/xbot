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
    ) -> bool | dict[str, Any]:
        import asyncio
        captured_tweet_ids: list[str] = []

        async def _handle_post_response(response: Any) -> None:
            try:
                if "CreateTweet" in response.url or "CreateDraft" in response.url:
                    if response.status == 200:
                        data = await response.json()

                        def _find_rest_id(obj: Any) -> str | None:
                            if isinstance(obj, dict):
                                if "rest_id" in obj and isinstance(obj["rest_id"], str) and obj["rest_id"]:
                                    return obj["rest_id"]
                                for v in obj.values():
                                    found = _find_rest_id(v)
                                    if found:
                                        return found
                            elif isinstance(obj, list):
                                for item in obj:
                                    found = _find_rest_id(item)
                                    if found:
                                        return found
                            return None

                        rest_id = _find_rest_id(data.get("data", {}))
                        if rest_id and rest_id not in captured_tweet_ids:
                            captured_tweet_ids.append(rest_id)
                            logger.info("Captured published tweet ID via CreateTweet GraphQL: %s", rest_id)
            except Exception:
                pass

        page.on("response", _handle_post_response)

        try:
            # Ensure text is cleanly <= 260 chars for free tier X accounts with smart boundary truncation
            if text:
                text = smart_truncate_tweet_text(text, 260)

            logger.info(
                "Composing new post (%d chars, media=%s, gif=%s): %s...",
                len(text) if text else 0,
                media_paths,
                gif_query,
                (text or "")[:40],
            )

            textarea_sel = (
                'div[role="dialog"] div[data-testid^="tweetTextarea_"], '
                'div[role="dialog"] div[role="textbox"], '
                '#compose-modal textarea, '
                'div[aria-label="Post text"], '
                'div[aria-label*="Post text"], '
                'div[role="textbox"][contenteditable="true"], '
                '.public-DraftEditor-content, '
                'div[data-testid="tweetTextarea_0"], '
                'textarea[data-testid="tweetTextarea_0"]'
            )

            # 1. Open the dedicated compose modal via SideNav or compose URL to avoid inline feed ambiguity
            current_url = getattr(page, "url", "")
            if not current_url.startswith("https://x.com") and not current_url.startswith("http://127.0.0.1"):
                logger.info("Navigating to https://x.com/home...")
                await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
                await sleep_think_time(2000, 4000)

            # Check if compose modal/dialog is already open
            modal_el = await page.query_selector('div[role="dialog"], #compose-modal')
            modal_is_open = False
            if modal_el:
                try:
                    modal_is_open = await modal_el.is_visible()
                except Exception:
                    modal_is_open = False

            if not modal_is_open:
                # Open modal via SideNav Post button
                side_nav_btn = await page.query_selector(
                    'button[data-testid="SideNav_NewTweet_Button"], '
                    'a[data-testid="SideNav_NewTweet_Button"], '
                    'a[href="/compose/post"], '
                    'a[href="/compose/tweet"], '
                    '#nav-post-btn'
                )
                if side_nav_btn:
                    logger.info("Clicking SideNav compose button to open dedicated modal...")
                    await human_click(page, side_nav_btn, 300, 700)
                    await sleep_think_time(1500, 2500)
                    modal_el = await page.query_selector('div[role="dialog"], #compose-modal')
                    if modal_el and await modal_el.is_visible():
                        modal_is_open = True
                elif "127.0.0.1" not in current_url:
                    logger.info("Navigating to https://x.com/compose/post...")
                    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=30000)
                    await sleep_think_time(2000, 3500)
                    modal_el = await page.query_selector('div[role="dialog"]')
                    if modal_el and await modal_el.is_visible():
                        modal_is_open = True

            # 2. Locate composer textarea (in modal or fallback to inline)
            textarea_el = await page.wait_for_selector(textarea_sel, state="visible", timeout=25000)
            if not textarea_el:
                raise RuntimeError("Could not locate tweet composer textarea")

            # Click textarea to focus
            await human_click(page, textarea_el, 200, 500)
            await sleep_think_time(600, 1200)

            # 3. Type text via human_type
            if text:
                from xbot.browser.timing import human_type
                await human_type(page, textarea_sel, text)
                await sleep_think_time(1000, 2000)

            # 4. Attach media files if provided
            if media_paths:
                await _attach_media_files(page, media_paths)
                await sleep_think_time(2000, 3500)

            # 5. Attach GIF if requested
            if gif_query and not media_paths:
                await _attach_gif_if_requested(page, gif_query)
                await sleep_think_time(1000, 2000)

            # 6. Locate enabled submit button strictly scoped to the modal/composer
            enabled_submit_sel = (
                'div[role="dialog"] button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                '#compose-modal button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                '#submit-post-btn, '
                '[data-testid="tweetButtonInline"]:not([aria-disabled="true"]):not([disabled]), '
                'button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled])'
            )
            submit_btn = None
            try:
                submit_btn = await page.wait_for_selector(enabled_submit_sel, timeout=30000)
            except Exception:
                logger.warning("Enabled post button selector timed out; checking fallback selectors...")
                for sel in [
                    'div[role="dialog"] button[data-testid="tweetButton"]',
                    '#compose-modal button[data-testid="tweetButton"]',
                    '#submit-post-btn',
                    '[data-testid="tweetButtonInline"]',
                    'button[data-testid="tweetButton"]',
                ]:
                    el = await page.query_selector(sel)
                    if el:
                        submit_btn = el
                        break

            if not submit_btn:
                raise RuntimeError("Could not locate post submit button")

            logger.info("Clicking enabled Post button...")
            try:
                await submit_btn.click(timeout=3000)
            except Exception:
                try:
                    await submit_btn.click(force=True, timeout=3000)
                except Exception:
                    await page.evaluate('(btn) => btn.click()', submit_btn)

            # 7. Verification Loop: Wait up to 25s for submission completion
            post_confirmed = False
            for sec in range(25):
                await asyncio.sleep(1)

                # A. Tweet ID captured from CreateTweet GraphQL network response
                if captured_tweet_ids:
                    logger.info("Confirmed tweet published via CreateTweet GraphQL (ID: %s) after %ds", captured_tweet_ids[0], sec + 1)
                    post_confirmed = True
                    break

                # B. Success toast detected
                toast = await page.query_selector('[data-testid="toast"]')
                if toast:
                    try:
                        toast_text = (await toast.inner_text()).strip()
                        if "your post was sent" in toast_text.lower():
                            logger.info("Confirmed success toast on X: %s", toast_text)
                            post_confirmed = True
                            break
                        if any(err in toast_text.lower() for err in ["wasn't sent", "something went wrong"]):
                            logger.error("Post rejected by X with toast: %s", toast_text)
                            return False
                    except Exception:
                        pass

                # C. Modal closed
                if modal_is_open:
                    d_check = await page.query_selector('div[role="dialog"], #compose-modal')
                    if not d_check or not (await d_check.is_visible()):
                        logger.info("Compose modal closed after %ds.", sec + 1)
                        post_confirmed = True
                        break
                else:
                    # Inline composer: check if text cleared
                    try:
                        cur_text = (await textarea_el.inner_text()).strip()
                        if not cur_text:
                            logger.info("Inline composer text cleared after %ds.", sec + 1)
                            post_confirmed = True
                            break
                    except Exception:
                        pass

                # Periodic retry click and shortcuts every 4s if still open
                if sec in (4, 8, 12, 16) and not post_confirmed:
                    logger.info("Post still open at %ds; re-querying active Post button and shortcuts...", sec)
                    try:
                        fresh_btn = await page.query_selector(
                            'div[role="dialog"] button[data-testid="tweetButton"], '
                            '#compose-modal button[data-testid="tweetButton"], '
                            '#submit-post-btn, '
                            '[data-testid="tweetButtonInline"], '
                            'button[data-testid="tweetButton"]'
                        )
                        if fresh_btn:
                            try:
                                await fresh_btn.click(force=True, timeout=2000)
                            except Exception:
                                await page.evaluate('(btn) => btn.click()', fresh_btn)
                    except Exception:
                        pass
                    try:
                        await textarea_el.focus()
                        await page.keyboard.press("Meta+Enter")
                        await page.keyboard.press("Control+Enter")
                    except Exception:
                        pass

            if not post_confirmed and not captured_tweet_ids:
                await self.capture_failure(page, "compose_post_timeout")
                logger.error("Post composer still open and unconfirmed after timeout.")
                return False

            published_tweet_id = captured_tweet_ids[0] if captured_tweet_ids else None
            logger.info("Post published successfully. Tweet ID: %s", published_tweet_id)
            if published_tweet_id:
                return {
                    "status": "success",
                    "posted": True,
                    "tweet_id": published_tweet_id,
                }
            return True
        except Exception as e:
            await self.capture_failure(page, "compose_post")
            logger.error("Failed to compose post: %s", e)
            return False
        finally:
            try:
                page.remove_listener("response", _handle_post_response)
            except Exception:
                pass
