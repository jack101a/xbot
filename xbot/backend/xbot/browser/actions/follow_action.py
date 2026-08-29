from __future__ import annotations
import logging
import random
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.timing import (
    human_click,
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)


class FollowUser(BaseAction):
    """Follows a user by navigating to their profile."""

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            logger.info("Navigating to user profile to follow: %s", clean)
            await page.goto(f"https://x.com/{clean}", wait_until="commit", timeout=20000)
            
            # Wait for profile header or follow button
            try:
                await page.wait_for_selector('[data-testid="UserName"], [data-testid*="UserAvatar"], [data-testid*="follow"], h2', timeout=15000)
            except Exception:
                pass

            # Check for account suspended / non-existent banners
            err_banner = await page.query_selector('[data-testid="error-detail"], [data-testid="emptyState"]')
            if err_banner:
                txt = (await err_banner.inner_text()).lower()
                if any(w in txt for w in ("suspended", "does not exist", "blocked", "protected", "not available")):
                    logger.warning("Target user @%s unavailable: %s", clean, txt.replace("\n", " ")[:80])
                    return False

            # Human: scan profile for a moment
            await sleep_think_time(1500, 3500)
            await human_scroll(page, random.randint(100, 250), "down")
            await sleep_think_time(800, 1800)
            await human_scroll(page, random.randint(50, 150), "up")
            await sleep_think_time(600, 1500)

            # Check already-following via case-insensitive aria-label or inner text
            already_following = await page.query_selector(
                f'button[aria-label*="Following @" i], button[aria-label*="Unfollow @" i], button:has-text("Following"), button:has-text("Unfollow")'
            )
            if already_following:
                logger.info("Already following user: %s", username)
                return True

            # Follow button — try flexible case-insensitive aria-label, dynamic testids, and text
            follow_btn = await page.query_selector(f'button[aria-label*="Follow @{clean}" i]')
            if not follow_btn:
                follow_btn = await page.query_selector('button[aria-label*="Follow @" i]')
            if not follow_btn:
                follow_btn = await page.query_selector('button[data-testid*="-follow"], button[data-testid$="-follow"], [data-testid="placementTracking"]')
            if not follow_btn:
                # Text fallback
                for btn in await page.query_selector_all("button"):
                    txt = (await btn.inner_text()).strip()
                    if txt == "Follow":
                        follow_btn = btn
                        break

            if not follow_btn:
                logger.warning("Could not locate follow button for: %s", username)
                return False

            btn_text = (await follow_btn.inner_text()).strip()
            if btn_text in ("Following", "Unfollow"):
                logger.info("Already following user: %s", username)
                return True

            await human_click(page, follow_btn, 500, 1500)
            await sleep_with_jitter(2000)
            logger.info("Followed user %s successfully.", username)
            return True
        except Exception as e:
            await self.capture_failure(page, f"follow_{username}")
            logger.error("Failed to follow user %s: %s", username, e)
            return False

class UnfollowUser(BaseAction):
    """Unfollows a user."""

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            logger.info("Navigating to profile to unfollow: %s", clean)
            await page.goto(f"https://x.com/{clean}", wait_until="domcontentloaded", timeout=20000)
            try:
                await page.wait_for_selector('[data-testid="UserName"], [data-testid*="UserAvatar"], h2', timeout=12000)
            except Exception:
                pass
            await sleep_think_time(1500, 4000)

            # X uses dynamic testid e.g. '1605-unfollow' — use aria-label first, then testid
            unfollow_btn = await page.query_selector(f'button[aria-label="Following @{clean}"]')
            if not unfollow_btn:
                unfollow_btn = await page.query_selector(f'button[aria-label="Unfollow @{clean}"]')
            if not unfollow_btn:
                unfollow_btn = await page.query_selector("[data-testid$='-unfollow'], [data-testid='placementTracking']")
            if not unfollow_btn:
                # Text check
                for btn in await page.query_selector_all("button"):
                    txt = (await btn.inner_text()).strip()
                    if txt in ("Following", "Unfollow"):
                        unfollow_btn = btn
                        break

            if not unfollow_btn:
                logger.warning("Could not locate unfollow button for: %s (might not be following)", username)
                return False

            await human_click(page, unfollow_btn, 600, 1800)

            confirm_btn = await page.wait_for_selector("[data-testid='confirmationSheetConfirm']", timeout=5000)
            if confirm_btn:
                await sleep_with_jitter(1200)
                await human_click(page, confirm_btn, 300, 800)

            await sleep_with_jitter(2000)
            logger.info("Unfollowed user %s successfully.", username)
            return True
        except Exception as e:
            await self.capture_failure(page, f"unfollow_{username}")
            logger.error("Failed to unfollow user %s: %s", username, e)
            return False

class CheckProfileFollowsYou(BaseAction):
    """
    Navigates to a profile and checks if the 'Follows you' badge is present.
    """

    async def execute(self, page: Page, username: str) -> bool:
        try:
            clean = username.lstrip("@")
            await page.goto(f"https://x.com/{clean}", wait_until="domcontentloaded", timeout=15000)
            await sleep_think_time(1000, 2500)

            # Check for 'Follows you' badge
            indicator = await page.query_selector(
                '[data-testid="userFollowIndicator"], span:has-text("Follows you"), div:has-text("Follows you")'
            )
            return indicator is not None
        except Exception as e:
            logger.debug("Error checking follows-you badge for @%s: %s", username, e)
            return False

