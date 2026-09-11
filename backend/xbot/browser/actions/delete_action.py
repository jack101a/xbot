from __future__ import annotations

import logging
import re
from typing import Any
from playwright.async_api import Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_click,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)


class DeleteTweet(BaseAction):
    """
    Automates deleting an author's own tweet on X (Twitter).
    Navigates to the tweet URL, opens the caret menu, clicks Delete, and confirms deletion.
    """

    async def execute(
        self,
        page: Page,
        tweet_url: str | None = None,
        tweet_id: str | None = None,
        username: str | None = None,
    ) -> dict[str, Any]:
        try:
            target_url = tweet_url
            if not target_url and tweet_id:
                clean_user = (username or "i").lstrip("@")
                target_url = f"https://x.com/{clean_user}/status/{tweet_id}"

            if not target_url:
                logger.error("DeleteTweet: Neither tweet_url nor tweet_id was provided.")
                return {"status": "failed", "error": "missing_target_url", "deleted": False}

            logger.info("DeleteTweet: Navigating to %s for deletion", target_url)
            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            await sleep_with_jitter(2000)

            # 1. Locate tweet article (specifically matching user handle or tweet_id if present)
            clean_user = (username or "").lstrip("@").strip().lower()
            target_t_id = tweet_id or (target_url.split("/status/")[-1].split("?")[0] if "/status/" in target_url else "")
            
            target_article = None
            try:
                await page.wait_for_selector("[data-testid='tweet']", timeout=12000)
                articles = await page.query_selector_all("[data-testid='tweet']")
                for art in articles:
                    # Check if tweet has link to target status id
                    if target_t_id:
                        link_match = await art.query_selector(f"a[href*='/status/{target_t_id}']")
                        if link_match:
                            target_article = art
                            break
                    # Check if user matches
                    if clean_user:
                        u_el = await art.query_selector("[data-testid='User-Name']")
                        u_text = (await u_el.inner_text()).lower() if u_el else ""
                        if f"@{clean_user}" in u_text or clean_user in u_text:
                            target_article = art
                            break
                if not target_article and articles:
                    target_article = articles[-1] if len(articles) > 1 else articles[0]
            except Exception as e:
                logger.debug("Error finding target tweet article for deletion: %s", e)
                target_article = None

            if not target_article:
                logger.warning("DeleteTweet: Target tweet article not found at %s", target_url)
                return {"status": "failed", "error": "tweet_not_found", "deleted": False}

            # 2. Click the Caret menu button
            try:
                caret_btn = await target_article.wait_for_selector(
                    "[data-testid='caret'], button[aria-label='More'], button[aria-label='More actions']",
                    timeout=5000,
                )
            except Exception:
                caret_btn = await page.query_selector(
                    "[data-testid='caret'], button[aria-label='More'], button[aria-label='More actions']"
                )

            if not caret_btn:
                logger.warning("DeleteTweet: Caret menu button not found on tweet at %s", target_url)
                return {"status": "failed", "error": "caret_button_not_found", "deleted": False}

            await human_click(page, caret_btn)
            await sleep_with_jitter(1000)

            # 3. Click Delete in the dropdown menu
            try:
                delete_menu_item = await page.wait_for_selector(
                    "[role='menuitem']:has-text('Delete'), [data-testid='Dropdown'] span:has-text('Delete')",
                    timeout=6000,
                )
            except Exception:
                delete_menu_item = None

            if not delete_menu_item:
                logger.warning("DeleteTweet: 'Delete' option not found in dropdown menu for %s", target_url)
                return {"status": "failed", "error": "delete_menu_item_not_found", "deleted": False}

            await human_click(page, delete_menu_item)
            await sleep_with_jitter(1000)

            # 4. Confirm in the modal dialog
            confirm_btn = await page.wait_for_selector(
                "[data-testid='confirmationSheetConfirm'], button[data-testid='confirmationSheetConfirm']",
                timeout=10000,
            )
            if not confirm_btn:
                logger.warning("DeleteTweet: Confirmation modal button not found for %s", target_url)
                return {"status": "failed", "error": "confirm_button_not_found", "deleted": False}

            await human_click(page, confirm_btn)
            await sleep_with_jitter(2000)

            logger.info("DeleteTweet: Successfully deleted tweet %s", target_url)
            parsed_id = tweet_id
            if not parsed_id and "/status/" in target_url:
                m = re.search(r"/status/(\d+)", target_url)
                if m:
                    parsed_id = m.group(1)

            return {
                "status": "success",
                "deleted": True,
                "tweet_url": target_url,
                "tweet_id": parsed_id,
            }

        except Exception as e:
            logger.error("DeleteTweet: Exception deleting tweet at %s: %s", tweet_url, e, exc_info=True)
            return {"status": "error", "error": str(e), "deleted": False}
