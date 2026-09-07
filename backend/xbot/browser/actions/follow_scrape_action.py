from __future__ import annotations
import logging
import random
import re
from typing import Any
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

from xbot.browser.actions.utils import (check_target_tweet_status, _navigate_home_if_needed, _random_tab_detour, _post_action_cooldown_browse, _extract_tweet_id_from_url, human_scroll_to_tweet)

class ScrapeFollowList(BaseAction):
    """
    Scrapes the list of followers or following handles for a given user,
    with built-in detection and filtering for Verified Blue-Tick / Gold-Tick accounts.
    """

    async def execute(
        self,
        page: Page,
        username: str,
        list_type: str = "followers",
        limit: int = 100,
        verified_only: bool = False,
    ) -> list[str]:
        try:
            clean = username.lstrip("@")
            url = f"https://x.com/{clean}/{list_type}"
            logger.info("Scraping %s list for @%s (limit: %d, verified_only: %s)", list_type, clean, limit, verified_only)
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            try:
                await page.wait_for_selector("[data-testid='UserCell']", timeout=15000)
            except Exception:
                logger.warning("No UserCell selector loaded on follow list page.")
                return []

            await sleep_with_jitter(2000)

            handles = []
            seen_handles = set()
            scroll_count = 0
            max_scrolls = 20

            while len(handles) < limit and scroll_count < max_scrolls:
                cells = await page.query_selector_all("[data-testid='UserCell']")
                for cell in cells:
                    # Check verified badge
                    is_verified = bool(
                        await cell.query_selector(
                            "svg[data-testid='icon-verified'], [aria-label*='Verified'], svg[aria-label*='Verified']"
                        )
                    )

                    if verified_only and not is_verified:
                        continue

                    links = await cell.query_selector_all("a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if h and "/" not in h and h not in ["home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings"]:
                                handle = h
                                break
                    
                    if handle and handle not in seen_handles:
                        seen_handles.add(handle)
                        handles.append(handle)
                        if len(handles) >= limit:
                            break
                
                if len(handles) >= limit:
                    break

                scroll_count += 1
                await human_scroll(page, random.randint(400, 700), "down")
                await sleep_with_jitter(1500)
                
            logger.info("Scraped %d %s handles from @%s (verified_only=%s)", len(handles), list_type, clean, verified_only)
            return handles
        except Exception as e:
            await self.capture_failure(page, f"scrape_{list_type}_{username}")
            logger.error("Error scraping %s for %s: %s", list_type, username, e)
            return []

class HarvestFollowBackThread(BaseAction):
    """
    Navigates to an active follow-back / mutuals thread URL,
    analyzes the post and its comment section, and extracts high-reciprocity Blue Tick candidates.
    """

    async def execute(self, page: Page, tweet_url: str, max_candidates: int = 8) -> list[dict[str, Any]]:
        candidates = []
        try:
            logger.info("Harvesting active follow-back thread: %s", tweet_url)
            await page.goto(tweet_url, wait_until="commit", timeout=20000)
            status_check = await check_target_tweet_status(page, timeout=15000)
            if not status_check["available"]:
                logger.warning("Thread harvest target tweet unavailable: %s", status_check["reason"])
                return []
            await sleep_think_time(1000, 2500)

            # Scroll down to load thread comments
            for _ in range(2):
                await human_scroll(page, random.randint(300, 600), "down")
                await sleep_think_time(1000, 2000)

            tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
            seen_handles: set[str] = set()

            # Skip root tweet (index 0), inspect comment replies (index 1+)
            for el in tweet_elements[1:]:
                try:
                    user_el = await el.query_selector('[data-testid="User-Name"]')
                    if not user_el:
                        continue
                    u_text = await user_el.inner_text()
                    m = re.search(r"@([A-Za-z0-9_]+)", u_text)
                    if not m:
                        continue
                    handle = m.group(1)
                    if handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    # Check verified / blue tick
                    verified_el = await user_el.query_selector(
                        'svg[data-testid="icon-verified"], svg[aria-label="Verified account"], svg[aria-label="Blue tick"]'
                    )
                    is_blue_tick = verified_el is not None

                    # Comment text
                    c_text_el = await el.query_selector(SELECTORS.get("tweet_text", '[data-testid="tweetText"]'))
                    comment_body = (await c_text_el.inner_text()).strip() if c_text_el else ""

                    # Check for mutuals/f4f intent
                    f4f_intent = bool(re.search(r"(drop|f4f|follow|mutual|following|connect|back)", comment_body, re.IGNORECASE))
                    score = 90.0 if (is_blue_tick and f4f_intent) else (75.0 if is_blue_tick else (60.0 if f4f_intent else 45.0))

                    display_name = u_text.split("@")[0].strip() or handle

                    candidates.append({
                        "handle": handle,
                        "display_name": display_name,
                        "is_blue_tick": is_blue_tick,
                        "comment": comment_body[:100],
                        "source_tweet_url": tweet_url,
                        "reciprocity_score": score,
                    })
                    if len(candidates) >= max_candidates:
                        break
                except Exception:
                    continue

            logger.info("Harvested %d candidate peers from follow-back thread %s", len(candidates), tweet_url)
            return candidates
        except Exception as ex:
            logger.warning("Error harvesting follow-back thread %s: %s", tweet_url, ex)
            return []

