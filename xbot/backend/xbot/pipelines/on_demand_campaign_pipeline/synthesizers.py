"""
On-Demand Campaign Deliverable Synthesizers for Thread, Poll, Visual, and Post types.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.campaign_planner import DeliverableSpec
from xbot.ai.formatting_engine import format_content
from xbot.models.content import Content, ContentStatus, ContentType, ThreadItem
from xbot.models.profile import Profile

logger = logging.getLogger(__name__)


async def synthesize_thread_deliverable(
    db: AsyncSession,
    profile: Profile,
    spec: DeliverableSpec,
    persona: Any,
    context_summary: str,
    downloaded_media: list[str],
    campaign_id: str,
    profile_slug: str,
    pkg: Any,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes a campaign thread deliverable."""
    thread_res = await pkg.generate_thread(
        topic=f"{spec.topic} ({context_summary})",
        persona=persona,
        num_tweets=4,
        deep_research=False,
    )
    raw_tweets = thread_res.tweets if hasattr(thread_res, "tweets") else thread_res.get("tweets", [spec.topic])
    clean_tweets = [strip_surrounding_quotes(t) for t in raw_tweets]

    formatted_tweets = []
    for t in clean_tweets:
        f_t = format_content(t, profile_slug=profile_slug, content_type="thread")
        formatted_tweets.append(strip_surrounding_quotes(f_t))

    thread_media = downloaded_media if spec.target_media_count > 0 else []
    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.THREAD,
        status=ContentStatus.DRAFT,
        body="\n\n".join(formatted_tweets),
        ai_metadata={
            "campaign_id": campaign_id,
            "deliverable_id": spec.id,
            "topic": spec.topic,
            "thread_items": formatted_tweets,
            "tweets": formatted_tweets,
            "media_paths": thread_media,
            "instructions": spec.instructions,
        },
    )
    db.add(content_record)
    await db.flush()

    for i, tw_text in enumerate(formatted_tweets):
        i_type = "hook" if i == 0 else ("closer" if i == len(formatted_tweets) - 1 else "body")
        db.add(ThreadItem(content_id=content_record.id, position=i, item_type=i_type, text=tw_text))

    preview_payload = {
        "thread_tweets": formatted_tweets,
        "text": formatted_tweets[0] if formatted_tweets else "",
    }
    return content_record, preview_payload


async def synthesize_poll_deliverable(
    db: AsyncSession,
    profile: Profile,
    spec: DeliverableSpec,
    persona: Any,
    campaign_id: str,
    pkg: Any,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes an on-demand campaign interactive poll deliverable."""
    poll = await pkg.generate_poll(
        persona=persona,
        topic=f"{spec.topic} ({spec.instructions})",
    )
    poll_text = strip_surrounding_quotes(poll.question)
    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.POLL,
        status=ContentStatus.DRAFT,
        body=poll_text,
        ai_metadata={
            "campaign_id": campaign_id,
            "deliverable_id": spec.id,
            "topic": spec.topic,
            "poll": {
                "question": poll.question,
                "options": poll.options,
                "duration_days": poll.duration_days,
                "context_hook": poll.context_hook,
                "reasoning": poll.reasoning,
            },
            "poll_options": poll.options,
            "duration_days": poll.duration_days,
            "instructions": spec.instructions,
        },
    )
    db.add(content_record)
    preview_payload = {
        "question": poll.question,
        "options": poll.options,
        "duration_days": poll.duration_days,
        "text": poll.question,
    }
    return content_record, preview_payload


async def synthesize_visual_deliverable(
    db: AsyncSession,
    profile: Profile,
    spec: DeliverableSpec,
    persona: Any,
    downloaded_media: list[str],
    campaign_id: str,
    profile_slug: str,
    pkg: Any,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes an on-demand campaign visual meme / infographic deliverable."""
    visual_spec = await pkg.generate_visual_post_spec(
        topic=spec.topic,
        persona=persona,
    )
    raw_hook = strip_surrounding_quotes(visual_spec.tweet_copy)
    formatted_hook = strip_surrounding_quotes(format_content(raw_hook, profile_slug=profile_slug, content_type="post", has_media=True))
    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.ORIGINAL,
        status=ContentStatus.DRAFT,
        body=formatted_hook,
        ai_metadata={
            "campaign_id": campaign_id,
            "deliverable_id": spec.id,
            "topic": spec.topic,
            "archetype": "VISUAL",
            "visual_post_spec": visual_spec.model_dump(),
            "format_type": visual_spec.format_type,
            "aspect_ratio": "4:5",
            "target_simcluster": visual_spec.target_simcluster,
            "image_prompt": visual_spec.image_prompt,
            "media_paths": downloaded_media,
            "instructions": spec.instructions,
        },
    )
    db.add(content_record)
    preview_payload = {
        "text": formatted_hook,
        "visual_spec": visual_spec.model_dump(),
    }
    return content_record, preview_payload


async def synthesize_post_deliverable(
    db: AsyncSession,
    profile: Profile,
    spec: DeliverableSpec,
    persona: Any,
    context_summary: str,
    downloaded_media: list[str],
    campaign_id: str,
    profile_slug: str,
    pkg: Any,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes an on-demand campaign standalone post deliverable."""
    synth_res = await pkg.synthesize_creator_post(
        topic=spec.topic,
        persona=persona,
        context_summary=f"{context_summary}\n\nInstructions: {spec.instructions}",
        post_type="post",
    )
    raw_post = synth_res.content if synth_res and synth_res.content else spec.topic
    formatted_post = format_content(raw_post, profile_slug=profile_slug, content_type="post", has_media=bool(downloaded_media))
    opt_res = await pkg.optimize_post_for_virality(formatted_post)
    final_text = strip_surrounding_quotes(opt_res.full_optimized_text or formatted_post)

    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.ORIGINAL,
        status=ContentStatus.DRAFT,
        body=final_text,
        ai_metadata={
            "campaign_id": campaign_id,
            "deliverable_id": spec.id,
            "topic": spec.topic,
            "extracted_link": opt_res.extracted_link,
            "first_reply_text": f"Link / source breakdown: {opt_res.extracted_link}" if opt_res.extracted_link else None,
            "media_paths": downloaded_media if spec.target_media_count > 0 else [],
            "instructions": spec.instructions,
        },
    )
    db.add(content_record)
    preview_payload = {
        "text": final_text,
        "extracted_link": opt_res.extracted_link,
    }
    return content_record, preview_payload
