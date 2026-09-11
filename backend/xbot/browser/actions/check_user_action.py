"""
Browser action for checking a user's profile and extracting their latest tweet.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import ElementHandle, Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import sleep_with_jitter

logger = logging.getLogger(__name__)


def _extract_tweet_id_from_url(url: str) -> str | None:
    """Extract numeric tweet ID from a tweet URL."""
    try:
        match = re.search(r"/status/(\d+)", url)
        if match:
            return match.group(1)
        parts = urlparse(url).path.strip("/").split("/")
        if "status" in parts:
            idx = parts.index("status")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except Exception:
        pass
    return None


def _is_tweet_fresh(created_at_str: str | None, max_age_minutes: int = 60) -> bool:
    """Returns True if the tweet was posted within max_age_minutes."""
    if not created_at_str:
        return True
    try:
        from datetime import datetime, timezone
        clean_str = created_at_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        now_dt = datetime.now(timezone.utc)
        diff_minutes = (now_dt - dt).total_seconds() / 60.0
        return diff_minutes <= max_age_minutes
    except Exception:
        pass

    try:
        s = created_at_str.strip().lower()
        if s.endswith("s"):
            return True
        if s.endswith("m"):
            mins = int(s[:-1])
            return mins <= max_age_minutes
        if s.endswith("h"):
            hours = int(s[:-1])
            return (hours * 60) <= max_age_minutes
        if s.endswith("d"):
            return False
    except Exception:
        pass
    return True


class CheckUserLatestTweet(BaseAction):
    """
    Navigates to a user's profile and extracts their latest tweet.
    Strictly skips pinned tweets and enforces max_age_minutes freshness.
    """

    async def _is_pinned(self, tweet_el: ElementHandle) -> bool:
        """Determines if a tweet element is a pinned tweet."""
        try:
            # Check socialContext element (standard X pinned badge)
            social_ctx = await tweet_el.query_selector('[data-testid="socialContext"]')
            if social_ctx:
                text = (await social_ctx.inner_text()).lower()
                if "pinned" in text:
                    return True

            # Check for pin icon / testid
            pin_el = await tweet_el.query_selector(
                '[data-testid="pin"], svg[data-testid="icon-pin"]'
            )
            if pin_el:
                return True

            # Check text in the top of the tweet container
            raw_text = await tweet_el.inner_text()
            first_lines = [
                line.strip().lower()
                for line in raw_text.split("\n")[:3]
                if line.strip()
            ]
            for line in first_lines:
                if line == "pinned" or "pinned post" in line or "pinned tweet" in line:
                    return True
        except Exception as e:
            logger.debug("Error checking pinned status: %s", e)
        return False

    async def _extract_tweet_dict(
        self,
        tweet_el: ElementHandle,
        clean_handle: str,
        base_url: str,
        is_pinned: bool,
    ) -> dict[str, Any]:
        """Extracts structured tweet dictionary from an ElementHandle."""
        text_sel = SELECTORS.get("tweet_text", '[data-testid="tweetText"]')
        text_el = await tweet_el.query_selector(text_sel)
        text = (await text_el.inner_text()).strip() if text_el else ""

        link_el = await tweet_el.query_selector("a[href*='/status/']")
        url = ""
        tweet_id = ""
        if link_el:
            href = await link_el.get_attribute("href")
            if href:
                if href.startswith("http://") or href.startswith("https://"):
                    url = href
                else:
                    url = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
                tweet_id = _extract_tweet_id_from_url(url) or ""

        time_el = await tweet_el.query_selector("time")
        created_at = None
        if time_el:
            created_at = await time_el.get_attribute("datetime")
            if not created_at:
                created_at = (await time_el.inner_text()).strip() or None

        return {
            "tweet_id": tweet_id,
            "text": text,
            "url": url,
            "handle": clean_handle,
            "is_pinned": is_pinned,
            "created_at": created_at,
        }

    async def execute(
        self,
        page: Page,
        handle: str = "",
        username: str = "",
        base_url: str = "https://x.com",
        max_age_minutes: int = 60,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """
        Navigates to a user's profile and extracts their latest fresh, unpinned tweet.
        """
        target_handle = handle or username or ""
        clean_handle = target_handle.lstrip("@").strip()
        if not clean_handle:
            logger.error("Empty handle provided to CheckUserLatestTweet")
            return None

        profile_url = f"{base_url.rstrip('/')}/{clean_handle}"
        logger.info("Navigating to check latest tweet for @%s: %s (max_age=%dm)", clean_handle, profile_url, max_age_minutes)

        try:
            response = await page.goto(profile_url, wait_until="commit", timeout=20000)
            if response and response.status >= 400:
                logger.warning(
                    "Navigation to @%s returned status code %d",
                    clean_handle,
                    response.status,
                )
                return None

            tweet_sel = SELECTORS.get("tweet", '[data-testid="tweet"]')
            # Condition-based wait: retry up to 3x waiting for tweets to hydrate in X's React SPA
            tweet_elements = []
            for attempt in range(3):
                try:
                    await page.wait_for_selector(tweet_sel, timeout=7000)
                    tweet_elements = await page.query_selector_all(tweet_sel)
                    if tweet_elements:
                        logger.info("Found %d tweets on @%s (attempt %d)", len(tweet_elements), clean_handle, attempt + 1)
                        break
                except Exception:
                    pass
                if attempt < 2:
                    logger.debug("Retry %d/3 waiting for tweets on @%s with scroll hydration", attempt + 1, clean_handle)
                    await page.evaluate("window.scrollBy(0, 400)")
                    await sleep_with_jitter(2000)

            if not tweet_elements:
                logger.warning("No tweet elements found on @%s profile after 3 attempts", clean_handle)
                return None

            # Iterate through top 4 visible tweets to find first unpinned, fresh tweet
            for idx, tweet_el in enumerate(tweet_elements[:4]):
                is_pinned = await self._is_pinned(tweet_el)
                if is_pinned:
                    logger.info("Tweet %d on @%s is pinned; skipping.", idx + 1, clean_handle)
                    continue

                tweet_data = await self._extract_tweet_dict(
                    tweet_el,
                    clean_handle=clean_handle,
                    base_url=base_url,
                    is_pinned=False,
                )
                created_at = tweet_data.get("created_at")
                if not _is_tweet_fresh(created_at, max_age_minutes=max_age_minutes):
                    logger.info("Tweet %d on @%s (id=%s, created_at=%s) exceeds max_age of %dm; skipping.", idx + 1, tweet_data.get("tweet_id"), created_at, max_age_minutes)
                    continue

                logger.info(
                    "Successfully extracted fresh latest tweet for @%s (tweet_id=%s, created_at=%s)",
                    clean_handle,
                    tweet_data.get("tweet_id"),
                    created_at,
                )
                return tweet_data

            logger.info("No unpinned tweets within max_age %dm found for @%s.", max_age_minutes, clean_handle)
            return None

        except Exception as e:
            await self.capture_failure(page, f"check_user_{clean_handle}")
            logger.error("Failed to extract latest tweet for @%s: %s", clean_handle, e)
            return None
