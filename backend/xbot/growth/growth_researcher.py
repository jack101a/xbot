"""
Autonomous Follow Growth Researcher Engine for XBot Pro.

Executes periodically (every 3 days):
1. Searches X for top-performing 'follow for follow' / growth posts.
2. Scrapes the top 10-15 posts including tweet copy, authors, hashtags, and media attachments.
3. Sends all scraped posts in a single unified batch to ChatGPT Web Bridge.
4. ChatGPT synthesizes high-converting copy archetypes, winning hashtags, and 3D conceptual visual concepts.
5. Persists the discovered ideas to disk (data/growth_research/f4f_growth_ideas.json) to dynamically
   refresh and inspire the prompt generator and 3D image generator.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
from pathlib import Path
import random
import re
import time
from typing import Any

from xbot.ai.chatgpt_adapter import get_chatgpt_instance, _bridge_lock
from xbot.ai.client import get_ai_client
from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.container import Container, get_container
from xbot.contracts.browser import BrowserActionType, BrowserRequest

logger = logging.getLogger(__name__)

RESEARCH_INTERVAL_SECONDS = 3 * 24 * 60 * 60  # 3 days = 259,200 seconds
REDIS_KEY_LAST_RESEARCH = "xbot:growth_research:last_run_ts"
IDEAS_CACHE_DIR = Path("data/growth_research")
IDEAS_CACHE_FILE = IDEAS_CACHE_DIR / "f4f_growth_ideas.json"


def is_growth_research_due(r: Any | None = None) -> bool:
    """Checks if 3 days have elapsed since the last F4F growth research run."""
    if not IDEAS_CACHE_FILE.exists():
        return True

    if r:
        try:
            last_ts_str = r.get(REDIS_KEY_LAST_RESEARCH)
            if last_ts_str:
                last_ts = int(last_ts_str)
                now_ts = int(time.time())
                return (now_ts - last_ts) >= RESEARCH_INTERVAL_SECONDS
        except (ValueError, TypeError):
            pass

    # Fallback to file modification time
    try:
        file_mtime = int(IDEAS_CACHE_FILE.stat().st_mtime)
        return (int(time.time()) - file_mtime) >= RESEARCH_INTERVAL_SECONDS
    except Exception:
        return True


async def scrape_f4f_posts_from_x(
    container: Container,
    profile_slug: str,
    query: str = "follow for follow",
    max_posts: int = 15,
) -> list[dict[str, Any]]:
    """
    Executes a search query on X for growth/mutuals posts with media and returns structured post data.
    """
    logger.info("F4FGrowthResearcher: Searching X for '%s' with media (profile: %s, max_posts: %d)...", query, profile_slug, max_posts)
    req = BrowserRequest(
        profile_slug=profile_slug,
        action=BrowserActionType.SEARCH,
        params={
            "query": query,
            "search_filter": "media",
            "auto_relax": False,
            "max_scrolls": 15,
            "min_results": max_posts,
            "require_media": True,
        },
        timeout_seconds=90,
    )

    res = await container.browser.execute(req)
    tweets = []
    if res.scrape and res.scrape.tweets:
        tweets = res.scrape.tweets
    elif res.action_result and isinstance(res.action_result.raw, dict):
        raw_list = res.action_result.raw.get("results") or res.action_result.raw.get("tweets") or []
        tweets = raw_list

    formatted_posts: list[dict[str, Any]] = []
    for item in tweets:
        if hasattr(item, "text"):
            text = (item.text or "").strip()
            author = (item.handle or "").lstrip("@")
            hashtags = item.hashtags or []
            media_urls = item.media_urls or []
            metrics = item.metrics or {}
            likes = metrics.get("likes", getattr(item, "likes", 0))
            retweets = metrics.get("retweets", getattr(item, "retweets", 0))
            replies = metrics.get("replies", getattr(item, "replies", 0))
            media_alts = getattr(item, "media_alts", [])
        elif isinstance(item, dict):
            text = (item.get("text") or "").strip()
            author = (item.get("handle") or item.get("author") or "").lstrip("@")
            hashtags = item.get("hashtags") or []
            media_urls = item.get("media_urls") or []
            metrics = item.get("metrics") or {}
            likes = metrics.get("likes") or item.get("likes", 0)
            retweets = metrics.get("retweets") or item.get("retweets", 0)
            replies = metrics.get("replies") or item.get("replies", 0)
            media_alts = item.get("media_alts") or []
        else:
            continue

        if not text or len(text) < 15:
            continue

        # Strictly enforce that media is attached
        if not media_urls:
            continue

        # Deduplicate
        if any(p["text"] == text for p in formatted_posts):
            continue

        formatted_posts.append({
            "text": text,
            "author": author,
            "hashtags": hashtags,
            "media_urls": media_urls,
            "media_alts": media_alts,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
        })

        if len(formatted_posts) >= max_posts:
            break

    logger.info("F4FGrowthResearcher: Scraped %d posts WITH MEDIA from X search '%s'.", len(formatted_posts), query)
    return formatted_posts


async def synthesize_growth_ideas_with_chatgpt(
    scraped_posts: list[dict[str, Any]],
    client: Any | None = None,
) -> dict[str, Any]:
    """
    Submits all 10-15 scraped posts in a single prompt to ChatGPT to synthesize
    novel post writing ideas, growth archetypes, and 3D conceptual visual prompts.
    """
    if not scraped_posts:
        logger.warning("F4FGrowthResearcher: No posts provided for synthesis.")
        return {}

    post_summaries = []
    for idx, p in enumerate(scraped_posts, 1):
        media_list = p.get("media_urls", [])
        media_desc = f"{len(media_list)} image(s)/media: " + ", ".join(media_list[:2]) if media_list else "None"
        alts = p.get("media_alts", [])
        alts_desc = f" (Alt context: {', '.join(alts)})" if alts else ""
        tags_desc = ", ".join(p.get("hashtags", [])) if p.get("hashtags") else "None"
        likes = p.get("likes", 0)
        retweets = p.get("retweets", 0)
        replies = p.get("replies", 0)
        post_summaries.append(
            f"--- POST {idx} (Author: @{p['author']} | Likes: {likes} | Retweets: {retweets} | Replies: {replies}) ---\n"
            f"Tweet Copy:\n{p['text']}\n"
            f"Hashtags: {tags_desc}\n"
            f"Attached Media: {media_desc}{alts_desc}\n"
        )

    joined_posts = "\n".join(post_summaries)

    system_prompt = """You are the Chief Social Growth Strategist and Creative 3D Art Director for XBot Pro.
