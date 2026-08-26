"""
Deep Topic Research & Scraping Engine for X (Twitter) and Web.
Expands raw topics into high-intent search phrases, navigates to X Top/Latest search,
scrapes and parses 20-30 viral posts with media, captions, sentiment, and metrics,
downloads visual assets, and grounds facts via live web search.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.ai.fact_grounder import search_web_grounding
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)

MEDIA_STORAGE_DIR = Path("/home/ubuntu/projects/xbot/data/media/threads")
MEDIA_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class ViralTweet(BaseModel):
    author: str = ""
    handle: str = ""
    verified: bool = False
    text: str = ""
    views: int = 0
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    media_urls: list[str] = Field(default_factory=list)
    media_alts: list[str] = Field(default_factory=list)
    tweet_url: str = ""
    is_thread: bool = False


class DownloadedMedia(BaseModel):
    local_path: str
    source_url: str
    caption: str
    author_handle: str = ""


class TopicResearchReport(BaseModel):
    topic: str
    search_queries: list[str] = Field(default_factory=list)
    viral_tweets: list[ViralTweet] = Field(default_factory=list)
    key_facts: list[str] = Field(default_factory=list)
    community_sentiment: dict[str, Any] = Field(default_factory=dict)
    top_hashtags: list[str] = Field(default_factory=list)
    top_media_urls: list[str] = Field(default_factory=list)
    downloaded_media: list[DownloadedMedia] = Field(default_factory=list)
    summary: str = ""


def _parse_engagement_number(text: str) -> int:
    """Parses raw engagement text (e.g. '12.4K', '1.2M', '534') to an integer."""
    if not text:
        return 0
    clean = text.replace(",", "").strip().upper()
    match = re.search(r"([\d\.]+)\s*([KM]?)", clean)
    if not match:
        return 0
    num_str, mult = match.groups()
    try:
        val = float(num_str)
        if mult == "K":
            return int(val * 1000)
        elif mult == "M":
            return int(val * 1000000)
        return int(val)
    except Exception:
        return 0


async def generate_search_phrases(topic: str, persona: Persona | None = None, client: Any = None) -> list[str]:
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
        f"- Do NOT use AND, OR, NOT, or boolean operators.\n"
        f"- Use exact brand/celebrity/topic keywords (e.g., 'Kriti Sanon GIVA', 'Kriti Sanon ad', 'GIVA controversy').\n"
        f"- Keep each query between 2 and 4 words.\n"
        f"- Return ONLY a valid JSON array of 3 strings. Example: [\"Query 1\", \"Query 2\", \"Query 3\"]"
    )

    try:
        raw_resp = await client.chat.completions.create(
            model=settings.MODEL_TREND_ANALYSIS,
            messages=[
                {"role": "system", "content": "You are a specialized search query optimizer for X/Twitter. Respond ONLY with a JSON array."},
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
) -> list[ViralTweet]:
    """
    Navigates to X Top Search (`f=top`) using Playwright to scrape up to 20-30 viral posts
    with full texts, engagement metrics, and media image URLs.
    """
    from xbot.browser.manager import BrowserManager
    
    collected_tweets: list[ViralTweet] = []
    seen_texts: set[str] = set()

    mgr = BrowserManager(base_profile_dir=Path("/home/ubuntu/projects/xbot/data/profiles"))
    try:
        await mgr.start()
        ctx = await mgr.get_context(profile_slug)
        page = await ctx.new_page()

        for q in queries:
            if len(collected_tweets) >= max_tweets:
                break

            url = f"https://x.com/search?q={urllib.parse.quote_plus(q)}&f=top"
            logger.info("Deep X Research navigating to: %s", url)
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

                        img_els = await art.query_selector_all("[data-testid='tweetPhoto'] img, [aria-label='Image'] img")
                        media_urls = []
                        media_alts = []
                        for img in img_els:
                            src = await img.get_attribute("src")
                            alt = await img.get_attribute("alt") or ""
                            if src and "profile_images" not in src and "emoji" not in src and "svg" not in src:
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

                        time_el = await art.query_selector("time")
                        parent_link = None
                        if time_el:
                            parent_link = await time_el.evaluate("el => el.closest('a')?.href")
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


async def download_viral_media(
    tweets: list[ViralTweet],
    topic_slug: str,
    max_images: int = 3,
) -> list[DownloadedMedia]:
    """
    Downloads the top high-res images from viral tweets to the local media folder
    `data/media/threads/{topic_slug}/` for dashboard preview and tweet attachment.
    """
    downloaded: list[DownloadedMedia] = []
    target_dir = MEDIA_STORAGE_DIR / topic_slug
    target_dir.mkdir(parents=True, exist_ok=True)

    seen_urls: set[str] = set()

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for tw in tweets:
            if len(downloaded) >= max_images:
                break
            for img_url in tw.media_urls:
                if len(downloaded) >= max_images:
                    break
                if img_url in seen_urls:
                    continue
                seen_urls.add(img_url)

                try:
                    clean_url = img_url
                    if "name=" in clean_url:
                        clean_url = re.sub(r"name=\w+", "name=large", clean_url)
                    
                    url_hash = hashlib.md5(clean_url.encode()).hexdigest()[:8]
                    ext = ".jpg"
                    if "format=png" in clean_url:
                        ext = ".png"
                    
                    file_name = f"{topic_slug}_{url_hash}{ext}"
                    local_file = target_dir / file_name

                    resp = await client.get(clean_url)
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        with open(local_file, "wb") as f:
                            f.write(resp.content)
                        
                        caption = tw.text[:120].replace("\n", " ")
                        downloaded.append(DownloadedMedia(
                            local_path=str(local_file.resolve()),
                            source_url=clean_url,
                            caption=caption,
                            author_handle=tw.handle,
                        ))
                        logger.info("Downloaded viral media asset to %s", local_file)
                except Exception as dl_err:
                    logger.debug("Failed downloading image %s: %s", img_url, dl_err)

    return downloaded


async def research_topic_comprehensively(
    topic: str,
    persona: Persona | None = None,
    max_tweets: int = 25,
    profile_slug: str = "test_profile1",
    client: Any = None,
) -> TopicResearchReport:
    """
    Executes the end-to-end Topic Research Pipeline:
    1. AI query expansion & phrasing.
    2. Live X Top Search scraping of 20-30 viral tweets + media.
    3. Web search fact-grounding via SearXNG / Google News.
    4. Downloads top viral images with captions.
    5. Synthesizes key facts, community sentiment, and debate angles.
    """
    clean_topic = topic.strip()
    slug = re.sub(r"[^\w]+", "_", clean_topic.lower())[:30].strip("_") or "topic"

    if client is None:
        client = get_ai_client()

    # Step 1: AI Search Phrases
    queries = await generate_search_phrases(clean_topic, persona=persona, client=client)
    logger.info("Generated X research queries for '%s': %s", clean_topic, queries)

    # Step 2: Concurrently execute Live X Search and Web Search
    x_search_task = scrape_x_top_tweets(queries, max_tweets=max_tweets, profile_slug=profile_slug)
    web_grounding_task = search_web_grounding(clean_topic, max_results=5)

    viral_tweets, web_snippets = await asyncio.gather(x_search_task, web_grounding_task)

    # Step 3: Extract top media URLs and download top assets
    all_media_urls: list[str] = []
    for tw in viral_tweets:
        for m in tw.media_urls:
            if m not in all_media_urls:
                all_media_urls.append(m)

    downloaded_media = await download_viral_media(viral_tweets, topic_slug=slug, max_images=3)

    # Step 4: Extract Key Facts from web grounding & tweets
    key_facts: list[str] = []
    for snip in web_snippets:
        if snip.get("snippet"):
            key_facts.append(f"{snip.get('title', '')}: {snip.get('snippet', '')}")

    # Step 5: Synthesize Community Sentiment & Debate Angles via LLM
    sentiment_dict: dict[str, Any] = {
        "total_posts_analyzed": len(viral_tweets),
        "total_impressions_scanned": sum(tw.views for tw in viral_tweets),
        "total_likes_scanned": sum(tw.likes for tw in viral_tweets),
        "primary_debates": [],
        "consensus_view": "",
        "contrarian_view": "",
    }

    sample_text_lines = []
    for idx, tw in enumerate(viral_tweets[:12], 1):
        sample_text_lines.append(f"[{idx}] @{tw.handle} ({tw.views} views, {tw.likes} likes): {tw.text}")

    tweets_blob = "\n".join(sample_text_lines)
    facts_blob = "\n".join(key_facts[:4])

    summary_prompt = (
        f"You are a cultural intelligence director analyzing real-time discourse on X.\n"
        f"Topic: \"{clean_topic}\"\n\n"
        f"Verified News Facts:\n{facts_blob}\n\n"
        f"Top Viral Tweets on X:\n{tweets_blob}\n\n"
        f"Provide a structured JSON summary with:\n"
        f"1. \"summary\": 2-3 sentences explaining what happened, why it blew up, and the current state.\n"
        f"2. \"consensus_view\": The dominant public reaction or mainstream opinion on X.\n"
        f"3. \"contrarian_view\": The sharp counter-perspective, industry critique, or alternative take.\n"
        f"4. \"key_debates\": Array of 3 distinct bullet points showing the core fault lines of the argument.\n\n"
        f"Respond ONLY with valid JSON."
    )

    summary_text = ""
    try:
        raw_sum = await client.chat.completions.create(
            model=settings.MODEL_TREND_ANALYSIS,
            messages=[
                {"role": "system", "content": "You are a cultural trend and discourse analyst. Output ONLY valid JSON."},
                {"role": "user", "content": summary_prompt},
            ],
            max_tokens=350,
            temperature=0.3,
        )
        content_sum = raw_sum.choices[0].message.content or ""
        cleaned_sum = content_sum.strip()
        if "```json" in cleaned_sum:
            cleaned_sum = cleaned_sum.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned_sum:
            cleaned_sum = cleaned_sum.split("```")[1].split("```")[0].strip()
        
        sum_data = json.loads(cleaned_sum)
        summary_text = sum_data.get("summary", "")
        sentiment_dict["consensus_view"] = sum_data.get("consensus_view", "")
        sentiment_dict["contrarian_view"] = sum_data.get("contrarian_view", "")
        sentiment_dict["primary_debates"] = sum_data.get("key_debates", [])
    except Exception as e:
        logger.debug("Sentiment summary parsing fallback for '%s': %s", clean_topic, e)
        summary_text = f"Live discussion and viral discourse on X surrounding {clean_topic} across {len(viral_tweets)} popular posts."

    # Extract authentic hashtags from the scraped viral tweets
    hashtag_counts: dict[str, int] = {}
    for tw in viral_tweets:
        found_tags = re.findall(r"#\w+", tw.text)
        for tag in found_tags:
            tag_clean = tag.strip()
            if len(tag_clean) > 2:
                hashtag_counts[tag_clean] = hashtag_counts.get(tag_clean, 0) + 1
    top_hashtags = sorted(hashtag_counts.keys(), key=lambda t: hashtag_counts[t], reverse=True)[:3]

    report = TopicResearchReport(
        topic=clean_topic,
        search_queries=queries,
        viral_tweets=viral_tweets,
        key_facts=key_facts,
        community_sentiment=sentiment_dict,
        top_hashtags=top_hashtags,
        top_media_urls=all_media_urls[:10],
        downloaded_media=downloaded_media,
        summary=summary_text,
    )
    logger.info("Synthesized comprehensive TopicResearchReport for '%s' with %d viral tweets, %d hashtags, and %d downloaded media assets.",
                clean_topic, len(viral_tweets), len(top_hashtags), len(downloaded_media))
    return report
