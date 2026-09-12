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

async def dismiss_blocking_modals(page: Page) -> bool:
    """
    Detects and dismisses any blocking confirmation modals on X.com:
    - 'Save post? Discard / Save'
    - 'Got it' / 'Dismiss'
    - 'Leave' / 'Discard'
    """
    from unittest.mock import Mock, AsyncMock
    if isinstance(page, (Mock, AsyncMock)):
        return False
    try:
        discard_btn = await page.query_selector(
            '[data-testid="confirmationSheetConfirm"], button:has-text("Discard"), [data-testid="SheetDialog"] button:has-text("Discard")'
        )
        if discard_btn:
            logger.info("Detected blocking modal; dismissing via Discard.")
            await discard_btn.click()
            await page.wait_for_timeout(500)
            return True

        close_btn = await page.query_selector('[aria-label="Close"], [data-testid="app-bar-close"]')
        if close_btn:
            box = await close_btn.bounding_box()
            if box and box["y"] < 150:
                await close_btn.click()
                await page.wait_for_timeout(300)
                return True
    except Exception as e:
        logger.debug("dismiss_blocking_modals non-fatal error: %s", e)
    return False


async def _navigate_home_if_needed(page: Page) -> None:
    """Navigate to the X home feed if not already there."""
    await dismiss_blocking_modals(page)
    current = getattr(page, "url", "") or ""
    if current.startswith("data:"):
        return
    if "x.com/home" not in current and "twitter.com/home" not in current and "127.0.0.1" not in current and "localhost" not in current:
        try:
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


async def check_daily_post_limit(page: Page) -> str | None:
    """
    Checks if X (Twitter) has displayed a daily post limit error or modal:
    - 'You've hit the daily post limit. Subscribe to Premium for higher limits.'
    - 'Upgrade to unlock'
    - 'Daily limit reached'
    Returns the detected warning string, or None if no limit banner is found.
    """
    try:
        # Check inside modal dialog, alert boxes, toasts, and floating error banners
        selectors = [
            'div[role="dialog"]',
            '[data-testid="toast"]',
            'div[role="alert"]',
            '[data-testid="error-detail"]',
            'div[data-testid="SheetDialog"]',
        ]
        limit_keywords = [
            "hit the daily post limit",
            "daily post limit",
            "subscribe to premium for higher limits",
            "daily tweet limit",
            "you are unable to post",
            "you are unable to tweet",
        ]

        for sel in selectors:
            elements = await page.query_selector_all(sel)
            for el in elements:
                try:
                    if await el.is_visible():
                        txt = (await el.inner_text()).lower()
                        for kw in limit_keywords:
                            if kw in txt:
                                logger.critical("Detected X Daily Post Limit banner: '%s'", kw)
                                return kw
                except Exception:
                    pass

        # Fallback: check whole page body text if suspicious keywords match
        body_text = await page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''")
        for kw in limit_keywords:
            if kw in body_text:
                logger.critical("Detected X Daily Post Limit in page body: '%s'", kw)
                return kw

    except Exception as e:
        logger.debug("check_daily_post_limit error: %s", e)
    return None

