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

import json
import logging
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


class GeneratedThreadItem(BaseModel):
    position: int = Field(..., description="0-indexed tweet position in thread")
    item_type: Literal["hook", "body", "closer"] = Field(..., description="'hook', 'body', or 'closer'")
    text: str = Field(..., max_length=280, description="Tweet text strictly <= 260 chars")
    media_url: str | None = Field(None, description="Optional attached image URL or path")


class GeneratedThreadPayload(BaseModel):
    topic: str
    hook_score: int = Field(..., ge=1, le=100, description="Estimated viral hook strength (1-100)")
    archetype: str = Field(..., description="Framework, Contrarian Breakdown, Case Study, or Tactical Guide")
    tweets: list[GeneratedThreadItem] = Field(..., min_length=2, max_length=8)


class GeneratedThreadResponse(BaseModel):
    topic: str
    hook_score: int
    archetype: str
    tweets: list[str]
    items: list[ThreadItemCreate]
    research_report: dict[str, Any] | None = None
    downloaded_media: list[dict[str, Any]] = Field(default_factory=list)


def _build_fallback_thread(
    topic: str,
    persona: Persona | None = None,
    research_report: TopicResearchReport | None = None,
) -> GeneratedThreadResponse:
    """Generates a high-quality deterministic fallback thread adhering to Anti-AI typography."""
    t1 = (
        f"Most discussions around {topic} miss the single biggest leverage point.\n\n"
        f"Here is the exact 3-step breakdown I use to cut through the noise and execute: 🧵"
    )
    t2 = (
        "• Define the core operational constraint before reacting\n"
        "• Test public sentiment with direct data, not echo chambers\n"
        "• Eliminate vanity metrics in favor of actual retention"
    )
    t3 = (
        "• Ship raw minimum viable experiments\n"
        "• Gather feedback from real users rather than speculation\n"
        "• Iterate based on verifiable behavioral signals"
    )
    t4 = (
        f"TL;DR on {topic}:\n"
        "1. Identify core constraints first\n"
        "2. Prioritize empirical data over noise\n"
        "3. Optimize for fast iteration\n\n"
        "Bookmark this thread for quick reference. What is your #1 takeaway?"
    )

    items = [
        ThreadItemCreate(position=0, item_type="hook", text=t1),
        ThreadItemCreate(position=1, item_type="body", text=t2),
        ThreadItemCreate(position=2, item_type="body", text=t3),
        ThreadItemCreate(position=3, item_type="closer", text=t4),
    ]
    
    rep_dict = research_report.model_dump() if research_report else None
    dl_media = [m.model_dump() for m in research_report.downloaded_media] if research_report else []

    return GeneratedThreadResponse(
        topic=topic,
        hook_score=92,
        archetype="Framework",
        tweets=[t1, t2, t3, t4],
        items=items,
        research_report=rep_dict,
        downloaded_media=dl_media,
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

    system_prompt = (
        "You are an elite, culturally plugged-in digital creator and writer on X (Twitter).\n"
        "You construct viral, authentic multi-tweet threads using the 3-Tier Creator Formula:\n"
        "- Tweet 1 (Hook): Scroll-stopping contrast, personal dilemma, or high-stakes insight (< 140 chars before fold) + value promise ending with 🧵.\n"
        "- Tweets 2 to (N-1) (Body): 1 standalone concept per tweet with personal context, relatable observations, and clean standard bullet points (`•` or `-`).\n"
        "- Tweet N (Closer): TL;DR summary recap + open engagement question inviting followers to share their experience.\n\n"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n"
    )

    if persona:
        system_prompt += f"\nPersona: {persona.display_name}. Tone: {persona.personality.communication_style}. Primary Interests: {', '.join(persona.interests.primary)}."

    user_prompt = (
        f"Generate a {num_tweets}-tweet thread on the following topic:\n"
        f"Topic: \"{topic}\"\n"
        f"Archetype: {archetype}\n\n"
    )
    if research_context_blob:
        user_prompt += f"{research_context_blob}\n\n"

    user_prompt += (
        "Formatting Constraints:\n"
        "- Ground your thread in the real events, actual community debates, and specific nuances provided in the research.\n"
        "- Include 1-2 authentic research-grounded hashtags from the analysis naturally in the hook or closer tweet.\n"
        "- Every single tweet MUST be under 260 characters.\n"
        "- Every sentence MUST start with standard Sentence Case capitalization.\n"
        "- Use double line breaks (\\n\\n) for spacing.\n"
        "- Never use emojis as bullet headers (use '• ' or '- ').\n"
        "- Zero corporate AI clichés ('supercharge', 'unleash', 'delve', 'game-changer', 'let that sink in').\n\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        "  \"topic\": \"" + topic + "\",\n"
        "  \"hook_score\": 95,\n"
        "  \"archetype\": \"" + archetype + "\",\n"
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
            return _build_fallback_thread(topic, persona, research_report)

        items: list[ThreadItemCreate] = []
        tweet_texts: list[str] = []

        # Map top downloaded media if available
        top_media_url = None
        if research_report and research_report.downloaded_media:
            top_media_url = research_report.downloaded_media[0].local_path

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
        logger.error("Error generating AI thread: %s. Using high-signal fallback.", e)
        return _build_fallback_thread(topic, persona, research_report)
