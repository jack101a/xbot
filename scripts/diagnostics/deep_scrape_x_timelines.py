import asyncio
import json
import logging
import os
import re
import sys
from typing import Any

# Add backend to python path
sys.path.insert(0, os.path.abspath("backend"))

from xbot.browser.manager import BrowserManager
from xbot.browser.actions.x_actions import human_scroll, sleep_with_jitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("deep_scraper")

OUTPUT_PATH = "data/real_x_timeline_deep_corpus.json"


async def scrape_feed_posts(page, max_posts=50, feed_name="home"):
    logger.info("Scraping feed '%s' (target: %d posts)...", feed_name, max_posts)
    posts = []
    seen_texts = set()
    scroll_attempts = 0
    max_scrolls = 40

    while len(posts) < max_posts and scroll_attempts < max_scrolls:
        tweet_articles = await page.query_selector_all("article[data-testid='tweet']")
        for article in tweet_articles:
            try:
                # 1. Text
                text_el = await article.query_selector("[data-testid='tweetText']")
                raw_text = await text_el.inner_text() if text_el else ""
                clean_text = raw_text.strip()
                if not clean_text or clean_text in seen_texts:
                    continue
                seen_texts.add(clean_text)

                # 2. Author
                user_el = await article.query_selector("[data-testid='User-Name']")
                author_text = await user_el.inner_text() if user_el else ""
                author_handle = None
                m_handle = re.search(r"@(\w+)", author_text)
                if m_handle:
                    author_handle = m_handle.group(1)

                is_verified = bool(await article.query_selector("svg[data-testid='icon-verified'], [aria-label*='Verified']"))

                # 3. URL
                time_el = await article.query_selector("time")
                tweet_url = None
                if time_el:
                    parent_a = await time_el.evaluate_handle("el => el.closest('a')")
                    if parent_a:
                        href = await parent_a.get_attribute("href")
                        if href:
                            tweet_url = f"https://x.com{href}" if href.startswith("/") else href

                # 4. Metrics
                views_el = await article.query_selector("a[href*='/analytics'], [aria-label*='views'], [aria-label*='Views']")
                views_text = await views_el.inner_text() if views_el else ""

                like_el = await article.query_selector("[data-testid='like'], [data-testid='unlike']")
                like_text = await like_el.inner_text() if like_el else ""

                reply_el = await article.query_selector("[data-testid='reply']")
                reply_text = await reply_el.inner_text() if reply_el else ""

                retweet_el = await article.query_selector("[data-testid='retweet'], [data-testid='unretweet']")
                retweet_text = await retweet_el.inner_text() if retweet_el else ""

                # 5. Media check
                has_image = bool(await article.query_selector("[data-testid='tweetPhoto'] img, img[src*='pbs.twimg.com/media/']"))
                has_video = bool(await article.query_selector("[data-testid='videoPlayer'], video"))
                is_quote = bool(await article.query_selector("[data-testid='quoteTweet'], div[role='link'][tabindex='0']"))

                post_entry = {
                    "feed": feed_name,
                    "author": author_handle or "unknown",
                    "is_verified": is_verified,
                    "url": tweet_url,
                    "text": clean_text,
                    "char_count": len(clean_text),
                    "word_count": len(clean_text.split()),
                    "line_count": len(clean_text.split("\n")),
                    "has_double_newline": "\n\n" in clean_text,
                    "has_image": has_image,
                    "has_video": has_video,
                    "is_quote": is_quote,
                    "views_raw": views_text.strip(),
                    "likes_raw": like_text.strip(),
                    "replies_raw": reply_text.strip(),
                    "retweets_raw": retweet_text.strip(),
                }
                posts.append(post_entry)
                if len(posts) >= max_posts:
                    break
            except Exception as item_err:
                logger.debug("Error extracting tweet card: %s", item_err)

        scroll_attempts += 1
        await human_scroll(page, 700, "down")
        await sleep_with_jitter(1500)

    logger.info("Feed '%s' yielded %d unique tweets.", feed_name, len(posts))
    return posts


