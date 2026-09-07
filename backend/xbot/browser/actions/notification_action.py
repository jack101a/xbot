from __future__ import annotations

import logging
import random
import re
from typing import Any
from playwright.async_api import Page
from pydantic import BaseModel, Field

from xbot.browser.actions.base import BaseAction
from xbot.browser.timing import human_scroll, sleep_with_jitter

logger = logging.getLogger(__name__)


class NotificationItem(BaseModel):
    notification_type: str = Field(..., description="'reply', 'mention', 'follow', 'like', 'quote'")
    author_handle: str = Field(..., description="Handle of the user (without @)")
    author_name: str = ""
    tweet_url: str | None = None
    text: str = ""
    is_verified: bool = False


class ScrapeNotifications(BaseAction):
    """
    Navigates to https://x.com/notifications and scrapes incoming interactions:
    - New followers
    - Replies & comments on our posts
    - Mentions & Quote tweets
    """

    async def execute(
        self,
        page: Page,
        limit: int = 20,
        filter_tab: str = "all",  # "all", "verified", "mentions"
    ) -> list[dict[str, Any]]:
        target_url = "https://x.com/notifications"
        if filter_tab == "mentions":
            target_url = "https://x.com/notifications/mentions"
        elif filter_tab == "verified":
            target_url = "https://x.com/notifications/verified"

        logger.info("Navigating to %s (limit: %d)", target_url, limit)
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
            await sleep_with_jitter(2000)

            # Wait for cell/notification container
            try:
                await page.wait_for_selector("article, [data-testid='cellInnerDiv']", timeout=15000)
            except Exception:
                logger.warning("No notification cells detected on page.")
                return []

            notifications: list[NotificationItem] = []
            seen_keys: set[str] = set()
            scroll_count = 0
            max_scrolls = 5

            while len(notifications) < limit and scroll_count < max_scrolls:
                cells = await page.query_selector_all("article, [data-testid='cellInnerDiv']")
                for cell in cells:
                    cell_text = (await cell.inner_text()).strip()
                    if not cell_text:
                        continue

                    # 1. Check for follow notification
                    if "followed you" in cell_text.lower():
                        links = await cell.query_selector_all("a")
                        for l in links:
                            href = (await l.get_attribute("href") or "").strip("/")
                            if href and "/" not in href and href not in ["notifications", "home", "explore", "messages", "settings"]:
                                if href not in seen_keys:
                                    seen_keys.add(href)
                                    is_v = bool(await cell.query_selector("svg[data-testid='icon-verified'], [aria-label*='Verified']"))
                                    notifications.append(
                                        NotificationItem(
                                            notification_type="follow",
                                            author_handle=href,
                                            is_verified=is_v,
                                            text=cell_text[:120],
                                        )
                                    )
                                break
                        continue

                    # 2. Check for replies and mentions
                    article = await cell.query_selector("article")
                    target_el = article if article else cell

                    # Find tweet link
                    time_link = await target_el.query_selector("time")
                    tweet_url = None
                    if time_link:
                        parent_link = await time_link.evaluate_handle("el => el.closest('a')")
                        if parent_link:
                            href = await parent_link.get_attribute("href")
                            if href and "/status/" in href:
                                tweet_url = f"https://x.com{href}" if href.startswith("/") else href

                    # Extract author handle
                    links = await target_el.query_selector_all("a[href*='/']")
                    author_handle = ""
                    for l in links:
                        href = (await l.get_attribute("href") or "").strip("/")
                        if href and "/" not in href and href not in ["notifications", "home", "explore", "messages", "settings"]:
                            author_handle = href
                            break

                    if author_handle and tweet_url and tweet_url not in seen_keys:
                        seen_keys.add(tweet_url)
                        # Extract tweet text
                        tweet_text_el = await target_el.query_selector("[data-testid='tweetText']")
                        t_text = (await tweet_text_el.inner_text()).strip() if tweet_text_el else cell_text[:200]
                        is_v = bool(await target_el.query_selector("svg[data-testid='icon-verified'], [aria-label*='Verified']"))

                        notif_type = "reply" if ("replied" in cell_text.lower() or "/status/" in tweet_url) else "mention"

                        notifications.append(
                            NotificationItem(
                                notification_type=notif_type,
                                author_handle=author_handle,
                                tweet_url=tweet_url,
                                text=t_text,
                                is_verified=is_v,
                            )
                        )

                    if len(notifications) >= limit:
                        break

                scroll_count += 1
                await human_scroll(page, random.randint(400, 700), "down")
                await sleep_with_jitter(1200)

            logger.info("Scraped %d notifications from X", len(notifications))
            return [n.model_dump() for n in notifications]
        except Exception as e:
            logger.error("Error scraping notifications: %s", e)
            return []
