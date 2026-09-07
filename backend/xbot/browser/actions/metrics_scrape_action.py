from __future__ import annotations
import logging
import random
import re
from typing import Any
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_click,
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)


class ScrapeProfileTweets(BaseAction):
    """Scrapes recent tweets of a profile to calculate engagement metrics."""

    async def execute(self, page: Page, username: str, limit: int = 5) -> dict:
        try:
            logger.info("Scraping recent tweets for %s", username)
            clean = username.lstrip("@")
            await page.goto(f"https://x.com/{clean}", wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_selector(
                SELECTORS.get("tweet", "article[data-testid='tweet']"), timeout=10000
            )
            await sleep_with_jitter(2000)

            followers = 0
            following = 0
            try:
                followers_el = await page.query_selector(
                    "a[href$='/followers'], a[href$='/verified_followers']"
                )
                if followers_el:
                    txt = await followers_el.inner_text()
                    followers = self._parse_abbrev(txt.split()[0])

                following_el = await page.query_selector("a[href$='/following']")
                if following_el:
                    txt = await following_el.inner_text()
                    following = self._parse_abbrev(txt.split()[0])
            except Exception as e:
                logger.error("Failed to parse follower/following counts: %s", e)

            tweets_data = []
            for _ in range(3):
                tweet_elements = await page.query_selector_all(
                    SELECTORS.get("tweet", "article[data-testid='tweet']")
                )
                for el in tweet_elements:
                    if len(tweets_data) >= limit:
                        break

                    text_el = await el.query_selector("[data-testid='tweetText']")
                    text = await text_el.inner_text() if text_el else ""
                    if not text or any(t.get("text") == text for t in tweets_data):
                        continue

                    def _pm(label: str) -> int:
                        if not label:
                            return 0
                        n = label.split()[0].upper().replace(",", "")
                        if "K" in n:
                            return int(float(n.replace("K", "")) * 1000)
                        if "M" in n:
                            return int(float(n.replace("M", "")) * 1000000)
                        try:
                            return int(float(n))
                        except Exception:
                            return 0

                    reply_el = await el.query_selector("[data-testid='reply']")
                    retweet_el = await el.query_selector("[data-testid='retweet']")
                    like_el = await el.query_selector("[data-testid='like']")
                    view_el = await el.query_selector("a[href*='/analytics']")

                    replies = _pm(await reply_el.get_attribute("aria-label") if reply_el else "")
                    retweets = _pm(await retweet_el.get_attribute("aria-label") if retweet_el else "")
                    likes = _pm(await like_el.get_attribute("aria-label") if like_el else "")
                    views = _pm(await view_el.get_attribute("aria-label") if view_el else "")

                    tweets_data.append({
                        "text": text,
                        "replies": replies,
                        "retweets": retweets,
                        "likes": likes,
                        "views": views,
                        "engagement_score": replies + retweets + likes,
                    })

                if len(tweets_data) >= limit:
                    break
                await human_scroll(page, random.randint(300, 600), "down")
                await sleep_with_jitter(1500)

            logger.info("Scraped %d tweets for %s", len(tweets_data), username)
            return {"tweets": tweets_data, "followers": followers, "following": following}
        except Exception as e:
            await self.capture_failure(page, f"scrape_tweets_{username}")
            logger.error("Failed to scrape profile tweets: %s", e)
            return {"tweets": [], "followers": 0, "following": 0}

    def _parse_abbrev(self, text: str) -> int:
        t = text.strip().upper().replace(",", "")
        if "K" in t:
            return int(float(t.replace("K", "")) * 1000)
        if "M" in t:
            return int(float(t.replace("M", "")) * 1000000)
        try:
            return int(float(t))
        except Exception:
            return 0

class ScrapeCreatorStudioMetrics(BaseAction):
    """
    Navigates to https://x.com/i/jf/creators/studio, clicks into Original Content Rewards eligibility,
    and extracts official live account-wide metrics:
    - Verified Followers (out of 500)
    - 90-Day Verified Home Timeline Impressions (out of 500,000)
    """

    async def execute(self, page: Page) -> dict[str, Any]:
        try:
            logger.info("Opening X Creator Studio to scrape official monetization & impression metrics...")
            await page.goto("https://x.com/i/jf/creators/studio", wait_until="domcontentloaded", timeout=25000)
            await sleep_think_time(1500, 3000)

            btn1 = await page.query_selector("text=Original Content Rewards")
            if btn1:
                await human_click(page, btn1, 200, 500)
                await sleep_think_time(1000, 2000)

            btn2 = await page.query_selector("text=Check Original Content Rewards eligibility")
            if btn2:
                await human_click(page, btn2, 200, 500)
                await sleep_think_time(1500, 3000)

            body_text = await page.inner_text("body")

            # Extract verified followers (e.g. "16")
            vf_match = re.search(r"Have at least 500 Verified followers\s+([0-9,]+)", body_text)
            verified_followers = int(vf_match.group(1).replace(",", "")) if vf_match else 0

            # Extract 90-day impressions (e.g. "0" or "45K" or "1.2M")
            imp_match = re.search(r"Have at least 500K Verified Home Timeline impressions.*?\n+([0-9,KMkm.]+)", body_text)
            imp_str = imp_match.group(1).strip() if imp_match else "0"
            
            verified_impressions_90d = 0
            if imp_str:
                clean_imp = imp_str.upper().replace(",", "")
                if "M" in clean_imp:
                    verified_impressions_90d = int(float(clean_imp.replace("M", "")) * 1000000)
                elif "K" in clean_imp:
                    verified_impressions_90d = int(float(clean_imp.replace("K", "")) * 1000)
                else:
                    try:
                        verified_impressions_90d = int(float(clean_imp))
                    except Exception:
                        verified_impressions_90d = 0

            from datetime import datetime as dt
            logger.info("Successfully scraped Creator Studio: %d verified followers, %d 90-day verified impressions", verified_followers, verified_impressions_90d)
            return {
                "status": "success",
                "verified_followers": verified_followers,
                "verified_impressions_90d": verified_impressions_90d,
                "scraped_at": dt.utcnow().isoformat(),
            }
        except Exception as e:
            logger.warning("Failed to scrape Creator Studio metrics: %s", e)
            return {
                "status": "failed",
                "error": str(e),
                "verified_followers": 0,
                "verified_impressions_90d": 0,
            }

