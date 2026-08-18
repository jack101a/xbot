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


class CheckUserLatestTweet(BaseAction):
    """
    Navigates to a user's profile and extracts their latest tweet.
    Handles pinned tweets by falling back to the next tweet if available.
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
        handle: str,
        base_url: str = "https://x.com",
        max_age_minutes: int = 30,
    ) -> dict[str, Any] | None:
        """
        Navigates to a user's profile and extracts their latest tweet.
        Handles pinned tweets by falling back to the next tweet if available.
        Returns a dict:
        {
            "tweet_id": str,
            "text": str,
            "url": str,
            "handle": str,
            "is_pinned": bool,
            "created_at": str | None,
        }
        or None if no tweet is found or navigation fails.
        """
        clean_handle = handle.lstrip("@").strip()
        if not clean_handle:
            logger.error("Empty handle provided to CheckUserLatestTweet")
            return None

        profile_url = f"{base_url.rstrip('/')}/{clean_handle}"
        logger.info("Navigating to check latest tweet for @%s: %s", clean_handle, profile_url)

        try:
            response = await page.goto(profile_url, wait_until="domcontentloaded", timeout=15000)
            if response and response.status >= 400:
                logger.warning(
                    "Navigation to @%s returned status code %d",
                    clean_handle,
                    response.status,
                )
                return None

            await sleep_with_jitter(1000)

            tweet_sel = SELECTORS.get("tweet", '[data-testid="tweet"]')
            try:
                await page.wait_for_selector(tweet_sel, timeout=8000)
            except Exception:
                logger.warning("No tweet elements found on @%s profile within timeout", clean_handle)
                return None

            tweet_elements = await page.query_selector_all(tweet_sel)
            if not tweet_elements:
                logger.warning("No tweets found for user @%s", clean_handle)
                return None

            first_tweet = tweet_elements[0]
            first_is_pinned = await self._is_pinned(first_tweet)

            if first_is_pinned and len(tweet_elements) > 1:
                logger.info("First tweet is pinned; falling back to second tweet for @%s", clean_handle)
                target_tweet = tweet_elements[1]
                target_is_pinned = await self._is_pinned(target_tweet)
            else:
                target_tweet = first_tweet
                target_is_pinned = first_is_pinned

            tweet_data = await self._extract_tweet_dict(
                target_tweet,
                clean_handle=clean_handle,
                base_url=base_url,
                is_pinned=target_is_pinned,
            )

            logger.info(
                "Successfully extracted latest tweet for @%s (tweet_id=%s, pinned=%s)",
                clean_handle,
                tweet_data.get("tweet_id"),
                tweet_data.get("is_pinned"),
            )
            return tweet_data

        except Exception as e:
            await self.capture_failure(page, f"check_user_{clean_handle}")
            logger.error("Failed to extract latest tweet for @%s: %s", clean_handle, e)
            return None