async def scrape_tweet_comments(page, tweet_url, max_comments=10):
    logger.info("Navigating to tweet for comments: %s", tweet_url)
    comments = []
    try:
        await page.goto(tweet_url, wait_until="domcontentloaded", timeout=20000)
        await sleep_with_jitter(2500)

        articles = await page.query_selector_all("article[data-testid='tweet']")
        # Skip root tweet (idx 0)
        for art in articles[1:max_comments+1]:
            text_el = await art.query_selector("[data-testid='tweetText']")
            if text_el:
                c_text = (await text_el.inner_text()).strip()
                if c_text:
                    user_el = await art.query_selector("[data-testid='User-Name']")
                    user_text = await user_el.inner_text() if user_el else ""
                    m_handle = re.search(r"@(\w+)", user_text)
                    handle = m_handle.group(1) if m_handle else "unknown"

                    comments.append({
                        "parent_url": tweet_url,
                        "author": handle,
                        "text": c_text,
                        "char_count": len(c_text),
                        "word_count": len(c_text.split()),
                        "has_double_newline": "\n\n" in c_text,
                    })
    except Exception as e:
        logger.warning("Failed to scrape comments for %s: %s", tweet_url, e)
    return comments


async def main():
    manager = BrowserManager()
    profile_slug = "test_profile1"
    all_corpus = {
        "standalone_and_quote_posts": [],
        "replies_and_comments": [],
    }

    try:
        await manager.start()
        if not manager.acquire_lock(profile_slug, timeout_seconds=120):
            logger.error("Could not acquire browser lock for %s", profile_slug)
            return

        context = await manager.get_context(profile_slug)
        page = await context.new_page()
        page.set_default_timeout(25000)

        # 1. Scrape Live Home For You Timeline
        logger.info("Opening https://x.com/home...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
        await sleep_with_jitter(3000)
        home_posts = await scrape_feed_posts(page, max_posts=40, feed_name="home_for_you")
        all_corpus["standalone_and_quote_posts"].extend(home_posts)

        # 2. Scrape Top Tech & Creator Timelines
        kol_profiles = ["paulg", "levelsio", "MKBHD", "karpathy", "DiscussingFilm"]
        for kol in kol_profiles:
            try:
                kol_url = f"https://x.com/{kol}"
                logger.info("Opening %s...", kol_url)
                await page.goto(kol_url, wait_until="domcontentloaded", timeout=20000)
                await sleep_with_jitter(2500)
                kol_posts = await scrape_feed_posts(page, max_posts=15, feed_name=f"profile_{kol}")
                all_corpus["standalone_and_quote_posts"].extend(kol_posts)
            except Exception as k_err:
                logger.warning("Error scraping @%s: %s", kol, k_err)

        # 3. Scrape Viral Search Queries (Tech & AI)
        search_queries = ["AI coding since:2026-08-20 min_faves:50", "tech startup min_faves:50"]
        for q in search_queries:
            try:
                import urllib.parse
                s_url = f"https://x.com/search?q={urllib.parse.quote(q)}&f=top"
                logger.info("Opening search %s...", s_url)
                await page.goto(s_url, wait_until="domcontentloaded", timeout=20000)
                await sleep_with_jitter(2500)
                search_posts = await scrape_feed_posts(page, max_posts=20, feed_name=f"search_{q[:10]}")
                all_corpus["standalone_and_quote_posts"].extend(search_posts)
            except Exception as s_err:
                logger.warning("Error searching query '%s': %s", q, s_err)

        # 4. Scrape Comments from Top Viral Posts
        posts_with_urls = [p for p in all_corpus["standalone_and_quote_posts"] if p.get("url") and "status" in str(p.get("url"))]
        logger.info("Found %d posts with URLs. Scraping comments from top 10...", len(posts_with_urls))
        for p in posts_with_urls[:10]:
            c_list = await scrape_tweet_comments(page, p["url"], max_comments=8)
            all_corpus["replies_and_comments"].extend(c_list)
            await sleep_with_jitter(1000)

        # Save to disk
        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(all_corpus, f, indent=2, ensure_ascii=False)

        total_posts = len(all_corpus["standalone_and_quote_posts"])
        total_comments = len(all_corpus["replies_and_comments"])
        logger.info("✅ SUCCESS: Scraped %d posts and %d replies/comments saved to %s", total_posts, total_comments, OUTPUT_PATH)

    except Exception as e:
        logger.error("Deep scraper failed: %s", e, exc_info=True)
    finally:
        manager.release_lock(profile_slug)
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
