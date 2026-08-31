from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import email.utils
import logging
import re
import urllib.parse
from typing import Any

import httpx

logger = logging.getLogger(__name__)


SEARXNG_BASE_URL = "https://search.ajaxhs.duckdns.org"


def _is_recent_date_str(pub_str: str | None, max_age_days: int = 7) -> bool:
    """Checks if a published date string is within the last `max_age_days` (default 7 days)."""
    if not pub_str:
        return True
    
    clean_dt = pub_str.strip()
    now_utc = datetime.now(timezone.utc)
    
    # 1. RFC 2822 format (e.g. "Wed, 27 Aug 2026 14:32:00 GMT")
    try:
        dt = email.utils.parsedate_to_datetime(clean_dt)
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (now_utc - dt).total_seconds() / 86400.0 <= max_age_days
    except Exception:
        pass

    # 2. ISO format (e.g. "2026-08-27T14:32:00Z" or "2026-08-27")
    try:
        iso_clean = clean_dt.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now_utc - dt).total_seconds() / 86400.0 <= max_age_days
    except Exception:
        pass

    return True


async def search_web_grounding(query: str, max_results: int = 4, max_age_days: int = 7) -> list[dict[str, str]]:
    """
    Performs real-time web search to retrieve grounded facts, recent news,
    and verified snippets for named entities and trending topics.
    Strictly restricts results to within the past `max_age_days` (default 7 days).
    Uses SearXNG as primary, with DDGS & Google News fallback.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    # Clean query of emojis or hashtags
    clean_query = re.sub(r"[#@]", "", clean_query)
    clean_query = re.sub(r"[^\w\s\-\.\'\"]", " ", clean_query)
    clean_query = " ".join(clean_query.split())[:120]

    results: list[dict[str, str]] = []

    # 1. Primary: SearXNG Instance Search with time_range=week
    try:
        searx_url = f"{SEARXNG_BASE_URL}/search"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(
                searx_url,
                params={"q": clean_query, "format": "json", "time_range": "week"},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) XBot/2.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_res = data.get("results", [])
                for r in raw_res:
                    if len(results) >= max_results:
                        break
                    pub_str = r.get("publishedDate") or r.get("published_date") or r.get("date")
                    if pub_str and not _is_recent_date_str(pub_str, max_age_days=max_age_days):
                        continue

                    title = r.get("title", "").strip()
                    content = r.get("content", "").strip()
                    url = r.get("url", "").strip()
                    if title or content:
                        results.append({
                            "title": title,
                            "snippet": content,
                            "url": url,
                            "source": "searxng",
                        })
                if results:
                    logger.info("Retrieved %d recent SearXNG snippets (within 7d) for '%s'", len(results), clean_query)
                    return results
    except Exception as s_err:
        logger.debug("SearXNG search query '%s' fallback triggered: %s", clean_query, s_err)

    # 2. Secondary Fallback: DDGS live web search with timelimit='w' (past week)
    try:
        def _ddgs_run():
            from ddgs import DDGS
            with DDGS() as ddgs:
                return list(ddgs.text(clean_query, timelimit="w", max_results=max_results))

        loop = asyncio.get_running_loop()
        ddg_res = await loop.run_in_executor(None, _ddgs_run)
        if ddg_res:
            for item in ddg_res:
                title = item.get("title", "").strip()
                snippet = item.get("body", "").strip()
                href = item.get("href", "").strip()
                if title or snippet:
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "url": href,
                        "source": "live_web",
                    })
            if results:
                logger.info("Retrieved %d recent live web search snippets for '%s'", len(results), clean_query)
                return results
    except Exception as e:
        logger.debug("DDGS search fallback triggered for '%s': %s", clean_query, e)

    # 3. Fallback: Google News RSS search with when:7d
    try:
        rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(clean_query)}+when:7d&hl=en-IN&gl=IN&ceid=IN:en"
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(rss_url)
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                items = root.findall(".//item")
                for it in items:
                    if len(results) >= max_results:
                        break
                    t_el = it.find("title")
                    l_el = it.find("link")
                    d_el = it.find("pubDate")
                    if d_el is not None and d_el.text:
                        if not _is_recent_date_str(d_el.text, max_age_days=max_age_days):
                            continue

                    if t_el is not None and t_el.text:
                        results.append({
                            "title": t_el.text,
                            "snippet": f"Published: {d_el.text if d_el is not None else 'recent'}",
                            "url": l_el.text if l_el is not None else "",
                            "source": "google_news",
                        })
                if results:
                    logger.info("Retrieved %d Google News snippets for '%s'", len(results), clean_query)
                    return results
    except Exception as ex:
        logger.debug("Google News RSS search failed for '%s': %s", clean_query, ex)

    return results


SOCIAL_SLANG_OR_GROWTH_REGEX = re.compile(
    r"\b(gm|gn|good\s*morning|good\s*night|good\s*afternoon|hello\s*everyone|hey\s*all|happy\s*monday|happy\s*friday|happy\s*weekend|lfg|f4f|mutuals?|follow\s*back|drop\s*(your\s*)?(handle|links?|@)|say\s*yes|let'?s\s*connect|who'?s\s*active|boost\s*(your\s*)?profile|engage\s*with)\b",
    re.IGNORECASE,
)

ENTITY_OR_NEWS_SIGNAL_REGEX = re.compile(
    r"\b(apple|google|nvidia|openai|microsoft|gta|rockstar|nolan|movie|film|trailer|chip|camera|sensor|release|announced|launches|features|model|update|patch|box\s*office|directed|actor|character|series|season|engine|benchmark|gpu|cpu|ios|android|playstation|xbox|anime|one\s*piece|pewpiece|discussingfilm|mkbhd|sama)\b",
    re.IGNORECASE,
)


def extract_search_query_from_text(text: str) -> str:
    """
    Extracts high-signal keywords and named entities from a tweet or trend text
    suitable for web search fact-checking.
    Returns empty string for generic social banter, greetings (GM/GN), or mutuals threads.
    """
    if not text:
        return ""

    # Strip prefixes like "🔥 [TRENDING DEBATE/TOPIC]:" or "🤝 [ACTIVE FOLLOW-BACK / MUTUALS THREAD]:"
    clean = re.sub(r"^\[.*?\]:?", "", text).strip()
    clean = re.sub(r"^[🔥🤝💡🚀🎬🏴‍☠️💻🤖]\s*\[.*?\]:?", "", clean).strip()

    # If starts with greeting, strip leading greeting banter
    clean = re.sub(r"^(gm|gn|good morning|good night|hello|hi|hey|happy monday|happy friday)\b[,\.\!\s]*", "", clean, flags=re.IGNORECASE).strip()

    if not clean:
        return ""

    # Skip social banter / growth threads if no strong news or entity signal
    if SOCIAL_SLANG_OR_GROWTH_REGEX.search(text) and not ENTITY_OR_NEWS_SIGNAL_REGEX.search(clean):
        return ""

    # Require minimum signal: proper nouns (capitalized) or entity/news keywords
    has_proper_nouns = bool(re.search(r"\b[A-Z][a-zA-Z0-9_]{2,}\b", clean))
    has_entity_signal = bool(ENTITY_OR_NEWS_SIGNAL_REGEX.search(clean))
    if not (has_proper_nouns or has_entity_signal):
        return ""

    # Take first sentence or top 8 words
    first_sentence = re.split(r"[\.\?\!\n]", clean)[0]
    words = first_sentence.split()
    if len(words) <= 8:
        return " ".join(words)
    return " ".join(words[:8])


async def ground_context_with_live_facts(topic_or_tweet: str, max_results: int = 3) -> str:
    """
    Generates a structured prompt block with real-time web facts
    to prevent AI hallucinations and keep takes factually accurate.
    """
    query = extract_search_query_from_text(topic_or_tweet)
    if not query:
        return ""

    facts = await search_web_grounding(query, max_results=max_results)
    if not facts:
        return ""

    lines = [
        "## 🔍 Verified Real-Time Web Facts & Grounding (Live Fact-Check)",
        f"- Target Topic Query: \"{query}\"",
        "- Confirmed Live Web Search Verification:",
    ]
    for i, f in enumerate(facts, 1):
        lines.append(f"  {i}. **{f['title']}**: {f['snippet']}")

    lines.extend([
        "",
        "### 🛡️ Real-Time Fact-Check & Accuracy Guardrails:",
        "1. **Strictly adhere to verified facts**: Reference only accurate names, confirmed specs, and real timeline dates.",
        "2. **No Hallucinations**: Never invent unannounced release dates, nonexistent product specs, or false lore.",
        "3. **Distinguish Rumor vs Fact**: If the topic is an unconfirmed rumor, frame your take as community speculation/theory rather than stating it as a confirmed reality.",
        "4. **Strict Recency**: Reference only events, updates, and discussions occurring within the past 7 days. Reject historical anecdotes or ancient claims.",
        "",
    ])

    return "\n".join(lines)
