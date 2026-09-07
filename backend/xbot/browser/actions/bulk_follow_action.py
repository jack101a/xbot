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


class UnfollowNonFollowers(BaseAction):
    """
    Finds users the profile follows who do not follow back,
    and unfollows them up to a safe limit.
    """

    async def execute(self, page: Page, limit: int = 10) -> bool:
        try:
            # 1. Identify logged-in username
            my_username = ""
            profile_link = await page.query_selector("a[data-testid='AppTabBar_Profile_Link']")
            if profile_link:
                href = await profile_link.get_attribute("href")
                if href:
                    my_username = href.strip("/")
            
            if not my_username:
                logger.warning("Could not identify logged-in username from sidebar. Trying home navigation...")
                await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_selector("a[data-testid='AppTabBar_Profile_Link']", timeout=15000)
                profile_link = await page.query_selector("a[data-testid='AppTabBar_Profile_Link']")
                if profile_link:
                    href = await profile_link.get_attribute("href")
                    if href:
                        my_username = href.strip("/")
            
            if not my_username:
                logger.error("Failed to determine logged-in username.")
                return False

            logger.info("Unfollowing non-followers for @%s (limit: %d)", my_username, limit)
            await page.goto(f"https://x.com/{my_username}/following", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_selector("[data-testid='UserCell']", timeout=15000)
            await sleep_with_jitter(2000)

            unfollowed_count = 0
            seen_handles = set()

            # Scroll and process loop
            for scroll_attempt in range(5):
                if unfollowed_count >= limit:
                    break

                cells = await page.query_selector_all("[data-testid='UserCell']")
                logger.debug("Found %d user cells on page.", len(cells))
                
                for cell in cells:
                    if unfollowed_count >= limit:
                        break

                    # Get username handle
                    links = await cell.query_selector_all("a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if h and "/" not in h and h not in ["home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings"]:
                                handle = h
                                break
                    
                    if not handle or handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    # Check if they follow us back ("Follows you" badge)
                    follows_back = await cell.query_selector("[data-testid='userFollowIndicator']")
                    if follows_back:
                        logger.debug("@%s follows us back, skipping.", handle)
                        continue

                    # Non-follower! Locate the unfollow button
                    unfollow_btn = await cell.query_selector("[data-testid$='-unfollow']")
                    if unfollow_btn:
                        logger.info("Unfollowing non-follower: @%s", handle)
                        await human_click(page, unfollow_btn, 400, 1000)
                        
                        confirm_btn = await page.wait_for_selector("[data-testid='confirmationSheetConfirm']", timeout=5000)
                        if confirm_btn:
                            await sleep_with_jitter(1000)
                            await human_click(page, confirm_btn, 300, 800)
                        
                        unfollowed_count += 1
                        await sleep_think_time(3000, 6000)  # Human-like delay after clicking
                    
                # Scroll down to load more cells
                await human_scroll(page, random.randint(400, 700), "down")
                await sleep_with_jitter(2000)

            logger.info("Successfully unfollowed %d non-followers.", unfollowed_count)
            return True
        except Exception as e:
            await self.capture_failure(page, "unfollow_non_followers")
            logger.error("Error executing UnfollowNonFollowers: %s", e)
            return False

class FollowEngagers(BaseAction):
    """
    Navigates to a tweet URL, opens the likes/engagers list,
    and follows users up to a safe limit.
    """

    async def execute(self, page: Page, tweet_url: str, limit: int = 5) -> bool:
        try:
            if not tweet_url:
                logger.error("No tweet URL provided to FollowEngagers.")
                return False

            # Construct likes URL
            likes_url = tweet_url
            if "/likes" not in tweet_url:
                likes_url = f"{tweet_url.rstrip('/')}/likes"

            logger.info("Navigating to engagers list at %s (limit: %d)", likes_url, limit)
            await page.goto(likes_url, wait_until="domcontentloaded", timeout=20000)
            
            try:
                await page.wait_for_selector("[data-testid='UserCell']", timeout=12000)
            except Exception:
                logger.warning("No UserCell loaded for likes list. Tweet might have 0 likes or be private.")
                return False

            await sleep_with_jitter(2000)

            followed_count = 0
            seen_handles = set()

            # Scroll and process loop
            for scroll_attempt in range(5):
                if followed_count >= limit:
                    break

                cells = await page.query_selector_all("[data-testid='UserCell']")
                logger.debug("Found %d user cells on page.", len(cells))
                
                for cell in cells:
                    if followed_count >= limit:
                        break

                    # Get username handle
                    links = await cell.query_selector_all("a")
                    handle = None
                    for link in links:
                        href = await link.get_attribute("href")
                        if href:
                            h = href.strip("/")
                            if h and "/" not in h and h not in ["home", "explore", "notifications", "messages", "bookmarks", "lists", "profile", "settings"]:
                                handle = h
                                break
                    
                    if not handle or handle in seen_handles:
                        continue
                    seen_handles.add(handle)

                    # Look for follow button (ends with "-follow")
                    follow_btn = await cell.query_selector("[data-testid$='-follow']")
                    if follow_btn:
                        btn_text = await follow_btn.inner_text()
                        if "Following" in btn_text or "Pending" in btn_text:
                            continue

                        logger.info("Following engager user: @%s", handle)
                        await human_click(page, follow_btn, 400, 1000)
                        followed_count += 1
                        await sleep_think_time(3000, 6000)  # Human-like delay after following
                    
                # Scroll down slightly to load more cells
                await human_scroll(page, random.randint(300, 500), "down")
                await sleep_with_jitter(2000)

            logger.info("Successfully followed %d engagers.", followed_count)
            return True
        except Exception as e:
            await self.capture_failure(page, "follow_engagers")
            logger.error("Error executing FollowEngagers: %s", e)
            return False

