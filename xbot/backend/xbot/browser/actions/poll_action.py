from __future__ import annotations

import logging
from typing import Any

from playwright.async_api import Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_click,
    human_click_selector,
    human_type,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)


class CreatePoll(BaseAction):
    """
    Playwright action to create and publish a native X Poll.
    Supports 2 to 4 options and custom poll duration.
    """

    async def execute(
        self,
        page: Page,
        question: str,
        options: list[str],
        duration_days: int = 1,
        base_url: str = "https://x.com",
    ) -> bool:
        """
        Executes poll creation on X:
        1. Opens compose modal or navigates to {base_url}/compose/post.
        2. Types question into tweet textarea.
        3. Clicks poll button.
        4. Enters choice 1 and choice 2.
        5. If 3 or 4 options provided, adds additional choices and inputs them.
        6. Submits the poll tweet.
        """
        try:
            if not options or len(options) < 2:
                logger.error("At least 2 poll options are required to create a poll.")
                return False

            logger.info("Creating poll: '%s' with %d options", question[:40], len(options))

            # 1. Ensure compose modal is active or navigate to compose URL
            textarea = await page.query_selector(SELECTORS["tweet_textarea"])
            if not textarea:
                nav_btn = await page.query_selector(SELECTORS["nav_post_button"])
                if nav_btn:
                    await human_click(page, nav_btn, 200, 500)
                    try:
                        await page.wait_for_selector(SELECTORS["tweet_textarea"], timeout=3000)
                    except Exception:
                        await page.goto(f"{base_url.rstrip('/')}/compose/post")
                        await page.wait_for_selector(SELECTORS["tweet_textarea"], timeout=10000)
                else:
                    await page.goto(f"{base_url.rstrip('/')}/compose/post")
                    await page.wait_for_selector(SELECTORS["tweet_textarea"], timeout=10000)

            await sleep_think_time(500, 1500)

            # 2. Type question into tweet textarea
            await human_type(page, SELECTORS["tweet_textarea"], question)
            await sleep_think_time(600, 1800)

            # 3. Click poll button
            await human_click_selector(page, SELECTORS["poll_button"], 300, 700)
            await sleep_with_jitter(1000)

            # 4. Wait for choices 1 and 2
            await page.wait_for_selector(SELECTORS["poll_choice_1"], timeout=8000)
            await page.wait_for_selector(SELECTORS["poll_choice_2"], timeout=8000)

            # Type Choice 1 & 2
            await human_type(page, SELECTORS["poll_choice_1"], options[0])
            await sleep_think_time(300, 800)

            await human_type(page, SELECTORS["poll_choice_2"], options[1])
            await sleep_think_time(300, 800)

            # 5. Add Choice 3 if available
            if len(options) >= 3:
                await human_click_selector(page, SELECTORS["add_choice_button"], 300, 700)
                await page.wait_for_selector(SELECTORS["poll_choice_3"], timeout=8000)
                await human_type(page, SELECTORS["poll_choice_3"], options[2])
                await sleep_think_time(300, 800)

            # 6. Add Choice 4 if available
            if len(options) >= 4:
                await human_click_selector(page, SELECTORS["add_choice_button"], 300, 700)
                await page.wait_for_selector(SELECTORS["poll_choice_4"], timeout=8000)
                await human_type(page, SELECTORS["poll_choice_4"], options[3])
                await sleep_think_time(300, 800)

            await sleep_think_time(800, 2000)

            # 7. Submit poll
            submit_sel = SELECTORS["tweet_submit_button"]
            if await page.query_selector(SELECTORS.get("inline_tweet_submit_button", "")):
                inline_btn = await page.query_selector(SELECTORS["inline_tweet_submit_button"])
                if inline_btn and await inline_btn.is_visible():
                    submit_sel = SELECTORS["inline_tweet_submit_button"]

            await human_click_selector(page, submit_sel, 300, 700)
            await sleep_with_jitter(2500)

            logger.info("Poll created successfully.")
            return True

        except Exception as e:
            await self.capture_failure(page, "create_poll")
            logger.error("Failed to create poll: %s", e)
            return False
