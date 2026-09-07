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
from xbot.ai.formatting.cleaner import enforce_pacing_whitespace
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
    num_tweets: int | None = None,
    archetype: str = "Framework",
    deep_research: bool = True,
    profile_slug: str = "test_profile1",
    client: Any = None,
) -> GeneratedThreadResponse:
    """
    Generates an authentic, high-retention multi-tweet thread on the given topic.
    Dynamically scales thread length between 2 and 8 tweets based on information depth and quality.
    Validates every tweet part through AntiAIGatekeeper.
    """
    if num_tweets is not None:
        target_num_tweets = max(2, min(8, num_tweets))
        length_instruction = (
            f"Generate exactly a {target_num_tweets}-tweet thread. "
            f"Every single tweet must contain high-density, substantive insight with zero filler or fluff."
        )
    else:
        target_num_tweets = None
        length_instruction = (
            "Determine the ideal thread length dynamically between 2 and 8 tweets based strictly on the depth "
            "and quality of genuine information available.\n"
            "CRITICAL QUALITY RULE: DO NOT pad or stretch the thread with filler, repetition, or empty fluff. "
            "If there are only 2 or 3 solid, high-value insights, generate a punchy 2-3 tweet thread. "
            "Only extend up to 5-8 tweets if the topic genuinely has enough substantive breakdown, evidence, and nuance to justify that depth. "
            "Actual quality content > quantity always. Zero gibberish."
        )
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
        "5. DYNAMIC THREAD FORMULA (2 to 8 tweets):\n"
        "   - Tweet 1 (Hook): Short, punchy opener that makes people want to read more (< 140 chars). NO thread numbering (no '1/X', '🧵'). Just open with strong, relatable context.\n"
        "   - Middle Tweets (Body, if thread >= 3 tweets): One clear observation or point per tweet with double line breaks (\\n\\n). NO thread numbering. NO numbered lists (1. 2. 3.). Write in natural conversational flow.\n"
        "   - Last Tweet (Closer): Concluding punchy takeaway + optional question. 1-2 authentic topic hashtags max. NEVER use 'TL;DR:' or 'TLDR:' or 'In conclusion:'.\n\n"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n"
    )

    if persona:
        system_prompt += f"\nPersona: {persona.display_name}. Tone: {persona.personality.communication_style}. Primary Interests: {', '.join(persona.interests.primary)}."

    user_prompt = (
        f"Generate a high-quality thread on this trending topic:\n"
        f"Topic: \"{topic}\"\n"
        f"Current Date: {now_date_str} (STRICTLY enforce that all facts and context are from the past 7 days)\n\n"
    )
    if research_context_blob:
        user_prompt += f"=== LIVE X RESEARCH & COMMUNITY SENTIMENT (Past 7 Days from 20-30 Top Viral Posts) ===\n{research_context_blob}\n\n"

    user_prompt += (
        "Instructions:\n"
        f"- THREAD SIZING & DENSITY: {length_instruction}\n"
        "- Base your entire thread on the ACTUAL community sentiment and top viral tweets shown above.\n"
        "- If the public is calling out a brand or celebrity for a tone-deaf campaign, match that critical, witty perspective.\n"
        "- Formatting & Thread Structure:\n"
        "  • Tweet 1 (Hook): Attention-grabbing opener under 140 chars. Do NOT put '🧵' or '1/N'. Open a curiosity loop that makes readers tap.\n"
        "  • Middle Tweets (Body): Each tweet covers ONE specific point. Use double line breaks (\\n\\n) for visual breathing room. Do NOT use numbering like '2/N'. NO numbered lists (1. 2. 3.). Write naturally.\n"
        "  • Last Tweet (Closer): Wrap it up with a strong final thought or debate question to drive replies. Max 1-2 authentic topic hashtags.\n"
        "- WHITESPACE & THE 2-SENTENCE RULE: Never write more than 2 sentences together without a double line break (\\n\\n). Ensure high scannability on mobile feeds.\n"
        "- DYNAMIC EMOJIS (0-3 MAX): Use 0 to 3 emojis total across the whole thread, chosen purely to fit the emotion/context. DO NOT dump emojis at the end of every tweet. Zero emojis is completely fine.\n"
        "- Every single tweet MUST be under 260 characters.\n"
        "- Simple, everyday English: NO heavy dictionary words (no 'moreover', 'delve', 'crucial', 'vital', 'robust'). Talk like a normal human on X.\n"
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

        raw_items = raw_items[:8]

        items: list[ThreadItemCreate] = []
        tweet_texts: list[str] = []

        # Map top downloaded media if available or generate guaranteed visual graphic
        top_media_url = None
        dl_media = []
        if research_report and len(research_report.downloaded_media) > 0:
            top_media_url = research_report.downloaded_media[0].local_path
            dl_media = [m.model_dump() for m in research_report.downloaded_media]


        for idx, item in enumerate(raw_items):
            raw_text = item.get("text", "").strip()
            # Remediate minor typography quirks
            remediated_text = gatekeeper.remediate_minor_issues(raw_text)

            # Strip robotic thread numbering e.g. "🧵 1/4", "1/4", "2/4:" etc.
            remediated_text = re.sub(r"^\s*🧵?\s*\d+/\d+\s*[-:•]?\s*", "", remediated_text)
            remediated_text = re.sub(r"\s*🧵?\s*\d+/\d+\s*$", "", remediated_text)

            # Visual pacing & 2-sentence whitespace rule
            remediated_text = enforce_pacing_whitespace(remediated_text)

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

        try:
            hook_score = int(data.get("hook_score") or 90)
        except (ValueError, TypeError):
            hook_score = 90

        return GeneratedThreadResponse(
            topic=data.get("topic", topic),
            hook_score=hook_score,
            archetype=data.get("archetype", archetype),
            tweets=tweet_texts,
            items=items,
            research_report=rep_dict,
            downloaded_media=dl_media,
        )

    except Exception as e:
        logger.error("Error generating AI thread: %s. Discarding without template fallback.", e)
        return None
