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
from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest
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

    now_year = datetime.now().year
    prompt = (
        f"You are a master social media researcher on X (Twitter).\n"
        f"Active Calendar Year: {now_year}. All queries must reflect events and buzz in {now_year}.\n"
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
    container: Container | None = None,
) -> list[ViralTweet]:
    """
    Scrapes top viral posts via BrowserPort for the given queries.
    Strictly filters out any posts older than max_age_days.
    """
    c = container or get_container()
    collected_tweets: list[ViralTweet] = []
    seen_texts: set[str] = set()

    now_utc = datetime.now(timezone.utc)
    since_date = (now_utc - timedelta(days=max_age_days)).strftime("%Y-%m-%d")

    for q in queries:
        if len(collected_tweets) >= max_tweets:
            break

        search_query = q
        if not any(op in search_query for op in ("min_faves:", "filter:", "-filter:")):
            from xbot.search import SearchMatrixStrategy
            builder = SearchMatrixStrategy.create_viral_anchor_query(q, min_faves=50, max_age_days=max_age_days)
            search_query = builder.build_query_string()
        elif "since:" not in search_query:
            search_query = f"{q} since:{since_date}"

        search_req = BrowserRequest(
            profile_slug=profile_slug,
            action=BrowserActionType.SEARCH,
            params={"query": search_query},
            timeout_seconds=45,
        )
        try:
            res = await c.browser.execute(search_req)
            if res.status == "success":
                raw_results = (
                    (res.scrape.raw.get("results") if (res.scrape and res.scrape.raw) else None)
                    or (res.action_result.raw.get("results") if (res.action_result and res.action_result.raw) else None)
                    or []
                )
                for item in raw_results:
                    if len(collected_tweets) >= max_tweets:
                        break
                    text = item.get("text", "")
                    if not text or len(text) < 15:
                        continue
                    norm_key = re.sub(r"\W+", "", text.lower())[:50]
                    if norm_key in seen_texts:
                        continue
                    seen_texts.add(norm_key)

                    collected_tweets.append(
                        ViralTweet(
                            tweet_id=item.get("tweet_id") or str(uuid.uuid4())[:8],
                            author=item.get("author") or "creator",
                            handle=item.get("handle") or "creator",
                            text=text,
                            tweet_url=item.get("tweet_url") or item.get("url"),
                            likes=int(item.get("likes") or 0),
                            retweets=int(item.get("retweets") or 0),
                            replies=int(item.get("replies") or 0),
                            views=int(item.get("views") or 0),
                            media_urls=item.get("media_urls") or [],
                        )
                    )
        except Exception as search_err:
            logger.warning("BrowserPort search error for '%s': %s", q, search_err)

    collected_tweets.sort(key=lambda t: t.views + (t.likes * 10), reverse=True)
    logger.info("Deep X research finished. Gathered %d unique viral tweets.", len(collected_tweets))
    return collected_tweets[:max_tweets]
