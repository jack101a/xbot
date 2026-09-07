from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any

from xbot.ai.client import get_ai_client
from xbot.ai.fact_grounder import search_web_grounding
from xbot.config import settings
from xbot.persona.loader import Persona

from .crawler import generate_search_phrases, scrape_x_top_tweets
from .extractor import (
    DownloadedMedia,
    TopicResearchReport,
    ViralTweet,
    download_viral_media,
)

logger = logging.getLogger(__name__)


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
    import sys
    mod = sys.modules.get("xbot.ai.x_researcher")
    _gen_phrases = getattr(mod, "generate_search_phrases", generate_search_phrases) if mod else generate_search_phrases
    _scrape_x = getattr(mod, "scrape_x_top_tweets", scrape_x_top_tweets) if mod else scrape_x_top_tweets
    _search_web = getattr(mod, "search_web_grounding", search_web_grounding) if mod else search_web_grounding
    _dl_media = getattr(mod, "download_viral_media", download_viral_media) if mod else download_viral_media

    queries = await _gen_phrases(clean_topic, persona=persona, client=client)
    logger.info("Generated X research queries for '%s': %s", clean_topic, queries)

    # Step 2: Concurrently execute Live X Search and Web Search
    x_search_task = _scrape_x(queries, max_tweets=max_tweets, profile_slug=profile_slug)
    web_grounding_task = _search_web(clean_topic, max_results=5)

    viral_tweets, web_snippets = await asyncio.gather(x_search_task, web_grounding_task)

    # Step 3: Extract top media URLs and download top assets
    all_media_urls: list[str] = []
    for tw in viral_tweets:
        for m in tw.media_urls:
            if m not in all_media_urls:
                all_media_urls.append(m)

    downloaded_media = await _dl_media(viral_tweets, topic_slug=slug, max_images=3)

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

    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    summary_prompt = (
        f"You are a cultural intelligence director analyzing real-time discourse on X.\n"
        f"Current Date: {now_str}\n"
        f"Topic: \"{clean_topic}\"\n\n"
        f"STRICT RECENCY REQUIREMENT: All analyzed facts, viral posts, and commentary must be strictly from within the past 7 days. Reject any historical anecdotes or ancient claims older than 1 week.\n\n"
        f"Verified News Facts (Past 7 Days):\n{facts_blob}\n\n"
        f"Top Viral Tweets on X (Past 7 Days):\n{tweets_blob}\n\n"
        f"Provide a structured JSON summary with:\n"
        f"1. \"summary\": 2-3 sentences explaining what happened recently (within 7 days), why it blew up, and the current state.\n"
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
                {
                    "role": "system",
                    "content": "You are a cultural trend and discourse analyst. Output ONLY valid JSON.",
                },
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
    logger.info(
        "Synthesized comprehensive TopicResearchReport for '%s' with %d viral tweets, %d hashtags, and %d downloaded media assets.",
        clean_topic,
        len(viral_tweets),
        len(top_hashtags),
        len(downloaded_media),
    )
    return report
