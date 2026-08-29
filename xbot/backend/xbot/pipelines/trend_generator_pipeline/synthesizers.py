"""
Trend Generator Topic Synthesizers for Visual, Thread, Poll, and Post content.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from xbot.models.content import Content, ContentStatus, ContentType, ThreadItem
from xbot.models.pipeline import ResearchedTopic
from xbot.models.profile import Profile
from xbot.pipelines.trend_generator_pipeline.collector import _detect_reaction_gif_query

logger = logging.getLogger(__name__)


async def synthesize_visual_topic(
    db: AsyncSession,
    profile: Profile,
    topic: ResearchedTopic,
    persona: Any,
    media_to_attach: list[str],
    gatekeeper: Any,
    profile_slug: str,
    pkg: Any,
) -> Content:
    """Synthesizes a 4:5 vertical visual post / infographic specification."""
    visual_spec = await pkg.generate_visual_post_spec(
        topic=topic.topic,
        persona=persona,
    )
    raw_hook = pkg.strip_surrounding_quotes(visual_spec.tweet_copy)
    val_res = gatekeeper.validate(raw_hook)
    if not val_res.is_valid:
        raw_hook = gatekeeper.remediate_minor_issues(raw_hook)

    formatted_hook = pkg.format_content(
        raw_text=raw_hook,
        profile_slug=profile_slug,
        content_type="post",
        has_media=True,
        topic=topic.topic,
    )
    final_hook = pkg.strip_surrounding_quotes(formatted_hook)

    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.ORIGINAL,
        status=ContentStatus.APPROVED,
        body=final_hook,
        ai_metadata={
            "topic": topic.topic,
            "archetype": "VISUAL",
            "visual_post_spec": visual_spec.model_dump(),
            "format_type": visual_spec.format_type,
            "aspect_ratio": "4:5",
            "target_simcluster": visual_spec.target_simcluster,
            "one_two_punch_strategy": visual_spec.one_two_punch_strategy,
            "image_prompt": visual_spec.image_prompt,
            "researched_topic_id": str(topic.id),
            "media_paths": media_to_attach,
        },
    )
    db.add(content_record)
    return content_record


async def synthesize_thread_topic(
    db: AsyncSession,
    profile: Profile,
    topic: ResearchedTopic,
    persona: Any,
    media_to_attach: list[str],
    profile_slug: str,
    pkg: Any,
) -> Content:
    """Synthesizes a multi-tweet deep-dive thread."""
    thread_res = await pkg.generate_thread(
        topic=topic.topic,
        persona=persona,
        num_tweets=4,
        deep_research=False,
        profile_slug=profile_slug,
    )
    first_tweet = thread_res.tweets[0] if thread_res.tweets else topic.topic
    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.THREAD,
        status=ContentStatus.APPROVED,
        body=first_tweet,
        ai_metadata={
            "topic": topic.topic,
            "archetype": "THREAD",
            "researched_topic_id": str(topic.id),
            "media_paths": media_to_attach,
            "tweets": thread_res.tweets,
        },
    )
    db.add(content_record)
    await db.flush()

    for idx, tweet_text in enumerate(thread_res.tweets):
        cleaned_tweet = pkg.format_content(tweet_text, profile_slug=profile_slug, content_type="thread")
        t_item = ThreadItem(
            content_id=content_record.id,
            position=idx,
            item_type="hook" if idx == 0 else ("closer" if idx == len(thread_res.tweets) - 1 else "body"),
            text=cleaned_tweet,
            media_url=media_to_attach[0] if (idx == 0 and media_to_attach) else None,
        )
        db.add(t_item)
    return content_record


async def synthesize_poll_topic(
    db: AsyncSession,
    profile: Profile,
    topic: ResearchedTopic,
    persona: Any,
    pkg: Any,
) -> Content:
    """Synthesizes an interactive community poll."""
    poll = await pkg.generate_poll(
        persona=persona,
        topic=topic.topic,
    )
    poll_body = f"{poll.question}\n" + "\n".join(f"🔘 {opt}" for opt in poll.options)
    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.POLL,
        status=ContentStatus.APPROVED,
        body=poll_body,
        ai_metadata={
            "topic": topic.topic,
            "archetype": "POLL",
            "poll": poll.model_dump() if hasattr(poll, "model_dump") else {
                "question": poll.question,
                "options": poll.options,
                "duration_days": poll.duration_days,
                "context_hook": poll.context_hook,
                "reasoning": poll.reasoning,
            },
            "poll_options": poll.options,
            "duration_days": poll.duration_days,
            "context_hook": poll.context_hook,
            "reasoning": poll.reasoning,
            "researched_topic_id": str(topic.id),
        },
    )
    db.add(content_record)
    return content_record


async def synthesize_post_topic(
    db: AsyncSession,
    profile: Profile,
    topic: ResearchedTopic,
    persona: Any,
    media_to_attach: list[str],
    has_media: bool,
    gatekeeper: Any,
    profile_slug: str,
    pkg: Any,
) -> Content:
    """Synthesizes a punchy standalone hot take."""
    synth_res = await pkg.synthesize_creator_post(
        topic=topic.topic,
        persona=persona,
        image_url=media_to_attach[0] if media_to_attach else None,
        post_type="post",
    )
    raw_post = synth_res.content if synth_res and synth_res.content else topic.topic

    val_res = gatekeeper.validate(raw_post)
    if not val_res.is_valid:
        raw_post = gatekeeper.remediate_minor_issues(raw_post)

    formatted_post = pkg.format_content(
        raw_text=raw_post,
        profile_slug=profile_slug,
        content_type="post",
        has_media=has_media,
        topic=topic.topic,
    )

    opt_res = await pkg.optimize_post_for_virality(formatted_post)
    final_post_text = pkg.strip_surrounding_quotes(opt_res.full_optimized_text or formatted_post)
    extracted_link = opt_res.extracted_link
    first_reply_text = f"Link / source breakdown: {extracted_link}" if extracted_link else None
    gif_query = _detect_reaction_gif_query(final_post_text, topic.topic)

    attached_media = [media_to_attach[0]] if (media_to_attach and has_media) else None

    content_record = Content(
        profile_id=profile.id,
        content_type=ContentType.ORIGINAL,
        status=ContentStatus.APPROVED,
        body=final_post_text,
        ai_metadata={
            "topic": topic.topic,
            "archetype": "ORIGINAL",
            "extracted_link": extracted_link,
            "first_reply_text": first_reply_text,
            "gif_query": gif_query,
            "researched_topic_id": str(topic.id),
            "media_paths": attached_media,
        },
    )
    db.add(content_record)
    return content_record
