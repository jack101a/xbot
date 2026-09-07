from __future__ import annotations
import logging
import random
from playwright.async_api import Page
from xbot.browser.actions.base import BaseAction
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    human_scroll,
    sleep_think_time,
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)


class ScrapeProfileMetrics(BaseAction):
    """Scrapes follower, following, and post counts from a profile."""

    async def execute(self, page: Page, username: str) -> dict[str, int]:
        try:
            logger.info("Scraping metrics for %s", username)
            clean = username.lstrip("@")
            await page.goto(f"https://x.com/{clean}", wait_until="commit", timeout=20000)
            try:
                await page.wait_for_selector(
                    SELECTORS.get("profile_avatar", "[data-testid*='UserAvatar']"), timeout=15000
                )
            except Exception:
                pass
            await sleep_with_jitter(2000)

            metrics = {"followers": 0, "following": 0, "posts": 0}

            following_el = await page.query_selector(f"a[href='/{clean}/following'] span")
            if following_el:
                metrics["following"] = self._parse_count(await following_el.inner_text())

            followers_el = await page.query_selector(
                f"a[href='/{clean}/verified_followers'] span, a[href='/{clean}/followers'] span"
            )
            if followers_el:
                metrics["followers"] = self._parse_count(await followers_el.inner_text())

            # Also scrape avatar_url if present
            avatar_el = await page.query_selector("img[src*='pbs.twimg.com/profile_images']")
            if avatar_el:
                metrics["avatar_url"] = await avatar_el.get_attribute("src") or ""  # type: ignore[assignment]

            logger.info("Scraped metrics: %s", metrics)
            return metrics
        except Exception as e:
            await self.capture_failure(page, f"scrape_metrics_{username}")
            logger.error("Failed to scrape metrics: %s", e)
            return {"followers": 0, "following": 0, "posts": 0}

    def _parse_count(self, text: str) -> int:
        text = text.replace(",", "").replace(" ", "").upper()
        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        if "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        try:
            return int(text)
        except Exception:
            return 0

class ScrapeTrends(BaseAction):
    """Scrapes trending topics from the X explore page."""

    async def execute(self, page: Page, limit: int = 15) -> list[dict[str, str]]:
        try:
            logger.info("Scraping X Trends (limit=%d)", limit)
            await page.goto("https://x.com/explore", wait_until="domcontentloaded", timeout=25000)
            await sleep_with_jitter(3000)

            # Human-like scroll through explore section
            await human_scroll(page, random.randint(200, 400), "down")
            await sleep_think_time(1000, 2000)

            from xbot.ai.sniper import BANNED_POLITICS_REGEX
            trends: list[dict[str, str]] = []
            seen_topics: set[str] = set()

            # 1. Try dedicated trend selector
            trend_elements = await page.query_selector_all("[data-testid='trend']")
            if not trend_elements:
                trend_elements = await page.query_selector_all("[data-testid='cellInnerDiv']")

            for el in trend_elements:
                if len(trends) >= limit:
                    break
                text = await el.inner_text()
                if not text or "promoted by" in text.lower() or BANNED_POLITICS_REGEX.search(text):
                    continue

                lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
                if not lines:
                    continue

                # Filter out sports scores / multi-line schedule tables
                if len(lines) > 6 and any("final" in l.lower() or "today" in l.lower() for l in lines):
                    continue

                topic = lines[1] if len(lines) > 1 and not lines[0].startswith("#") else lines[0]
                context = lines[0] if len(lines) > 1 else "Trending on X"
                volume = lines[2] if len(lines) > 2 else (lines[1] if len(lines) > 1 and "post" in lines[1].lower() else "")

                # Clean topic
                topic = topic.strip()
                if topic and topic.lower() not in seen_topics and len(topic) > 2:
                    seen_topics.add(topic.lower())
                    trends.append({
                        "topic": topic,
                        "context": context,
                        "volume": volume,
                    })

            logger.info("Scraped %d live X trends.", len(trends))
            return trends
        except Exception as e:
            await self.capture_failure(page, "scrape_trends")
            logger.error("Failed to scrape trends: %s", e)
            return []

