"""
AI Multi-Tweet Thread Generator for X (Twitter).
Synthesizes high-retention 3-6 tweet threads using the 3-Tier Viral Formula:
- Tweet 1: The Viral Hook (Scroll-stop premise + thesis + value promise)
- Tweets 2 to (N-1): Atomic Value Nuggets (1 concept per tweet with clean bullets)
- Tweet N: The Conversion Closer (Executive summary + bookmark/repost CTA + open question)

Enforces strict Anti-AI typography, sentence casing, and zero buzzwords via AntiAIGatekeeper.
Features Deep X Topic Research: parses 20-30 viral tweets, metrics, media images, and public sentiment.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper, ANTI_AI_TYPOGRAPHY_DIRECTIVE
from xbot.ai.client import get_ai_client
from xbot.ai.x_researcher import research_topic_comprehensively, TopicResearchReport
from xbot.config import settings
from xbot.persona.loader import Persona
from xbot.schemas.thread import ThreadItemCreate

logger = logging.getLogger(__name__)


from xbot.ai.thread_models import (
    GeneratedThreadItem,
    GeneratedThreadPayload,
    GeneratedThreadResponse,
)

async def generate_thread(
    topic: str,
    persona: Persona | None = None,
    num_tweets: int = 4,
    archetype: str = "Framework",
    deep_research: bool = True,
    profile_slug: str = "test_profile1",
    client: Any = None,
) -> GeneratedThreadResponse:
    """
    Generates an authentic, high-retention multi-tweet thread on the given topic.
    If deep_research is True, actively conducts live research on X & Web (scraping 20-30 viral posts & media).
    Validates every tweet part through AntiAIGatekeeper.
    """
    num_tweets = max(3, min(6, num_tweets))
    gatekeeper = AntiAIGatekeeper()

    research_report: TopicResearchReport | None = None
    research_context_blob = ""

    if deep_research:
        try:
            logger.info("Conducting deep live X research for thread topic '%s'...", topic)
            research_report = await research_topic_comprehensively(
                topic=topic,
                persona=persona,
                max_tweets=20,
                profile_slug=profile_slug,
                client=client,
            )
            
            # Format research grounding for LLM
            lines = [
                f"### Live Research on X & Web for Topic: \"{research_report.topic}\"",
                f"- Fact Summary: {research_report.summary}",
            ]
            if research_report.community_sentiment:
                cs = research_report.community_sentiment
                if cs.get("consensus_view"):
                    lines.append(f"- Dominant Reaction on X (Consensus): {cs.get('consensus_view')}")
                if cs.get("contrarian_view"):
                    lines.append(f"- Contrarian / Industry Take: {cs.get('contrarian_view')}")
                if cs.get("primary_debates"):
                    lines.append(f"- Core Debate Angles: {'; '.join(cs.get('primary_debates', []))}")
            
            if getattr(research_report, "top_hashtags", None) and len(research_report.top_hashtags) > 0:
                lines.append(f"\nAuthentic Researched Community Hashtags on X: {', '.join(research_report.top_hashtags[:2])}")

            if research_report.viral_tweets:
                lines.append("\nTop Viral Tweets Analyzed on X:")
                for idx, tw in enumerate(research_report.viral_tweets[:8], 1):
                    lines.append(f"  {idx}. @{tw.handle} ({tw.views} views, {tw.likes} likes): \"{tw.text}\"")

            if research_report.downloaded_media:
                lines.append("\nAvailable Downloaded Media Assets (Screenshots/Statements):")
                for m in research_report.downloaded_media:
                    lines.append(f"  - Image: {m.source_url} (Caption: {m.caption})")

            research_context_blob = "\n".join(lines)
        except Exception as r_err:
            logger.warning("Deep X research encountered error, proceeding with standard generation: %s", r_err)

    now_date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    system_prompt = (
        "You are an elite, culturally plugged-in digital creator and writer on X (Twitter).\n"
        f"Current Date: {now_date_str}\n"
        "Your sole mission is MAXIMUM GROWTH AND VIRAL RESONANCE by riding the real trending wave on X.\n\n"
        "CORE RULES FOR TRENDING TOPICS:\n"
        "1. STRICT 7-DAY RECENCY: All topics, facts, quotes, events, and context must be strictly from within the past 7 days. Reject and never post historical events, ancient controversies, or old milestones from years/months ago.\n"
        "2. RIDE THE ACTUAL WAVE: Base your take directly on the prevailing sentiment, anger, humor, critique, or celebration from the 20-30 viral posts on X.\n"
        "3. NO PREACHING OR MORALIZING: NEVER lecture the audience, push propaganda, or defend things that the trending community is actively calling out.\n"
        "4. CHANNEL THE AUDIENCE'S VOICE: Use the sharp observations, witty roasts, relatable cynicism, and real details that people on X are enthusiastically liking and retweeting by the thousands.\n"
        "5. 3-TIER CREATOR THREAD FORMULA:\n"
        "   - Tweet 1 (Hook): Hard-hitting, relatable hook capturing the core reason the topic blew up (< 140 chars) with 1 emoji ending in 🧵.\n"
        "   - Tweets 2 to (N-1) (Body): 1 punchy observation or breakdown per tweet with double line breaks (\\n\\n) and clean bullet points (`•` or `-`).\n"
        "   - Tweet N (Closer): Sharp concluding takeaway + open question inviting replies (NEVER use 'TL;DR:' or 'TLDR:') + 1-2 authentic research hashtags.\n\n"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n"
    )

    if persona:
        system_prompt += f"\nPersona: {persona.display_name}. Tone: {persona.personality.communication_style}. Primary Interests: {', '.join(persona.interests.primary)}."

    user_prompt = (
        f"Generate a {num_tweets}-tweet thread for maximum engagement on this trending topic:\n"
        f"Topic: \"{topic}\"\n"
        f"Current Date: {now_date_str} (STRICTLY enforce that all facts and context are from the past 7 days)\n\n"
    )
    if research_context_blob:
        user_prompt += f"=== LIVE X RESEARCH & COMMUNITY SENTIMENT (Past 7 Days from 20-30 Top Viral Posts) ===\n{research_context_blob}\n\n"

    user_prompt += (
        "Instructions:\n"
        "- Base your entire thread on the ACTUAL community sentiment and top viral tweets shown above.\n"
        "- If the public is calling out a brand or celebrity for a tone-deaf campaign, match that critical, witty perspective.\n"
        "- Formatting & Thread Structure:\n"
        f"  • Tweet 1: Hook (< 140 chars) with 1 emoji ending in '🧵 1/{num_tweets}'.\n"
        f"  • Tweets 2 to {num_tweets-1}: Numbered '2/{num_tweets}', '3/{num_tweets}' etc. Include 1-2 natural emojis (e.g. 🍿, 💀, 🤌, 👀, ☕, 📈) and clean line breaks (\\n\\n).\n"
        f"  • Tweet {num_tweets} (Closer): Numbered '{num_tweets}/{num_tweets}', concluding punchy takeaway + question + 1-2 authentic research hashtags.\n"
        "- Every single tweet MUST be under 260 characters.\n"
        "- Every sentence MUST start with standard Sentence Case capitalization.\n"
        "- Never use emojis as bullet headers (use '• ' or '- ').\n"
        "- Zero corporate AI clichés ('supercharge', 'unleash', 'delve', 'game-changer', 'let that sink in').\n\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        "  \"topic\": \"" + topic + "\",\n"
        "  \"hook_score\": 95,\n"
        "  \"tweets\": [\n"
        "    {\"position\": 0, \"item_type\": \"hook\", \"text\": \"...\"},\n"
        "    {\"position\": 1, \"item_type\": \"body\", \"text\": \"...\"},\n"
        "    {\"position\": 2, \"item_type\": \"closer\", \"text\": \"...\"}\n"
        "  ]\n"
        "}"
    )

    if client is None:
        client = get_ai_client()

    model = getattr(settings, "MODEL_POST_CREATION", "litellm/gemini-3.1-flash-lite,litellm/gemini-flash-latest")

    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        content_str = completion.choices[0].message.content or ""
        
        # Clean JSON markdown fences
        clean_json = content_str.strip()
        if "```" in clean_json:
            clean_json = re.sub(r"^```(?:json)?", "", clean_json).rstrip("`").strip()

        data = json.loads(clean_json)
        raw_items = data.get("tweets", [])

        if not raw_items or len(raw_items) < 2:
            logger.warning("Thread generation failed: Fewer than 2 items produced by AI. Discarding without template fallback.")
            return None

        items: list[ThreadItemCreate] = []
        tweet_texts: list[str] = []

        # Map top downloaded media if available or generate guaranteed visual graphic
        top_media_url = None
        dl_media = []
        if research_report and len(research_report.downloaded_media) > 0:
            top_media_url = research_report.downloaded_media[0].local_path
            dl_media = [m.model_dump() for m in research_report.downloaded_media]
        else:
            # Generate rich 4:5 visual graphic fallback so media is ALWAYS present
            try:
                from xbot.ai.visual_engine import generate_visual_post_spec
                from xbot.ai.meme_renderer import render_visual_spec_to_image
                v_spec = await generate_visual_post_spec(topic=topic, persona=persona, client=client)
                if v_spec:
                    rendered_path = render_visual_spec_to_image(v_spec.model_dump())
                    if rendered_path and os.path.exists(rendered_path):
                        abs_p = os.path.abspath(rendered_path)
                        top_media_url = abs_p
                        dl_media.append({
                            "local_path": abs_p,
                            "source_url": "visual_engine",
                            "caption": v_spec.image_prompt,
                            "author_handle": persona.x_handle if persona else "xbot",
                        })
            except Exception as v_err:
                logger.warning("Visual fallback media generation error: %s", v_err)

        for idx, item in enumerate(raw_items):
            raw_text = item.get("text", "").strip()
            # Remediate minor typography quirks
            remediated_text = gatekeeper.remediate_minor_issues(raw_text)
            
            # Length guard
            if len(remediated_text) > 260:
                remediated_text = remediated_text[:257].rstrip() + "..."

            # Validate with Gatekeeper
            val = gatekeeper.validate(remediated_text)
            if not val.is_valid:
                logger.warning("Thread item %d failed gatekeeper: %s", idx, val.errors)

            item_type = item.get("item_type", "body")
            if idx == 0:
                item_type = "hook"
            elif idx == len(raw_items) - 1:
                item_type = "closer"

            # Attach media to Tweet 1 if available
            item_media = top_media_url if (idx == 0 and top_media_url) else None

            items.append(
                ThreadItemCreate(
                    position=idx,
                    item_type=item_type,
                    text=remediated_text,
                    media_url=item_media,
                )
            )
            tweet_texts.append(remediated_text)

        rep_dict = research_report.model_dump() if research_report else None
        dl_media = [m.model_dump() for m in research_report.downloaded_media] if research_report else []

        return GeneratedThreadResponse(
            topic=data.get("topic", topic),
            hook_score=int(data.get("hook_score", 90)),
            archetype=data.get("archetype", archetype),
            tweets=tweet_texts,
            items=items,
            research_report=rep_dict,
            downloaded_media=dl_media,
        )

    except Exception as e:
        logger.error("Error generating AI thread: %s. Discarding without template fallback.", e)
        return None
