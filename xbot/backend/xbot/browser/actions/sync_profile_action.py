"""
Browser action for synchronizing X profile data and verifying session authentication.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from playwright.async_api import Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.timing import sleep_with_jitter

logger = logging.getLogger(__name__)


def _parse_count(text: str) -> int:
    """Parses abbreviation numbers (e.g. 1.2M, 15.4K, 1,234) into integers."""
    if not text:
        return 0
    clean = text.strip().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KkMmBb])?", clean)
    if not match:
        return 0
    num_str, suffix = match.groups()
    try:
        val = float(num_str)
        if suffix:
            s = suffix.upper()
            if s == "K":
                val *= 1_000
            elif s == "M":
                val *= 1_000_000
            elif s == "B":
                val *= 1_000_000_000
        return int(val)
    except Exception:
        return 0


def _upgrade_avatar_url(url: str) -> str:
    """Upgrades X avatar thumbnail URL to high-resolution 400x400."""
    if not url:
        return ""
    return re.sub(
        r"_(normal|200x200|bigger|mini|x96|reasonably_small)(?=\.[a-zA-Z0-9]+(?:\?|$))",
        "_400x400",
        url,
    )


class SyncProfileFromX(BaseAction):
    """
    Navigates to an X profile and extracts user information, metrics,
    and session authentication health status.
    """

    async def _extract_count_from_selector(self, page: Page, selector: str) -> int:
        """Helper to find and parse count numbers from matching elements or child spans."""
        try:
            el = await page.query_selector(selector)
            if not el:
                return 0
            spans = await el.query_selector_all("span")
            for span in spans:
                text = (await span.inner_text()).strip()
                if not text:
                    continue
                # If text is a count
                count = _parse_count(text)
                if count > 0 or text == "0":
                    return count
            full_text = (await el.inner_text()).strip()
            return _parse_count(full_text)
        except Exception:
            return 0

    async def execute(
        self,
        page: Page,
        username: str,
        base_url: str = "https://x.com",
    ) -> dict[str, Any]:
        """
        Navigates to the user's profile and extracts metrics, avatar, and authentication state.

        Returns:
            dict with keys:
                - status: 'authenticated' | 'logged_out' | 'challenged' | 'failed'
                - is_authenticated: bool
                - handle: str
                - display_name: str
                - avatar_url: str
                - followers_count: int
                - following_count: int
                - bio: str
                - is_verified: bool
        """
        clean_username = username.strip().lstrip("@").strip()
        if not clean_username:
            logger.error("Empty username provided to SyncProfileFromX")
            return {
                "status": "failed",
                "is_authenticated": False,
                "handle": "",
                "display_name": "",
                "avatar_url": "",
                "followers_count": 0,
                "following_count": 0,
                "bio": "",
                "is_verified": False,
            }

        profile_url = f"{base_url.rstrip('/')}/{clean_username}"
        logger.info("Syncing profile from X for @%s: %s", clean_username, profile_url)

        try:
            response = await page.goto(profile_url, wait_until="domcontentloaded", timeout=15000)
            if response and response.status >= 400:
                logger.warning(
                    "Navigation to @%s returned HTTP status %d",
                    clean_username,
                    response.status,
                )
                await self.capture_failure(page, f"sync_profile_{clean_username}")
                return {
                    "status": "failed",
                    "is_authenticated": False,
                    "handle": clean_username,
                    "display_name": "",
                    "avatar_url": "",
                    "followers_count": 0,
                    "following_count": 0,
                    "bio": "",
                    "is_verified": False,
                }

            await sleep_with_jitter(1000)

            current_url = page.url.lower()

            # 1. Detect Challenge / Lock screens
            is_challenged = (
                "/account/access" in current_url
                or "/login_verification" in current_url
                or "/account/suspended" in current_url
                or "/i/flow/challenge" in current_url
            )
            if not is_challenged:
                challenge_el = await page.query_selector(
                    '[data-testid="challenge"], [data-testid="confirmation_code"], #challenge-container, input[name="challenge_response"]'
                )
                if challenge_el:
                    is_challenged = True

            if is_challenged:
                logger.warning("X session challenge detected for @%s at %s", clean_username, current_url)
                return {
                    "status": "challenged",
                    "is_authenticated": False,
                    "handle": clean_username,
                    "display_name": "",
                    "avatar_url": "",
                    "followers_count": 0,
                    "following_count": 0,
                    "bio": "",
                    "is_verified": False,
                }

            # 2. Detect Authentication Status
            auth_indicator = await page.query_selector(
                '[data-testid="SideNav_AccountSwitcher_Button"], '
                '[data-testid="AppTabBar_Profile_Link"], '
                '[data-testid="SideNav_NewTweet_Button"]'
            )
            is_authenticated = auth_indicator is not None
            status = "authenticated" if is_authenticated else "logged_out"

            # 3. Extract Avatar URL
            avatar_url = ""
            avatar_el = await page.query_selector(
                '[data-testid="UserAvatar-Container-profileUser"] img, '
                '[data-testid="primaryColumn"] img[src*="pbs.twimg.com/profile_images"], '
                'img[src*="pbs.twimg.com/profile_images"]'
            )
            if avatar_el:
                raw_src = await avatar_el.get_attribute("src")
                if raw_src:
                    avatar_url = _upgrade_avatar_url(raw_src)

            # 4. Extract Display Name
            display_name = clean_username
            user_name_el = await page.query_selector('[data-testid="UserName"]')
            if user_name_el:
                user_name_text = await user_name_el.inner_text()
                lines = [ln.strip() for ln in user_name_text.split("\n") if ln.strip()]
                # Find first line not starting with '@'
                for line in lines:
                    if not line.startswith("@"):
                        display_name = line
                        break

            # 5. Extract Bio / Description
            bio = ""
            bio_el = await page.query_selector('[data-testid="UserDescription"]')
            if bio_el:
                bio = (await bio_el.inner_text()).strip()

            # 6. Extract Verified Badge
            is_verified = False
            verified_badge = await page.query_selector(
                '[data-testid="UserName"] svg[data-testid="icon-verified"], '
                '[data-testid="UserName"] [aria-label*="Verified" i], '
                'svg[data-testid="icon-verified"], '
                '[data-testid*="verified"]'
            )
            if verified_badge:
                is_verified = True

            # 7. Extract Following Count
            following_count = await self._extract_count_from_selector(
                page,
                f"a[href='/{clean_username}/following'], a[href$='/following']",
            )

            # 8. Extract Followers Count
            followers_count = await self._extract_count_from_selector(
                page,
                f"a[href='/{clean_username}/verified_followers'], a[href='/{clean_username}/followers'], a[href$='/verified_followers'], a[href$='/followers']",
            )

            logger.info(
                "Profile sync for @%s completed: status=%s, followers=%d, following=%d, verified=%s",
                clean_username,
                status,
                followers_count,
                following_count,
                is_verified,
            )

            return {
                "status": status,
                "is_authenticated": is_authenticated,
                "handle": clean_username,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "followers_count": followers_count,
                "following_count": following_count,
                "bio": bio,
                "is_verified": is_verified,
            }

        except Exception as e:
            await self.capture_failure(page, f"sync_profile_{clean_username}")
            logger.error("Failed to sync profile for @%s: %s", clean_username, e)
            return {
                "status": "failed",
                "is_authenticated": False,
                "handle": clean_username,
                "display_name": "",
                "avatar_url": "",
                "followers_count": 0,
                "following_count": 0,
                "bio": "",
                "is_verified": False,
            }
