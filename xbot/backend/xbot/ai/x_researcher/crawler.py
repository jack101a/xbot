from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import re
from typing import Any
import urllib.parse

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona

from .extractor import ViralTweet, _parse_engagement_number

logger = logging.getLogger(__name__)


async def generate_search_phrases(
    topic: str, persona: Persona | None = None, client: Any = None
) -> list[str]:
    """
    Uses AI to generate 2-3 precise, high-intent X search queries for a topic.
    Returns strings optimized for X search bar (avoiding boolean operators that X rejects).
    """
    clean_topic = topic.strip()
    if not clean_topic:
        return ["viral news"]

    if client is None:
        client = get_ai_client()

    prompt = (
        f"You are a master social media researcher on X (Twitter).\n"
        f"Given the user topic or breaking controversy: \"{clean_topic}\", "
        f"generate exactly 3 distinct, high-signal search queries to find the most viral tweets, "
        f"official statements, and hot debates on X.\n\n"
        f"Rules:\n"
        f"- Use exact brand, product, celebrity, or news keywords matching the topic directly.\n"
        f"- Keep each query between 2 and 4 words.\n"
        f"- Return ONLY a valid JSON array of 3 strings. Example: [\"Query 1\", \"Query 2\", \"Query 3\"]"
    )

    try:
        raw_resp = await client.chat.completions.create(
            model=settings.MODEL_TREND_ANALYSIS,
            messages=[
                {
                    "role": "system",
                    "content": "You are a specialized search query optimizer for X/Twitter. Respond ONLY with a JSON array.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        content = raw_resp.choices[0].message.content or ""
        cleaned = content.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) > 0:
            queries = [str(q).strip() for q in parsed if str(q).strip()]
            if clean_topic not in queries:
                queries.insert(0, clean_topic)
            return queries[:3]
    except Exception as e:
        logger.debug("AI query phrasing fallback for '%s': %s", clean_topic, e)

    tokens = clean_topic.split()
    if len(tokens) > 2:
        q1 = clean_topic
        q2 = " ".join(tokens[:3])
        return [q1, q2]
    return [clean_topic, f"{clean_topic} controversy", f"{clean_topic} news"]


async def scrape_x_top_tweets(
    queries: list[str],
    max_tweets: int = 25,
    profile_slug: str = "test_profile1",
    max_age_days: int = 7,
) -> list[ViralTweet]:
    """
    Navigates to X Top Search (`f=top`) using Playwright to scrape up to 20-30 viral posts
    with full texts, engagement metrics, and media image URLs.
    Strictly filters out any posts older than `max_age_days` (default 7 days).
    """
    from xbot.browser.manager import BrowserManager

    collected_tweets: list[ViralTweet] = []
    seen_texts: set[str] = set()

    now_utc = datetime.now(timezone.utc)
    since_date = (now_utc - timedelta(days=max_age_days)).strftime("%Y-%m-%d")

    mgr = BrowserManager(base_profile_dir=Path("/home/ubuntu/projects/xbot/data/profiles"))
    try:
        await mgr.start()
        ctx = await mgr.get_context(profile_slug)
        page = await ctx.new_page()

        for q in queries:
            if len(collected_tweets) >= max_tweets:
                break

            search_query = q
            if "since:" not in search_query:
                search_query = f"{q} since:{since_date}"

            url = f"https://x.com/search?q={urllib.parse.quote_plus(search_query)}&f=top"
            logger.info("Deep X Research navigating to (7-day window since %s): %s", since_date, url)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(4)
            except Exception as nav_err:
                logger.warning("Error loading X search page for '%s': %s", q, nav_err)
                continue

            for scroll_idx in range(4):
                if len(collected_tweets) >= max_tweets:
                    break

                articles = await page.query_selector_all("article[data-testid='tweet']")
                for art in articles:
                    try:
                        text_el = await art.query_selector("[data-testid='tweetText']")
                        text = await text_el.inner_text() if text_el else ""
                        if not text or len(text) < 15:
                            continue

                        norm_key = re.sub(r"\W+", "", text.lower())[:50]
                        if norm_key in seen_texts:
                            continue
                        seen_texts.add(norm_key)

                        time_el = await art.query_selector("time")
                        parent_link = None
                        datetime_val = None
                        created_at_iso = None
                        if time_el:
                            parent_link = await time_el.evaluate("el => el.closest('a')?.href")
                            dt_attr = await time_el.get_attribute("datetime")
                            if dt_attr:
                                created_at_iso = dt_attr
                                try:
                                    cleaned_dt = dt_attr.replace("Z", "+00:00")
                                    datetime_val = datetime.fromisoformat(cleaned_dt)
                                    if datetime_val.tzinfo is None:
                                        datetime_val = datetime_val.replace(tzinfo=timezone.utc)
                                except Exception:
                                    datetime_val = None

                        if datetime_val:
                            age_days = (now_utc - datetime_val).total_seconds() / 86400.0
                            if age_days > max_age_days:
                                logger.debug("Skipping ancient tweet from %.1f days ago: %s", age_days, text[:40])
                                continue

                        user_el = await art.query_selector("[data-testid='User-Name']")
                        user_raw = await user_el.inner_text() if user_el else ""
                        lines = [line.strip() for line in user_raw.split("\n") if line.strip()]

                        auth_name = lines[0] if lines else "Creator"
                        auth_handle = ""
                        for line in lines:
                            if line.startswith("@"):
                                auth_handle = line.split()[0]
                                break

                        verified = bool(await art.query_selector("[data-testid='icon-verified'], svg[aria-label*='Verified']"))

                        img_els = await art.query_selector_all(
                            "[data-testid='tweetPhoto'] img, [aria-label='Image'] img, img[src*='pbs.twimg.com/media/'], [data-testid='card.layoutLarge.media'] img"
                        )
                        media_urls = []
                        media_alts = []
                        for img in img_els:
                            src = await img.get_attribute("src")
                            alt = await img.get_attribute("alt") or ""
                            if src and "profile_images" not in src and "emoji" not in src and "svg" not in src:
                                if "name=" in src:
                                    src = re.sub(r"name=\w+", "name=large", src)
                                if src not in media_urls:
                                    media_urls.append(src)
                                    if alt and alt != "Image":
                                        media_alts.append(alt.strip())

                        vid_els = await art.query_selector_all("[data-testid='videoPlayer'] video, [data-testid='videoComponent'] img")
                        for vid in vid_els:
                            poster = await vid.get_attribute("poster") or await vid.get_attribute("src")
                            if poster and poster not in media_urls:
                                media_urls.append(poster)

                        views_raw = ""
                        view_el = await art.query_selector("a[href*='/analytics'], [aria-label*='views'], [aria-label*='Views']")
                        if view_el:
                            views_raw = await view_el.get_attribute("aria-label") or await view_el.inner_text() or ""

                        likes_raw = ""
                        like_el = await art.query_selector("[data-testid='like']")
                        if like_el:
                            likes_raw = await like_el.get_attribute("aria-label") or await like_el.inner_text() or ""

                        rts_raw = ""
                        rt_el = await art.query_selector("[data-testid='retweet']")
                        if rt_el:
                            rts_raw = await rt_el.get_attribute("aria-label") or await rt_el.inner_text() or ""

                        replies_raw = ""
                        reply_el = await art.query_selector("[data-testid='reply']")
                        if reply_el:
                            replies_raw = await reply_el.get_attribute("aria-label") or await reply_el.inner_text() or ""

                        tweet_url = str(parent_link) if parent_link else ""
                        is_thread = bool("1/" in text or "🧵" in text or "thread" in text.lower())

                        vt = ViralTweet(
                            author=auth_name,
                            handle=auth_handle,
                            verified=verified,
                            text=text,
                            views=_parse_engagement_number(views_raw),
                            likes=_parse_engagement_number(likes_raw),
                            retweets=_parse_engagement_number(rts_raw),
                            replies=_parse_engagement_number(replies_raw),
                            media_urls=media_urls[:4],
                            media_alts=media_alts[:4],
                            tweet_url=tweet_url,
                            is_thread=is_thread,
                            created_at=created_at_iso,
                        )
                        collected_tweets.append(vt)
                    except Exception as parse_err:
                        logger.debug("Error parsing tweet element: %s", parse_err)

                try:
                    await page.evaluate("window.scrollBy(0, 1400)")
                    await asyncio.sleep(2)
                except Exception:
                    break

        await ctx.close()
    except Exception as e:
        logger.warning("Browser deep X research encountered exception: %s", e)
    finally:
        try:
            await mgr.stop()
        except Exception:
            pass

    collected_tweets.sort(key=lambda t: t.views + (t.likes * 10), reverse=True)
    logger.info("Deep X research finished. Gathered %d unique viral tweets.", len(collected_tweets))
    return collected_tweets[:max_tweets]
