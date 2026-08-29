from __future__ import annotations
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
from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

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

