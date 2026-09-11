"""
On-Demand Campaign Deliverable Synthesizers for Thread, Poll, Visual, and Post types.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.anti_ai_gatekeeper import strip_surrounding_quotes
from xbot.ai.campaign_planner import DeliverableSpec
from xbot.ai.formatting_engine import format_content
from xbot.ai.smart_media_director import (
    classify_post_visual_intent,
    ensure_main_post_hashtags,
    resolve_post_media_waterfall,
    select_best_authentic_media,
    verify_image_with_vision,
)
from xbot.config import settings
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
    used_media_paths: set[str] | None = None,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes a campaign thread deliverable."""
    if used_media_paths is None:
        used_media_paths = set()

    thread_res = await pkg.generate_thread(
        topic=f"{spec.topic} ({context_summary})",
        persona=persona,
        num_tweets=None,
        deep_research=False,
    )
    raw_tweets = thread_res.tweets if hasattr(thread_res, "tweets") else thread_res.get("tweets", [spec.topic])
    clean_tweets = [strip_surrounding_quotes(t) for t in raw_tweets]

    formatted_tweets = []
    for t in clean_tweets:
        f_t = format_content(t, profile_slug=profile_slug, content_type="thread")
        formatted_tweets.append(strip_surrounding_quotes(f_t))

    thread_media: list[str] = []
    hook_text = formatted_tweets[0] if formatted_tweets else spec.topic

    # Waterfall Media Resolution: X First -> SearXNG Precision -> GIF
    resolved_media, _, hook_text = await resolve_post_media_waterfall(
        topic=spec.topic,
        post_text=hook_text,
        profile_slug=profile_slug,
        candidate_images=downloaded_media,
        allow_gif=False,  # Threads require genuine static images on the hook
        used_media_paths=used_media_paths,
    )
    if resolved_media:
        thread_media = resolved_media
    elif getattr(settings, "CHATGPT_BRIDGE_ENABLED", False):
        visual_plan = await classify_post_visual_intent(post_text=hook_text, campaign_topic=spec.topic)
        c_prompt = visual_plan.get("creative_image_prompt") or f"Cinematic aesthetic opening visual for: {spec.topic}"
        try:
            from xbot.ai.chatgpt_image import generate_and_save_chatgpt_image_async
            img_path = await generate_and_save_chatgpt_image_async(c_prompt, aspect_ratio="4:5", timeout_s=18)
            if img_path and os.path.exists(img_path):
                thread_media = [img_path]
                used_media_paths.add(img_path)
        except Exception as img_err:
            logger.warning("Thread deliverable ChatGPT image generation skipped: %s", img_err)

    if formatted_tweets:
        formatted_tweets[0] = hook_text
        # Enforce 1-2 community hashtags on the thread closer for search indexing
        formatted_tweets[-1] = ensure_main_post_hashtags(formatted_tweets[-1], spec.topic)

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
    used_media_paths: set[str] | None = None,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes an on-demand campaign visual meme / infographic deliverable."""
    if used_media_paths is None:
        used_media_paths = set()

    visual_spec = await pkg.generate_visual_post_spec(
        topic=spec.topic,
        persona=persona,
    )
    if not visual_spec:
        from xbot.ai.visual_models import VisualPostSpec
        visual_spec = VisualPostSpec(
            tweet_copy=f"The reality of {spec.topic[:110]}.",
            image_prompt=f"Cinematic 4:5 visual breakdown of {spec.topic}, dark aesthetic (#0D1117), ultra-clean composition, 8k realism.",
            aspect_ratio="4:5",
            format_type="storyboard_4panel",
            target_simcluster="Cinema/Prestige",
            one_two_punch_strategy="Setup tension in tweet copy; deliver visual punchline in 4:5 image.",
        )

    raw_hook = strip_surrounding_quotes(visual_spec.tweet_copy)
    formatted_hook = strip_surrounding_quotes(format_content(raw_hook, profile_slug=profile_slug, content_type="post", has_media=True))

    visual_media: list[str] = []
    gif_query = None

    # Waterfall Media Resolution: X First -> SearXNG Precision -> AI Art/GIF
    resolved_media, gif_query, formatted_hook = await resolve_post_media_waterfall(
        topic=spec.topic,
        post_text=formatted_hook,
        profile_slug=profile_slug,
        candidate_images=downloaded_media,
        allow_gif=True,
        used_media_paths=used_media_paths,
    )
    if resolved_media:
        visual_media = resolved_media
    elif getattr(settings, "CHATGPT_BRIDGE_ENABLED", False):
        visual_plan = await classify_post_visual_intent(post_text=formatted_hook, campaign_topic=spec.topic)
        prompt = visual_plan.get("creative_image_prompt") or visual_spec.image_prompt or f"Cinematic 4:5 visual breakdown of {spec.topic}"
        try:
            from xbot.ai.chatgpt_image import generate_and_save_chatgpt_image_async
            img_path = await generate_and_save_chatgpt_image_async(
                prompt,
                aspect_ratio="4:5",
                timeout_s=18,
            )
            if img_path and os.path.exists(img_path):
                visual_media = [img_path]
                used_media_paths.add(img_path)
                gif_query = None
        except Exception as img_err:
            logger.warning("Visual deliverable ChatGPT image generation failed/skipped: %s", img_err)

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
            "media_paths": visual_media,
            "gif_query": gif_query,
            "instructions": spec.instructions,
        },
    )
    db.add(content_record)
    preview_payload = {
        "text": formatted_hook,
        "visual_spec": visual_spec.model_dump(),
        "media_paths": visual_media,
        "gif_query": gif_query,
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
    used_media_paths: set[str] | None = None,
) -> tuple[Content, dict[str, Any]]:
    """Synthesizes an on-demand campaign standalone post deliverable."""
    if used_media_paths is None:
        used_media_paths = set()

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

    # Waterfall Media Resolution: X First -> SearXNG Precision -> AI Art/GIF
    post_media: list[str] = []
    gif_query = None

    resolved_media, gif_query, final_text = await resolve_post_media_waterfall(
        topic=spec.topic,
        post_text=final_text,
        profile_slug=profile_slug,
        candidate_images=downloaded_media,
        allow_gif=True,
        used_media_paths=used_media_paths,
    )
    if resolved_media:
        post_media = resolved_media
    elif getattr(settings, "CHATGPT_BRIDGE_ENABLED", False):
        visual_plan = await classify_post_visual_intent(post_text=final_text, campaign_topic=spec.topic)
        if visual_plan.get("visual_intent") == "CREATIVE_AI_ART" or spec.target_media_count > 0:
            prompt = visual_plan.get("creative_image_prompt") or f"Cinematic 4:5 visual breakdown of {spec.topic}"
            try:
                from xbot.ai.chatgpt_image import generate_and_save_chatgpt_image_async
                img_path = await generate_and_save_chatgpt_image_async(prompt, aspect_ratio="4:5", timeout_s=18)
                if img_path and os.path.exists(img_path):
                    post_media = [img_path]
                    used_media_paths.add(img_path)
                    gif_query = None
            except Exception as img_err:
                logger.warning("Post deliverable ChatGPT image generation skipped: %s", img_err)

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
            "media_paths": post_media,
            "gif_query": gif_query,
            "instructions": spec.instructions,
        },
    )
    db.add(content_record)
    preview_payload = {
        "text": final_text,
        "extracted_link": opt_res.extracted_link,
        "media_paths": post_media,
        "gif_query": gif_query,
    }
    return content_record, preview_payload
