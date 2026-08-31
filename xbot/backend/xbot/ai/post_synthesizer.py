from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

from xbot.ai.anti_ai_gatekeeper import (
    ANTI_AI_TYPOGRAPHY_DIRECTIVE,
    AntiAIGatekeeper,
    strip_surrounding_quotes,
)

from xbot.ai.client import get_ai_client
from xbot.ai.fact_grounder import search_web_grounding
from xbot.ai.hook_optimizer import extract_links, trim_open_loop_hook
from xbot.ai.vision import analyze_image_context
from xbot.ai.formatting_engine import (
    ARCHETYPE_REGISTRY,
    PostFormattingArchetype,
    post_process_formatted_content,
    select_archetype,
)
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)


from xbot.ai.post_synthesis_builder import (
    SynthesizedPostResult,
    _build_clean_creator_prompt,
)


async def synthesize_creator_post(
    topic: str,
    persona: Persona,
    image_url: str | None = None,
    recent_posts: list[str] | None = None,
    post_type: Literal["post", "thread", "poll"] = "post",
    recent_archetypes: list[str] | None = None,
    context_summary: str | None = None,
    client: Any | None = None,
) -> SynthesizedPostResult:
    """
    Unified 5-Stage Creator Post Synthesis Pipeline:
    1. Vision Analysis via Gemini Flash Lite if image present.
    2. Real-Time Fact Grounding via SearXNG.
    3. Dynamic Structural Archetype Selection (Anti-Monotony).
    4. Clean Prompt Assembly with archetype layout directives and few-shot pacing.
    5. Heavy Writing Generation + Post-processing (whitespace pacing, trailing emoji stripping, link extraction).
    """
    if client is None:
        client = get_ai_client()

    gatekeeper = AntiAIGatekeeper()

    # Step 1: Multimodal Vision Analysis (if image provided)
    vision_summary = None
    if image_url:
        vision_summary = await analyze_image_context(
            image_url=image_url,
            prompt_hint=topic,
            client=client,
        )

    # Step 2: Real-Time Web Grounding via SearXNG
    search_facts = []
    try:
        search_facts = await search_web_grounding(query=topic, max_results=3)
    except Exception as s_err:
        logger.debug("Web search grounding skipped: %s", s_err)

    # Step 3: Dynamic Archetype Selection
    selected_archetype = select_archetype(
        topic=topic,
        has_media=bool(image_url),
        persona=persona,
        recent_archetypes=recent_archetypes,
        content_type=post_type,
    )

    # Step 4: Clean, Uncluttered User Prompt with Archetype Directives
    user_prompt = _build_clean_creator_prompt(
        topic=topic,
        persona=persona,
        vision_summary=vision_summary,
        search_facts=search_facts,
        recent_posts=recent_posts,
        post_type=post_type,
        archetype=selected_archetype,
        context_summary=context_summary,
    )

    system_prompt = (
        f"You are {persona.display_name} (@{persona.x_handle.lstrip('@')}).\n"
        f"Tone: {persona.personality.communication_style}.\n"
        f"Values: {', '.join(persona.personality.values)}.\n"
        f"Primary Interests: {', '.join(persona.interests.primary)}.\n\n"
        f"{ANTI_AI_TYPOGRAPHY_DIRECTIVE}\n\n"
        "Return ONLY a JSON object matching this schema:\n"
        "{\n"
        "  \"content\": \"primary tweet text or thread hook text (strictly NO external links)\",\n"
        "  \"thread_items\": [\"tweet 1\", \"tweet 2\", \"tweet 3\"] (only if thread, else null),\n"
        "  \"poll_options\": [\"opt 1\", \"opt 2\"] (only if poll, else null),\n"
        "  \"poll_duration_days\": 1,\n"
        "  \"reasoning\": \"strategic rationale for this post\"\n"
        "}"
    )

    writing_model = getattr(settings, "MODEL_POST_CREATION", "litellm/gemini-flash-latest,litellm/deepseek-v4-flash-0731")

    # Step 5: Heavy Writing Model Generation
    try:
        logger.info(
            "Synthesizing creator post via heavy writing cascade (%s) on topic '%s' [archetype=%s]",
            writing_model,
            topic[:50],
            selected_archetype.value,
        )
        response = await client.chat.completions.create(
            model=writing_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.75,
            max_tokens=600,
            action_type="post_synthesis",
            profile_slug=persona.x_handle.lstrip("@"),
        )
        content_str = response.choices[0].message.content or ""
        clean_json = content_str.strip()
        if "```" in clean_json:
            clean_json = re.sub(r"^```(?:json)?", "", clean_json).rstrip("`").strip()

        data = json.loads(clean_json)
        raw_content = strip_surrounding_quotes(data.get("content", "").strip())

        # Enforce dynamic formatting post-processing (whitespace pacing, trailing emoji stripping, length cadence)
        formatted_content = post_process_formatted_content(raw_content, archetype=selected_archetype)

        # Enforce link extraction: strip external URLs into extracted_link for 1st-reply injection
        clean_content, extracted_link = extract_links(formatted_content)
        clean_content = strip_surrounding_quotes(clean_content)

        # Extract <100 char open-loop curiosity hook
        open_loop_hook = None
        if clean_content:
            first_line = clean_content.strip().split("\n")[0].strip()
            first_line = strip_surrounding_quotes(first_line)
            open_loop_hook = trim_open_loop_hook(first_line, max_len=99)

        thread_items = data.get("thread_items")
        if thread_items and isinstance(thread_items, list):
            cleaned_threads = []
            for t in thread_items:
                if t:
                    rem_t = post_process_formatted_content(str(t).strip())
                    clean_t, t_link = extract_links(rem_t)
                    clean_t = strip_surrounding_quotes(clean_t)
                    cleaned_threads.append(clean_t)
                    if not extracted_link and t_link:
                        extracted_link = t_link
            thread_items = cleaned_threads


        poll_options = data.get("poll_options")
        if poll_options and isinstance(poll_options, list):
            poll_options = [str(opt).strip()[:25] for opt in poll_options if opt]

        fact_summaries = [f.get("snippet", "") for f in search_facts if f.get("snippet")]

        return SynthesizedPostResult(
            post_type=post_type,
            content=clean_content,
            archetype=selected_archetype.value,
            thread_items=thread_items,
            poll_options=poll_options,
            poll_duration_days=int(data.get("poll_duration_days", 1)),
            reasoning=data.get("reasoning", "Grounded creator perspective synthesized with verified facts."),
            vision_context=vision_summary,
            search_facts=fact_summaries,
            extracted_link=extracted_link,
            open_loop_hook=open_loop_hook,
            status="success",
        )

    except Exception as e:
        logger.warning("Heavy writing model cascade failed or timed out for topic '%s': %s. Discarding post.", topic[:50], e)
        return SynthesizedPostResult(
            post_type=post_type,
            content="",
            archetype=selected_archetype.value if 'selected_archetype' in locals() else None,
            reasoning="Writing failed: Heavy writing models were unavailable or timed out. Discarded to prevent posting low-quality slop.",
            status="failed",
            error=str(e),
        )