Your task is to analyze top-performing 'follow for follow' and creator community growth posts scraped live from X (with their text and attached media).

Synthesize actionable creative insights to update our autonomous Growth Post Generator and 3D Image Engine.

IMAGE CONSTRAINTS (MANDATORY & NON-NEGOTIABLE):
1. ZERO REALISTIC HUMANS: Under NO circumstances should any image prompt describe a realistic person, man, woman, human face, skin, hands, or photorealistic human figures.
2. 3D CONCEPTUAL ARTWORK: All visual prompts must describe modern 3D conceptual designs, futuristic UI cards, glowing 'Follow' interaction buttons, ascending community network graphs, and milestone badges.
3. NO HEAVY CINEMATIC DRAMA: Clean, crisp, vibrant modern 3D studio lighting with sleek dark-mode glassmorphism (#0A0E17).

HASHTAG CONSTRAINTS:
Prioritize high-converting growth tags like #F4F, #500Followers, #FollowForFollow, #FollowBack, #FollowTrain, #Mutuals.

Return ONLY a valid JSON object matching this schema:
{
  "analyzed_posts_count": <int>,
  "winning_hashtags": ["#F4F", "#500Followers", "#FollowForFollow", "#FollowBack", ...],
  "discovered_archetypes": [
    {
      "name": "CREATOR_MUTUALS_CIRCLE",
      "description": "Brief description of the copy angle",
      "directive": "Instructions for LLM on tone, message, and call to action",
      "hook_example": "Example hook opening"
    }
  ],
  "discovered_image_concepts": [
    {
      "title": "Glowing Follow Beacon",
      "prompt": "Detailed 3D conceptual prompt (zero humans, glowing follow button, network nodes, crisp studio lighting)"
    }
  ],
  "high_converting_ctas": [
    "Drop your current project below—connecting with everyone who replies.",
    ...
  ],
  "key_insights": [
    "Insight on what works best right now on X for follow growth",
    ...
  ]
}
"""

    user_prompt = f"""Here are {len(scraped_posts)} live follow-for-follow growth posts (all with attached images/media) scraped directly from X:

{joined_posts}

Analyze all {len(scraped_posts)} posts together at once.
Pay close attention to:
1. The copy hooks, phrasing, follower milestones (e.g. 500, 1K), and calls-to-action that creators use.
2. The hashtags that drive engagement (#F4F, #500Followers, #FollowForFollow, #FollowBack, #Mutuals, etc.).
3. The visual themes and imagery used to represent growth, mutual connections, follower milestones, and community building.

From your analysis, synthesize:
- Winning growth hashtags.
- 5 high-converting copy archetypes with hook examples.
- 5 innovative 3D conceptual image prompts designed specifically for follow/growth posts (STRICTLY adhering to: zero realistic humans, no photorealistic people/faces/hands, modern sleek dark-mode glassmorphism #0A0E17, luminous 3D follow buttons, ascending community network nodes, milestone badges, crisp vibrant studio lighting, no heavy cinematic drama).
- High-converting CTAs.
- Key growth insights from the analyzed posts.
"""

    response_text = ""
    # Try ChatGPT Web Bridge first
    try:
        logger.info("F4FGrowthResearcher: Sending batch of %d posts to ChatGPT Web Bridge...", len(scraped_posts))
        async with _bridge_lock:
            bridge = get_chatgpt_instance()
            combined_prompt = f"=== SYSTEM DIRECTIVE ===\n{system_prompt}\n\n=== USER INPUT ===\n{user_prompt}"
            bridge_res = await bridge.ask(prompt=combined_prompt)
            response_text = bridge_res.get("text") or ""
    except Exception as bridge_err:
        logger.warning("F4FGrowthResearcher: ChatGPT Web Bridge failed (%s); falling back to AI client cascade...", bridge_err)

    # Fallback to LLM client cascade if ChatGPT Web Bridge was unavailable
    if not response_text:
        ai_client = client or get_ai_client()
        model_cascade = getattr(
            settings, "MODEL_POST_CREATION", "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731"
        )
        try:
            llm_res = await ai_client.chat.completions.create(
                model=model_cascade,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=2500,
            )
            response_text = llm_res.choices[0].message.content or ""
        except Exception as llm_err:
            logger.error("F4FGrowthResearcher: LLM fallback also failed: %s", llm_err)
            return {}

    # Extract JSON
    clean_json = response_text.strip()
    if "```" in clean_json:
        clean_json = re.sub(r"^```(?:json)?", "", clean_json, flags=re.MULTILINE)
        clean_json = re.sub(r"```$", "", clean_json, flags=re.MULTILINE).strip()

    start_idx = clean_json.find("{")
    end_idx = clean_json.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        clean_json = clean_json[start_idx : end_idx + 1]

    try:
        data = json.loads(clean_json, strict=False)
        data["analyzed_posts_count"] = len(scraped_posts)
        data["researched_at"] = datetime.datetime.utcnow().isoformat()
        data["scraped_sample_posts"] = [
            {
                "author": p["author"],
                "text": p["text"][:140] + ("..." if len(p["text"]) > 140 else ""),
                "media_urls": p.get("media_urls", []),
                "hashtags": p.get("hashtags", []),
                "likes": p.get("likes", 0),
                "retweets": p.get("retweets", 0),
            }
            for p in scraped_posts
        ]
        return data
    except Exception as parse_err:
        logger.warning("F4FGrowthResearcher: Failed to parse JSON response: %s", parse_err)
        return {}


def save_growth_ideas(ideas: dict[str, Any], output_path: Path | str | None = None) -> Path:
    """Persists synthesized growth ideas to disk for the prompt generator to load."""
    target_file = Path(output_path) if output_path else IDEAS_CACHE_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(json.dumps(ideas, indent=2), encoding="utf-8")
    logger.info("F4FGrowthResearcher: Successfully saved synthesized growth ideas to %s", target_file)
    return target_file


async def run_f4f_growth_research(
    profile_slug: str = "test_profile1",
    force: bool = False,
    container: Container | None = None,
    target_posts: int = 15,
) -> dict[str, Any]:
    """
    Main orchestrator for the 3-day Follow Growth Idea Discovery cycle.
    Ensures 10 to 15 posts with media are scraped and sent in a single batch to ChatGPT.
    """
    c = container or get_container()
    guard = getattr(c, "guard", None)
    r = getattr(guard, "r", None)

    # Check 3-day frequency gate
    if not force and not is_growth_research_due(r):
        logger.info("F4FGrowthResearcher: Research cycle not due yet (3-day interval active). Skipping.")
        return {"status": "skipped", "reason": "3_day_cooldown_active"}

    logger.info("F4FGrowthResearcher: Starting autonomous 3-day F4F idea discovery cycle (target: 10-15 posts with media)...")

    min_required = 10
    # 1. Scrape top posts with media from X
    scraped = await scrape_f4f_posts_from_x(
        container=c,
        profile_slug=profile_slug,
        query="follow for follow",
        max_posts=target_posts,
    )

    # If fewer than min_required (10), try secondary queries to top up to 10-15 posts
    top_up_queries = ["f4f follow back", "mutuals follow back", "follow for follow back"]
    for q in top_up_queries:
        if len(scraped) >= min_required:
            break
        needed = target_posts - len(scraped)
        logger.info(
            "F4FGrowthResearcher: Currently have %d posts with media. Running top-up query '%s' for %d more...",
            len(scraped),
            q,
            needed,
        )
        additional = await scrape_f4f_posts_from_x(
            container=c,
            profile_slug=profile_slug,
            query=q,
            max_posts=needed,
        )
        for post in additional:
            if not any(p["text"] == post["text"] for p in scraped):
                scraped.append(post)
            if len(scraped) >= target_posts:
                break

    if not scraped:
        logger.warning("F4FGrowthResearcher: Could not scrape any posts with media from X. Aborting.")
        return {"status": "failed", "reason": "no_posts_scraped"}

    logger.info("F4FGrowthResearcher: Collected %d posts with media. Sending all to ChatGPT for batch analysis...", len(scraped))

    # 2. Batch synthesis via ChatGPT
    ideas = await synthesize_growth_ideas_with_chatgpt(scraped)
    if not ideas:
        logger.warning("F4FGrowthResearcher: Synthesis returned empty ideas.")
        return {"status": "failed", "reason": "synthesis_failed"}

    # 3. Save to disk
    save_growth_ideas(ideas)

    # 4. Update Redis timestamp
    now_ts = int(time.time())
    if r:
        try:
            r.set(REDIS_KEY_LAST_RESEARCH, str(now_ts), ex=RESEARCH_INTERVAL_SECONDS * 2)
        except Exception as red_err:
            logger.debug("Could not set Redis research timestamp: %s", red_err)

    logger.info(
        "F4FGrowthResearcher: Cycle completed! Analyzed %d posts with media. Discovered %d archetypes, %d image concepts.",
        len(scraped),
        len(ideas.get("discovered_archetypes", [])),
        len(ideas.get("discovered_image_concepts", [])),
    )

    return {
        "status": "success",
        "scraped_count": len(scraped),
        "archetypes_count": len(ideas.get("discovered_archetypes", [])),
        "image_concepts_count": len(ideas.get("discovered_image_concepts", [])),
        "winning_hashtags": ideas.get("winning_hashtags", []),
    }


@celery_app.task(name="xbot.growth.growth_researcher.run_f4f_growth_research_task")
def run_f4f_growth_research_task(profile_slug: str = "test_profile1", force: bool = False) -> dict[str, Any]:
    """Celery entrypoint for periodic 3-day F4F growth research."""
    return asyncio.run(run_f4f_growth_research(profile_slug=profile_slug, force=force))
