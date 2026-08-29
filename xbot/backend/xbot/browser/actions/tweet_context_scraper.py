from __future__ import annotations
import logging
import re
from typing import Any
from playwright.async_api import Page
from xbot.browser.actions.selectors import SELECTORS
from xbot.browser.timing import (
    sleep_with_jitter,
)

logger = logging.getLogger(__name__)

async def scrape_target_tweet_context(
    page: Page, target_idx: int = 0, tweet_url: str | None = None
) -> dict[str, Any]:
    """
    Scrapes full live text, author, metrics, media URLs/alts, and top visible comment replies
    from the current tweet thread.
    """
    try:
        if tweet_url and ("/status/" in tweet_url) and (tweet_url not in page.url):
            try:
                await page.goto(tweet_url, wait_until="commit", timeout=20000)
                await page.wait_for_selector(SELECTORS["tweet"], timeout=12000)
                await sleep_with_jitter(1500)
            except Exception as nav_e:
                logger.warning("scrape_target_tweet_context navigation error: %s", nav_e)

        tweet_elements = await page.query_selector_all(SELECTORS["tweet"])
        if not tweet_elements or target_idx >= len(tweet_elements):
            return {}

        target_tweet = tweet_elements[target_idx]

        # Author handle
        author = ""
        user_el = await target_tweet.query_selector('[data-testid="User-Name"]')
        if user_el:
            user_text = await user_el.inner_text()
            match = re.search(r"@([A-Za-z0-9_]+)", user_text)
            if match:
                author = match.group(1)

        # Main tweet text
        text = ""
        text_el = await target_tweet.query_selector(SELECTORS.get("tweet_text", '[data-testid="tweetText"]'))
        if text_el:
            text = (await text_el.inner_text()).strip()

        # Helper to parse metric numbers like "1.2K", "450", "2M", "1,200"
        def _parse_metric(val_str: str | None) -> int:
            if not val_str:
                return 0
            val = str(val_str).replace(",", "").replace("\u00a0", " ").strip()
            m = re.search(r'([\d\.]+)\s*([KkMmBbtT]?)', val)
            if not m:
                return 0
            try:
                num = float(m.group(1))
                unit = m.group(2).upper()
                if unit == "K":
                    return int(num * 1000)
                elif unit == "M":
                    return int(num * 1000000)
                elif unit == "B" or unit == "T":
                    return int(num * 1000000000)
                return int(num)
            except Exception:
                return 0

        # Scrape top comments in thread (filtered & sorted by popularity/likes)
        collected_comments: list[dict[str, Any]] = []
        seen_texts: set[str] = set()

        async def _collect_comments():
            nonlocal collected_comments, seen_texts
            all_tweets = await page.query_selector_all(SELECTORS["tweet"])
            comment_elements = all_tweets[target_idx + 1:] if len(all_tweets) > target_idx else []
            for comment_el in comment_elements:
                c_text_el = await comment_el.query_selector(SELECTORS.get("tweet_text", '[data-testid="tweetText"]'))
                if not c_text_el:
                    continue
                c_text = (await c_text_el.inner_text()).strip()
                if not c_text or c_text == text or c_text in seen_texts:
                    continue
                seen_texts.add(c_text)

                # Commenter handle
                c_author = ""
                c_user_el = await comment_el.query_selector('[data-testid="User-Name"]')
                if c_user_el:
                    c_user_text = await c_user_el.inner_text()
                    c_match = re.search(r"@([A-Za-z0-9_]+)", c_user_text)
                    if c_match:
                        c_author = c_match.group(1)

                # Extract like count / popularity
                c_likes = 0
                try:
                    like_el = await comment_el.query_selector('[data-testid="like"], button[aria-label*="Like"], div[data-testid="like"]')
                    if like_el:
                        aria_label = await like_el.get_attribute("aria-label") or ""
                        like_text = await like_el.inner_text() or ""
                        c_likes = _parse_metric(aria_label) or _parse_metric(like_text)
                except Exception:
                    pass

                collected_comments.append({
                    "author": c_author,
                    "text": c_text,
                    "likes": c_likes,
                })

        # First pass
        await _collect_comments()

        # Scroll gently down to load 15-20 comments to find the most popular/top-liked
        try:
            if len(collected_comments) < 8:
                await page.evaluate("window.scrollBy(0, 600)")
                await sleep_with_jitter(1000)
                await _collect_comments()

            if len(collected_comments) < 15:
                await page.evaluate("window.scrollBy(0, 800)")
                await sleep_with_jitter(1000)
                await _collect_comments()
        except Exception:
            pass

        # Sort descending by likes / popularity (most popular first)
        collected_comments.sort(key=lambda c: c["likes"], reverse=True)
        top_comments = collected_comments[:10]

        # Scrape attached media images, videos, and alt text
        media_urls: list[str] = []
        media_alts: list[str] = []
        try:
            # 1. Images
            img_elements = await target_tweet.query_selector_all(
                '[data-testid="tweetPhoto"] img, div[aria-label="Image"] img, img[alt*="Image"], img'
            )
            for img in img_elements:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                if src and src.startswith("http") and not any(ignored in src for ignored in ("profile_images", "emoji", "svg", "twemoji", "avatar")):
                    if src not in media_urls:
                        media_urls.append(src)
                if alt and alt.strip():
                    alt_clean = alt.strip()
                    if alt_clean.lower() not in ("image", "embedded video", "profile image", "avatar") and alt_clean not in media_alts:
                        media_alts.append(alt_clean)

            # 2. Videos
            video_elements = await target_tweet.query_selector_all(
                '[data-testid="videoPlayer"] video, [data-testid="videoComponent"] video, video'
            )
            for vid in video_elements:
                v_src = await vid.get_attribute("src")
                if not v_src:
                    source_el = await vid.query_selector("source")
                    if source_el:
                        v_src = await source_el.get_attribute("src")
                if v_src and v_src.startswith("http") and v_src not in media_urls:
                    media_urls.append(v_src)
                elif not v_src:
                    v_poster = await vid.get_attribute("poster")
                    if v_poster and v_poster.startswith("http") and v_poster not in media_urls:
                        media_urls.append(v_poster)
        except Exception:
            pass

        # Extract root tweet engagement metrics (views/impressions, likes, replies, retweets)
        views_count = 0
        likes_count = 0
        replies_count = 0
        retweets_count = 0
        try:
            # 1. Views / Analytics
            view_el = await target_tweet.query_selector(
                'a[href*="/analytics"], [data-testid="app-text-transition-container"], [aria-label*="Views"], [aria-label*="views"], [aria-label*="Impressions"], [aria-label*="impressions"]'
            )
            if view_el:
                v_aria = await view_el.get_attribute("aria-label") or ""
                v_text = await view_el.inner_text() or ""
                views_count = _parse_metric(v_aria) or _parse_metric(v_text)

            # 2. Likes
            like_el = await target_tweet.query_selector('[data-testid="like"], button[aria-label*="Like"], div[data-testid="like"]')
            if like_el:
                l_aria = await like_el.get_attribute("aria-label") or ""
                l_text = await like_el.inner_text() or ""
                likes_count = _parse_metric(l_aria) or _parse_metric(l_text)

            # 3. Replies
            reply_el = await target_tweet.query_selector('[data-testid="reply"], button[aria-label*="Reply"], div[data-testid="reply"]')
            if reply_el:
                r_aria = await reply_el.get_attribute("aria-label") or ""
                r_text = await reply_el.inner_text() or ""
                replies_count = _parse_metric(r_aria) or _parse_metric(r_text)

            # 4. Retweets
            rt_el = await target_tweet.query_selector('[data-testid="retweet"], button[aria-label*="Repost"], button[aria-label*="Retweet"], div[data-testid="retweet"]')
            if rt_el:
                rt_aria = await rt_el.get_attribute("aria-label") or ""
                rt_text = await rt_el.inner_text() or ""
                retweets_count = _parse_metric(rt_aria) or _parse_metric(rt_text)
        except Exception:
            pass

        logger.info(
            "Scraped live thread context on page: author=@%s, text_preview='%s', views=%d, likes=%d, captured_comments=%d, media=%d",
            author,
            text[:40],
            views_count,
            likes_count,
            len(top_comments),
            len(media_urls),
        )
        return {
            "author": author,
            "text": text,
            "views": views_count,
            "impressions": views_count,
            "likes": likes_count,
            "replies": replies_count,
            "retweets": retweets_count,
            "top_comments": top_comments,
            "media_urls": media_urls[:4],
            "media_alts": media_alts[:4],
        }
    except Exception as e:
        logger.debug("Error scraping target tweet context: %s", e)
        return {}


async def peek_tweet_context_via_worker(
    manager: Any, profile_slug: str, tweet_url: str
) -> dict[str, Any]:
    """
    Spins up an ephemeral worker tab (Tab 3 or 4), extracts full media + top 10 comments,
    and auto-closes in < 2 seconds without disturbing the main Home feed.
    """
    try:
        async with manager.acquire_worker(profile_slug, name="tweet_peek") as worker_page:
            return await scrape_target_tweet_context(worker_page, target_idx=0, tweet_url=tweet_url)
    except Exception as e:
        logger.warning("peek_tweet_context_via_worker failed for %s: %s", tweet_url, e)
        return {}



