import asyncio
import json
import logging
import os
import random
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from xbot.browser.manager import BrowserManager
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.actions.x_actions import human_scroll, sleep_think_time, sleep_with_jitter
from xbot.persona import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("explorer_follow_back")

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "follow_back_deep_scan.json"

QUERIES = [
    "follow back",
    "drop your handle",
    "looking for mutuals",
    "verified mutuals follow back",
    "f4f mutuals",
    "drop handle anime tech",
]

async def scrape_tweet_element(el: Any) -> dict[str, Any] | None:
    try:
        user_el = await el.query_selector('[data-testid="User-Name"]')
        if not user_el:
            return None
        u_text = await user_el.inner_text()
        m = re.search(r"@([A-Za-z0-9_]+)", u_text)
        if not m:
            return None
        author = m.group(1)
        display_name = u_text.split("@")[0].strip()

        verified_el = await user_el.query_selector(
            'svg[data-testid="icon-verified"], svg[aria-label*="Verified"], svg[aria-label*="Blue"]'
        )
        is_blue_tick = verified_el is not None

        # Text
        text = ""
        text_el = await el.query_selector('[data-testid="tweetText"]')
        if text_el:
            text = (await text_el.inner_text()).strip()

        # Tweet Link
        url = None
        time_link = await el.query_selector("time")
        if time_link:
            parent_a = await time_link.evaluate_handle("el => el.closest('a')")
            if parent_a:
                href = await parent_a.get_attribute("href")
                if href and "/status/" in href:
                    url = f"https://x.com{href}" if href.startswith("/") else href

        # Metrics
        likes = 0
        retweets = 0
        replies = 0

        reply_el = await el.query_selector('[data-testid="reply"]')
        if reply_el:
            txt = (await reply_el.inner_text()).strip()
            replies = _parse_int(txt)

        retweet_el = await el.query_selector('[data-testid="retweet"]')
        if retweet_el:
            txt = (await retweet_el.inner_text()).strip()
            retweets = _parse_int(txt)

        like_el = await el.query_selector('[data-testid="like"]')
        if like_el:
            txt = (await like_el.inner_text()).strip()
            likes = _parse_int(txt)

        return {
            "author": author,
            "display_name": display_name,
            "is_blue_tick": is_blue_tick,
            "text": text,
            "url": url,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
        }
    except Exception as e:
        logger.debug("Error parsing tweet element: %s", e)
        return None

def _parse_int(val: str) -> int:
    if not val:
        return 0
    val = val.replace(",", "").upper()
    try:
        if "K" in val:
            return int(float(val.replace("K", "")) * 1000)
        if "M" in val:
            return int(float(val.replace("M", "")) * 1000000)
        return int(val)
    except Exception:
        return 0

async def scrape_thread_comments(page: Any, tweet_url: str, max_comments: int = 8) -> list[dict[str, Any]]:
    comments = []
    try:
        logger.info("Opening thread to explore comment section: %s", tweet_url)
        await page.goto(tweet_url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector(SELECTORS["tweet"], timeout=10000)
        await sleep_think_time(1000, 2000)

        # Scroll to load comments
        for _ in range(2):
            await human_scroll(page, random.randint(350, 650), "down")
            await sleep_think_time(800, 1500)

        tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
        seen_handles = set()

        for el in tweet_elements[1:]:  # skip root
            data = await scrape_tweet_element(el)
            if data and data["author"] not in seen_handles:
                seen_handles.add(data["author"])
                comments.append({
                    "author": data["author"],
                    "display_name": data["display_name"],
                    "is_blue_tick": data["is_blue_tick"],
                    "text": data["text"],
                    "likes": data["likes"],
                })
                if len(comments) >= max_comments:
                    break
    except Exception as e:
        logger.warning("Could not scrape comments for %s: %s", tweet_url, e)
    return comments

async def main():
    profile_slug = "test_profile1"
    manager = BrowserManager()
    await manager.start()

    profile_dir = manager.base_profile_dir / profile_slug
    config = load_config(profile_dir)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not manager.acquire_lock(profile_slug):
        logger.warning("Browser lock is currently held. Releasing and re-acquiring for exploration...")
        manager.release_lock(profile_slug)
        manager.acquire_lock(profile_slug)

    context = None
    try:
        context = await manager.get_context(
            profile_slug=profile_slug,
            timezone="Asia/Kolkata",
            proxy_url=config.proxy_url,
        )
        page = await context.new_page()

        collected_posts: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for q in QUERIES:
            if len(collected_posts) >= 55:
                break
            logger.info("==========================================")
            logger.info("Scanning query: '%s' (Collected so far: %d)", q, len(collected_posts))
            search_url = f"https://x.com/search?q={quote_plus(q)}&f=live"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_selector(SELECTORS["tweet"], timeout=12000)
            await sleep_think_time(1500, 3000)

            for scroll_idx in range(4):
                tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
                for el in tweet_elements:
                    data = await scrape_tweet_element(el)
                    if data and data.get("url") and data["url"] not in seen_urls:
                        low_text = data["text"].lower()
                        if any(k in low_text for k in ["follow", "mutual", "handle", "f4f", "drop", "connect", "grow"]):
                            seen_urls.add(data["url"])
                            collected_posts.append(data)
                            logger.info("  [+] Found Post (%d/50+): @%s (Verified: %s, Replies: %d) -> '%s'",
                                len(collected_posts), data["author"], data["is_blue_tick"], data["replies"], data["text"][:60]
                            )
                await human_scroll(page, random.randint(400, 750), "down")
                await sleep_think_time(1200, 2500)

        logger.info("Gathered %d candidate follow-back posts. Now harvesting comment discussions...", len(collected_posts))

        # Deep dive into comment sections for top 25 active posts
        for idx, post in enumerate(collected_posts[:25]):
            if post.get("url"):
                comments = await scrape_thread_comments(page, post["url"], max_comments=8)
                post["discussions"] = comments
                logger.info("  -> Harvested %d comments for post by @%s", len(comments), post["author"])

        # Save to JSON
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "total_posts_scanned": len(collected_posts),
                "posts": collected_posts
            }, f, indent=2, ensure_ascii=False)

        logger.info("SUCCESS: Scanned and saved %d follow-back posts with discussions to %s", len(collected_posts), OUTPUT_FILE)

    except Exception as e:
        logger.error("Exploration encountered error: %s", e, exc_info=True)
    finally:
        if context:
            await context.close()
        manager.release_lock(profile_slug)
        await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
