"""
Browser action for synchronizing X profile data and verifying session authentication.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from playwright.async_api import Page

from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.profile_dom_parser import (
    extract_count_from_selector,
    parse_count,
    upgrade_avatar_url,
)
from xbot.browser.timing import sleep_with_jitter

logger = logging.getLogger(__name__)


class SyncProfileFromX(BaseAction):
    """
    Navigates to an X profile and extracts user information, metrics,
    and session authentication health status.
    """

    async def _extract_count_from_selector(self, page: Page, selector: str) -> int:
        return await extract_count_from_selector(page, selector)

    async def execute(
        self,
        page: Page,
        username: str,
        base_url: str = "https://x.com",
    ) -> dict[str, Any]:
        """
        Navigates to the user's profile and extracts metrics, avatar, and authentication state.
        """
        clean_username = username.strip().lstrip("@").strip()
        if not clean_username:
            logger.error("Empty username provided to SyncProfileFromX")
            return self._empty_result(clean_username, status="failed")

        profile_url = f"{base_url.rstrip('/')}/{clean_username}"
        logger.info("Syncing profile from X for @%s: %s", clean_username, profile_url)

        try:
            response = await page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
            if response and response.status >= 400:
                logger.warning("Navigation to @%s returned HTTP status %d", clean_username, response.status)
                await self.capture_failure(page, f"sync_profile_{clean_username}")
                return self._empty_result(clean_username, status="failed")

            await sleep_with_jitter(2500)
            current_url = page.url.lower()

            # 1. Detect Challenge / Lock screens
            is_challenged = any(p in current_url for p in ("/account/access", "/login_verification", "/account/suspended", "/i/flow/challenge"))
            if not is_challenged:
                challenge_el = await page.query_selector(
                    '[data-testid="challenge"], [data-testid="confirmation_code"], #challenge-container, input[name="challenge_response"]'
                )
                if challenge_el:
                    is_challenged = True

            if is_challenged:
                logger.warning("X session challenge detected for @%s at %s", clean_username, current_url)
                return self._empty_result(clean_username, status="challenged")

            # 2. Detect Authentication Status & Logged-In Account Info
            auth_indicator = await page.query_selector(
                '[data-testid="SideNav_AccountSwitcher_Button"], [data-testid="AppTabBar_Profile_Link"], [data-testid="SideNav_NewTweet_Button"]'
            )
            is_authenticated = auth_indicator is not None
            status = "authenticated" if is_authenticated else "logged_out"

            # 3. Extract Avatar URL
            avatar_url = ""
            avatar_el = await page.query_selector(
                f'a[href="/{clean_username}/photo"] img, a[href$="/photo"] img[src*="pbs.twimg.com/profile_images"], [data-testid="UserAvatar-Container-profileUser"] img, [data-testid="UserProfileHeader_Items"] img[src*="pbs.twimg.com/profile_images"], [data-testid="SideNav_AccountSwitcher_Button"] img[src*="pbs.twimg.com/profile_images"]'
            )
            if not avatar_el:
                candidates = await page.query_selector_all('[data-testid="primaryColumn"] img[src*="pbs.twimg.com/profile_images"]')
                for cand in candidates:
                    if not await cand.evaluate("el => !!el.closest('article, [data-testid=\"tweet\"]')"):
                        avatar_el = cand
                        break

            if avatar_el:
                raw_src = await avatar_el.get_attribute("src")
                if raw_src:
                    avatar_url = upgrade_avatar_url(raw_src)

            # 4. Extract Display Name & Bio & Verified
            display_name = clean_username
            user_name_el = await page.query_selector('[data-testid="UserName"]')
            if user_name_el:
                lines = [ln.strip() for ln in (await user_name_el.inner_text()).split("\n") if ln.strip()]
                for line in lines:
                    if not line.startswith("@"):
                        display_name = line
                        break

            bio = ""
            bio_el = await page.query_selector('[data-testid="UserDescription"]')
            if bio_el:
                bio = (await bio_el.inner_text()).strip()

            verified_badge = await page.query_selector(
                '[data-testid="UserName"] svg[data-testid="icon-verified"], [data-testid="UserName"] [aria-label*="Verified" i], svg[data-testid="icon-verified"], [data-testid*="verified"]'
            )
            is_verified = verified_badge is not None

            # 5. Extract Follow Counts & Posts Count
            following_count = await self._extract_count_from_selector(page, f"a[href='/{clean_username}/following'], a[href$='/following']")
            followers_count = await self._extract_count_from_selector(
                page, f"a[href='/{clean_username}/verified_followers'], a[href='/{clean_username}/followers'], a[href$='/verified_followers'], a[href$='/followers']"
            )

            posts_count = 0
            try:
                subtitle_els = await page.query_selector_all('[data-testid="primaryColumn"] h2[role="heading"] + div, [data-testid="primaryColumn"] [data-testid="Title"] + div, header [data-testid="Heading"] + div')
                for sub_el in subtitle_els:
                    txt = (await sub_el.inner_text()).strip()
                    if txt and ("post" in txt.lower() or "tweet" in txt.lower()):
                        posts_count = parse_count(txt)
                        if posts_count > 0:
                            break
            except Exception as e_sub:
                logger.debug("Could not parse posts count: %s", e_sub)

            # 6. Extract Timeline Tweets & Metrics
            total_impressions, total_likes, total_retweets, total_replies = 0, 0, 0, 0
            recent_tweets = []

            try:
                tweet_articles = await page.query_selector_all('article[data-testid="tweet"]')
                for t_art in tweet_articles[:12]:
                    views_el = await t_art.query_selector('a[href*="/analytics"], [data-testid="app-text-transition-container"]')
                    t_views = parse_count((await views_el.inner_text()).strip()) if views_el else 0

                    like_el = await t_art.query_selector('[data-testid="like"], [data-testid="unlike"]')
                    t_likes = parse_count((await like_el.inner_text()).strip()) if like_el else 0

                    rt_el = await t_art.query_selector('[data-testid="retweet"], [data-testid="unretweet"]')
                    t_retweets = parse_count((await rt_el.inner_text()).strip()) if rt_el else 0

                    reply_el = await t_art.query_selector('[data-testid="reply"]')
                    t_replies = parse_count((await reply_el.inner_text()).strip()) if reply_el else 0

                    text_el = await t_art.query_selector('[data-testid="tweetText"]')
                    t_body = (await text_el.inner_text()).strip() if text_el else ""

                    total_impressions += t_views
                    total_likes += t_likes
                    total_retweets += t_retweets
                    total_replies += t_replies

                    if t_body:
                        recent_tweets.append({"body": t_body, "views": t_views, "likes": t_likes, "retweets": t_retweets, "replies": t_replies})

                if posts_count == 0 and len(tweet_articles) > 0:
                    posts_count = len(tweet_articles)
            except Exception as e_tw:
                logger.warning("Could not scrape timeline tweets: %s", e_tw)

            total_engagements = total_likes + total_retweets + total_replies
            engagement_rate = round((total_engagements / max(total_impressions, 1)) * 100, 2) if total_impressions > 0 else 0.0

            return {
                "status": status,
                "is_authenticated": is_authenticated,
                "handle": clean_username,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "followers_count": followers_count,
                "following_count": following_count,
                "posts_count": posts_count,
                "impressions_24h": total_impressions,
                "engagements_24h": total_engagements,
                "engagement_rate": engagement_rate,
                "likes_count": total_likes,
                "retweets_count": total_retweets,
                "replies_count": total_replies,
                "recent_tweets": recent_tweets,
                "bio": bio,
                "is_verified": is_verified,
            }

        except Exception as e:
            await self.capture_failure(page, f"sync_profile_{clean_username}")
            logger.error("Failed to sync profile for @%s: %s", clean_username, e)
            return self._empty_result(clean_username, status="failed")

    def _empty_result(self, clean_username: str, status: str) -> dict[str, Any]:
        return {
            "status": status,
            "is_authenticated": False,
            "handle": clean_username,
            "display_name": "",
            "avatar_url": "",
            "followers_count": 0,
            "following_count": 0,
            "posts_count": 0,
            "impressions_24h": 0,
            "engagements_24h": 0,
            "engagement_rate": 0.0,
            "likes_count": 0,
            "retweets_count": 0,
            "replies_count": 0,
            "recent_tweets": [],
            "bio": "",
            "is_verified": False,
        }

# Backward compatibility aliases for test imports
_parse_count = parse_count
_upgrade_avatar_url = upgrade_avatar_url


SyncProfileAction = SyncProfileFromX
