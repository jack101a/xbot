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
    with built-in detection for Verified Blue-Tick accounts and direct
    DOM detection of unreciprocated 'Follow back' relationships.
    """

    async def execute(
        self,
        page: Page,
        username: str,
        list_type: str = "followers",
        limit: int = 100,
        verified_only: bool = False,
        unreciprocated_only: bool = False,
        return_details: bool = False,
    ) -> list[str] | dict[str, Any]:
        try:
            clean = username.lstrip("@")
            actual_tab = "followers" if list_type in ("followers", "followers_unreciprocated") else list_type
            if list_type == "followers_unreciprocated":
                unreciprocated_only = True

            url = f"https://x.com/{clean}/{actual_tab}"
            logger.info(
                "Scraping %s list for @%s (url=%s, limit=%d, verified_only=%s, unreciprocated_only=%s)",
                list_type, clean, url, limit, verified_only, unreciprocated_only,
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)

            try:
                await page.wait_for_selector("[data-testid='UserCell']", timeout=15000)
            except Exception:
                logger.warning("No UserCell selector loaded on %s page.", url)
                if return_details:
                    return {
                        "handles": [],
                        "unreciprocated_handles": [],
                        "verified_unreciprocated_handles": [],
                        "following_handles": [],
                        "total_scanned": 0,
                    }
                return []

            await sleep_with_jitter(2000)

            handles: list[str] = []
            unreciprocated_handles: list[str] = []
            verified_unreciprocated_handles: list[str] = []
            following_handles: list[str] = []
            seen_handles: set[str] = set()

            scroll_count = 0
            max_scrolls = max(15, limit // 5)
            stagnant_scrolls = 0

            while scroll_count < max_scrolls:
                # Query cells specifically within primaryColumn to avoid sidebar "Who to follow"
                cells = await page.query_selector_all("[data-testid='primaryColumn'] [data-testid='UserCell']")
                if not cells:
                    cells = await page.query_selector_all("[data-testid='UserCell']")

                new_found_in_scroll = 0
                for cell in cells:
                    links = await cell.query_selector_all("a[role='link'], a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if (
                                h
                                and "/" not in h
                                and h.lower() not in [
                                    "home", "explore", "notifications", "messages",
                                    "bookmarks", "lists", "profile", "settings", "i", clean.lower()
                                ]
                            ):
                                handle = h
                                break

                    if not handle or handle in seen_handles:
                        continue

                    seen_handles.add(handle)
                    new_found_in_scroll += 1

                    # 1. Verified badge check
                    is_verified = bool(
                        await cell.query_selector(
                            "svg[data-testid='icon-verified'], [aria-label*='Verified'], svg[aria-label*='Verified']"
                        )
                    )

                    # 2. Relationship button inspection in DOM
                    unfollow_btn = await cell.query_selector(
                        "button[data-testid$='-unfollow'], div[data-testid$='-unfollow']"
                    )
                    follow_btn = await cell.query_selector(
                        "button[data-testid$='-follow'], div[data-testid$='-follow']"
                    )

                    btn_text = ""
                    buttons = await cell.query_selector_all("[role='button']")
                    for b in buttons:
                        txt = (await b.inner_text()).strip()
                        if txt in ("Follow", "Follow back", "Following", "Requested", "Pending"):
                            btn_text = txt
                            break

                    is_following = bool(unfollow_btn) or ("Following" in btn_text)
                    is_unreciprocated = (
                        (bool(follow_btn) or btn_text in ("Follow back", "Follow"))
                        and not is_following
                    )

                    if is_following:
                        following_handles.append(handle)

                    if is_unreciprocated:
                        unreciprocated_handles.append(handle)
                        if is_verified:
                            verified_unreciprocated_handles.append(handle)

                    # Filter based on flags
                    if verified_only and not is_verified:
                        continue
                    if unreciprocated_only and not is_unreciprocated:
                        continue

                    handles.append(handle)

                    target_check = handles if not unreciprocated_only else unreciprocated_handles
                    if len(target_check) >= limit:
                        break

                target_check = handles if not unreciprocated_only else unreciprocated_handles
                if len(target_check) >= limit:
                    break

                if new_found_in_scroll == 0:
                    stagnant_scrolls += 1
                    if stagnant_scrolls >= 3:
                        logger.info("ScrapeFollowList: No new accounts detected for 3 scrolls. Reached bottom.")
                        break
                else:
                    stagnant_scrolls = 0

                scroll_count += 1
                await human_scroll(page, random.randint(500, 800), "down")
                await sleep_with_jitter(1500)

            logger.info(
                "ScrapeFollowList: Scraped %d %s handles from @%s (unreciprocated=%d, verified_unreciprocated=%d, following=%d, total_seen=%d)",
                len(handles), list_type, clean, len(unreciprocated_handles),
                len(verified_unreciprocated_handles), len(following_handles), len(seen_handles)
            )

            if return_details:
                return {
                    "handles": handles,
                    "unreciprocated_handles": unreciprocated_handles,
                    "verified_unreciprocated_handles": verified_unreciprocated_handles,
                    "following_handles": following_handles,
                    "total_scanned": len(seen_handles),
                }

            return handles if not unreciprocated_only else unreciprocated_handles

        except Exception as e:
            await self.capture_failure(page, f"scrape_{list_type}_{username}")
            logger.error("Error scraping %s for %s: %s", list_type, username, e)
            if return_details:
                return {
                    "handles": [],
                    "unreciprocated_handles": [],
                    "verified_unreciprocated_handles": [],
                    "following_handles": [],
                    "total_scanned": 0,
                }
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

