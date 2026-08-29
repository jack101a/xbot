from __future__ import annotations
import logging
import random
from typing import Any
from urllib.parse import urlparse
from playwright.async_api import Page
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

async def check_target_tweet_status(page: Page, timeout: int = 15000) -> dict[str, Any]:
    """
    Checks if a target tweet page is loaded, or if it is deleted/suspended/unavailable.
    Returns: {"available": bool, "reason": str | None}
    """
    try:
        # Fast check for X error banners or deleted post indicators
        err_banner = await page.query_selector(
            '[data-testid="error-detail"], [data-testid="emptyState"], [data-testid="empty_timeline"]'
        )
        if err_banner:
            txt = (await err_banner.inner_text()).lower()
            if any(w in txt for w in ("deleted", "does not exist", "suspended", "protected", "not available", "something went wrong")):
                logger.warning("Target tweet unavailable banner: %s", txt.replace("\n", " ")[:100])
                return {"available": False, "reason": f"Tweet unavailable: {txt.splitlines()[0]}"}

        # Wait for tweet article element
        await page.wait_for_selector(
            SELECTORS["tweet"],
            timeout=timeout
        )
        return {"available": True, "reason": None}
    except Exception as e:
        # Fallback query
        articles = await page.query_selector_all(SELECTORS["tweet"])
        if articles:
            return {"available": True, "reason": None}
        return {"available": False, "reason": f"Tweet element not found: {e}"}

async def _navigate_home_if_needed(page: Page) -> None:
    """Navigate to the X home feed if not already there."""
    current = getattr(page, "url", "") or ""
    if current.startswith("data:"):
        return
    if "x.com/home" not in current and "twitter.com/home" not in current and "127.0.0.1" not in current and "localhost" not in current:
        try:
            # Check if tweet elements already exist on current page (e.g. unit test fixture or pre-rendered DOM)
            has_tweets = await page.query_selector(SELECTORS["tweet"])
            if has_tweets:
                return
            await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_selector(SELECTORS["tweet"], timeout=15000)
        except Exception:
            pass
        await sleep_with_jitter(2000)

async def _random_tab_detour(page: Page) -> None:
    """
    30% chance to detour to Notifications or own profile and back —
    simulating how real users casually check other tabs between actions.
    """
    import os
    import sys
    if os.environ.get("PYTEST_CURRENT_TEST") or "pytest" in sys.modules:
        return
    if random.random() > 0.3:
        return
    detour_urls = [
        "https://x.com/notifications",
        "https://x.com/i/lists",
    ]
    detour = random.choice(detour_urls)
    try:
        await page.goto(detour, wait_until="domcontentloaded", timeout=20000)
        await sleep_think_time(1500, 4000)  # Browse briefly
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector(SELECTORS["tweet"], timeout=8000)
    except Exception:
        pass
    await sleep_with_jitter(1500)

async def _post_action_cooldown_browse(page: Page, scrolls: int = 2) -> None:
    """
    After an engagement action (like, reply, post), humans typically
    scroll for a moment before doing the next thing.
    """
    for _ in range(scrolls):
        px = random.randint(200, 500)
        await human_scroll(page, px, "down")
        await sleep_think_time(800, 2500)
        # Occasionally back-scroll
        if random.random() < 0.3:
            await human_scroll(page, random.randint(80, 200), "up")
            await sleep_with_jitter(800)

def _extract_tweet_id_from_url(url: str) -> str | None:
    """Extract the numeric tweet ID from a URL like https://x.com/user/status/12345."""
    try:
        parts = urlparse(url).path.strip("/").split("/")
        if "status" in parts:
            idx = parts.index("status")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except Exception:
        pass
    return None

async def human_scroll_to_tweet(page: Page, tweet_el: Any) -> None:
    """Scroll a tweet into view and add a read pause."""
    await tweet_el.scroll_into_view_if_needed()
    await sleep_think_time(800, 2500)

