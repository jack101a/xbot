from __future__ import annotations
import asyncio
import logging
import random
from typing import Any
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.timing import (
    human_click,
    sleep_micro,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.post_utils import (_attach_gif_if_requested, _attach_media_files, smart_truncate_tweet_text)
from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet, check_daily_post_limit)

class ComposeThread(BaseAction):
    """
    Publishes a multi-tweet thread atomically using X's native composer 'Add Tweet' (+) button.
    Emulates realistic human typing, think time between tweets, and captures created tweet IDs.
    """

    SELECTORS = {
        "nav_post_btn": '[data-testid="SideNav_NewTweet_Button"]',
        "add_tweet_btn": (
            'div[role="dialog"] button[data-testid="addButton"], '
            'button[data-testid="addButton"], '
            'div[role="dialog"] button[aria-label="Add post"], '
            'button[aria-label="Add post"]'
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
                            logger.info("Captured thread tweet %d/%d (ID: %s)", len(captured_tweet_ids), len(clean_tweets), rest_id)
            except Exception as ex:
                logger.debug("Error parsing tweet creation response: %s", ex)

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

                # Ensure previous tweet is focused and scrolled into view so X displays the active action toolbar
                prev_ta = await page.query_selector(f'div[role="dialog"] div[data-testid="tweetTextarea_{idx-1}"]')
                if prev_ta:
                    try:
                        await prev_ta.scroll_into_view_if_needed(timeout=2000)
                        await prev_ta.focus()
                    except Exception:
                        pass
                    await sleep_micro(200, 400)

                add_btn = None
                try:
                    add_btn = await page.wait_for_selector(
                        'div[role="dialog"] button[data-testid="addButton"], div[role="dialog"] button[aria-label="Add post"]',
                        state="visible",
                        timeout=6000,
                    )
                except Exception:
                    add_btn = await page.query_selector(self.SELECTORS["add_tweet_btn"])

                if not add_btn:
                    # Scroll dialog container to bottom to expose addButton if scrolled out of view
                    try:
                        await page.evaluate('() => { const d = document.querySelector("div[role=\\"dialog\\"]"); if (d) d.scrollTop = d.scrollHeight; }')
                    except Exception:
                        pass
                    add_btn = await page.query_selector('div[role="dialog"] button[data-testid="addButton"], div[role="dialog"] button[aria-label="Add post"]')

                if not add_btn:
                    raise RuntimeError(f"Could not locate 'Add post' button (+) for tweet {idx+1}/{len(clean_tweets)}")

                logger.info("Clicking 'Add post' button to create tweet %d/%d...", idx + 1, len(clean_tweets))
                try:
                    await add_btn.click(timeout=2500)
                except Exception:
                    try:
                        await add_btn.click(force=True, timeout=2500)
                    except Exception:
                        await page.evaluate('(btn) => btn.click()', add_btn)
                await sleep_with_jitter(1000)

                # Explicitly target tweetTextarea_{idx} created by X (using state="attached" in case it is below scroll fold)
                target_el = None
                try:
                    target_el = await page.wait_for_selector(
                        f'div[role="dialog"] div[data-testid="tweetTextarea_{idx}"]',
                        state="attached",
                        timeout=8000,
                    )
                except Exception:
                    all_textboxes = await page.query_selector_all('div[role="dialog"] div[role="textbox"][data-testid^="tweetTextarea_"]')
                    if idx < len(all_textboxes):
                        target_el = all_textboxes[idx]

                if not target_el:
                    raise RuntimeError(f"Could not locate tweetTextarea_{idx} for tweet {idx+1}/{len(clean_tweets)}")

                try:
                    await target_el.scroll_into_view_if_needed(timeout=2000)
                except Exception:
                    pass
                await target_el.focus()
                await target_el.click()
                await sleep_micro(200, 400)

                for ch in tweet_text:
                    await page.keyboard.type(ch, delay=random.uniform(8, 20))
                await sleep_think_time(600, 1200)

                # Verify text was entered in target_el
                typed_check = (await target_el.inner_text()).strip()
                if not typed_check:
                    logger.warning("Tweet %d textarea appeared empty after typing; retrying with direct insert...", idx + 1)
                    await target_el.focus()
                    await page.keyboard.type(tweet_text, delay=random.uniform(4, 10))
                    await sleep_micro(300, 600)

            # 3. Verify ALL tweets in thread are populated before submitting
            filled_count = 0
            for i in range(len(clean_tweets)):
                tb = await page.query_selector(f'div[role="dialog"] div[data-testid="tweetTextarea_{i}"]')
                if tb:
                    txt = (await tb.inner_text()).strip()
                    if txt:
                        filled_count += 1
                        logger.info("Verified tweet %d/%d populated in composer: '%s...'", i + 1, len(clean_tweets), txt[:40])

            if filled_count < len(clean_tweets):
                raise RuntimeError(
                    f"Thread integrity failure: only {filled_count}/{len(clean_tweets)} tweets filled in composer. "
                    f"Aborting thread submission to prevent partial thread posting."
                )

            # 4. Submit post all: Wait for image processing/Post all button to be enabled (aria-disabled != "true")
            logger.info("All %d/%d tweets verified in composer. Submitting entire thread via 'Post all'...", filled_count, len(clean_tweets))
            enabled_submit_sel = (
                'div[role="dialog"] button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]), '
                'div[role="dialog"] button:has-text("Post all"):not([aria-disabled="true"]):not([disabled]), '
                'button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled]):has-text("Post all"), '
                'button[data-testid="tweetButton"]:not([aria-disabled="true"]):not([disabled])'
            )
            submit_btn = None
            try:
                submit_btn = await page.wait_for_selector(enabled_submit_sel, timeout=15000)
            except Exception:
                logger.warning("Enabled 'Post all' button selector timed out; checking fallback selectors...")
                for sel in ['div[role="dialog"] button[data-testid="tweetButton"]', 'button:has-text("Post all")', 'button:has-text("Post")']:
                    el = await page.query_selector(sel)
                    if el:
                        submit_btn = el
                        break

            # Save visual evidence of composer ready to submit
            try:
                await page.screenshot(path="logs/thread_ready_to_submit.png")
            except Exception:
                pass

            # Check if modal is blocked by daily limit banner before clicking
            pre_limit = await check_daily_post_limit(page)
            if pre_limit:
                await self.capture_failure(page, "x_daily_limit_reached")
                logger.critical("Aborting thread: X Daily Post Limit detected (%s)", pre_limit)
                return {
                    "status": "failed",
                    "error": f"You've hit the daily post limit on X ({pre_limit})",
                    "reason": "daily_post_limit_reached",
                    "daily_limit_reached": True,
                    "tweet_ids": [],
                }

            if submit_btn:
                try:
                    await submit_btn.click(timeout=2500)
                except Exception:
                    try:
                        await submit_btn.click(force=True, timeout=2500)
                    except Exception:
                        await page.evaluate('(btn) => btn.click()', submit_btn)

            # 5. Wait for ALL tweets in the thread to finish posting
            # Free-tier/web X posts multi-tweet threads sequentially via client-side GraphQL calls.
            # We must keep the browser alive until ALL tweets in the thread are acknowledged or modal closes!
            modal_closed = False
            total_expected = len(clean_tweets)
            max_wait_seconds = max(35, total_expected * 10)

            for sec in range(max_wait_seconds):
                await asyncio.sleep(1)

                # Check for daily limit banner in loop
                loop_limit = await check_daily_post_limit(page)
                if loop_limit:
                    await self.capture_failure(page, "x_daily_limit_reached")
                    logger.critical("Thread rejected: X Daily Post Limit banner detected (%s)", loop_limit)
                    return {
                        "status": "failed",
                        "error": f"You've hit the daily post limit on X ({loop_limit})",
                        "reason": "daily_post_limit_reached",
                        "daily_limit_reached": True,
                        "tweet_ids": captured_tweet_ids,
                    }

                # Condition A: All N tweets confirmed via CreateTweet GraphQL responses
                if len(captured_tweet_ids) >= total_expected:
                    logger.info("All %d/%d thread tweets confirmed published by X API!", len(captured_tweet_ids), total_expected)
                    modal_closed = True
                    await asyncio.sleep(3)  # Allow browser UI to settle
                    break

                # Condition B: The modal dialog has completely disappeared
                dialog_check = await page.query_selector('div[role="dialog"]')
                if not dialog_check:
                    if captured_tweet_ids:
                        logger.info("Composer modal closed after %ds (captured %d/%d tweet IDs).", sec + 1, len(captured_tweet_ids), total_expected)
                        modal_closed = True
                        await asyncio.sleep(2)
                        break
                    else:
                        # Dialog closed but response slightly delayed; wait a moment
                        await asyncio.sleep(2)
                        if captured_tweet_ids:
                            modal_closed = True
                            break

                # If after 12s no tweet response has been captured at all and dialog is still open, try click fallback
                if sec == 12 and not captured_tweet_ids and dialog_check and submit_btn:
                    logger.warning("No tweets captured after 12s; trying JS click fallback on 'Post all'...")
                    try:
                        await page.evaluate('(btn) => btn.click()', submit_btn)
                    except Exception:
                        pass

            try:
                await page.screenshot(path="logs/thread_after_submit.png")
            except Exception:
                pass

            root_id = captured_tweet_ids[0] if captured_tweet_ids else None
            dialog_still_open = await page.query_selector('div[role="dialog"]')
            toast = await page.query_selector('[data-testid="toast"]')

            if not modal_closed and dialog_still_open and not root_id and not toast:
                final_limit = await check_daily_post_limit(page)
                if final_limit:
                    await self.capture_failure(page, "x_daily_limit_reached")
                    return {
                        "status": "failed",
                        "error": f"You've hit the daily post limit on X ({final_limit})",
                        "reason": "daily_post_limit_reached",
                        "daily_limit_reached": True,
                        "tweet_ids": [],
                    }
                await self.capture_failure(page, "compose_thread_stuck")
                logger.error("Thread modal remained open without tweet creation event.")
                return {"status": "failed", "error": "Thread submission failed on X.", "tweet_ids": []}

            logger.info("Thread published successfully. Root ID: %s, Total tweets captured: %d/%d", root_id, len(captured_tweet_ids), len(clean_tweets))
            return {
                "status": "success",
                "tweet_id": root_id,
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

