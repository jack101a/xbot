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


class SynthesizedPostResult(BaseModel):
    post_type: Literal["post", "thread", "poll"] = "post"
    content: str
    archetype: str | None = None
    thread_items: list[str] | None = None
    poll_options: list[str] | None = None
    poll_duration_days: int = 1
    reasoning: str
    vision_context: str | None = None
    search_facts: list[str] = Field(default_factory=list)
    extracted_link: str | None = None
    open_loop_hook: str | None = None
    confidence: float = 1.0
    status: Literal["success", "failed"] = "success"
    error: str | None = None


def _build_clean_creator_prompt(
    topic: str,
    persona: Persona,
    vision_summary: str | None = None,
    search_facts: list[dict[str, str]] | None = None,
    recent_posts: list[str] | None = None,
    post_type: str = "post",
    archetype: PostFormattingArchetype | None = None,
    context_summary: str | None = None,
) -> str:
    """
    Constructs a clean, high-signal, zero-bloat prompt for the heavy writing model.
    Strips out internal DB metrics, budget counters, and raw diary dumps.
    """
    now_date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    sections = []

    # 1. Primary Premise & Recency Constraint
    sections.append(
        f"## Topic / Event Premise\n\"{topic}\"\n"
        f"Current Date: {now_date_str}\n"
        f"STRICT 7-DAY RECENCY: Focus strictly on recent developments, live reactions, and discussions within the past 7 days. Reject historical anecdotes or ancient claims older than 1 week."
    )

    # 2. Image Vision Context (if present)
    if vision_summary:
        sections.append(f"## 📸 Visual Image Analysis (From Multimodal Vision)\n{vision_summary}")

    # 2b. Live Researched Context / Discussion Dossier (if present)
    if context_summary:
        sections.append(f"## 💬 Live Community Context & Social Reactions\n{context_summary}")

    # 3. Live Web Search Facts from SearXNG
    if search_facts:
        fact_lines = []
        for f in search_facts[:3]:
            title = f.get("title", "").strip()
            snippet = f.get("snippet", "").strip()
            if title and snippet:
                fact_lines.append(f"- {title}: {snippet}")
            elif snippet:
                fact_lines.append(f"- {snippet}")
        if fact_lines:
            sections.append(f"## 🌐 Live Web Search Facts (Verified via SearXNG)\n" + "\n".join(fact_lines))

    # 4. Archetype-Specific Layout Directives & Few-Shot Formatting
    if post_type == "post" and archetype and archetype in ARCHETYPE_REGISTRY:
        spec = ARCHETYPE_REGISTRY[archetype]
        sections.append(f"## 🎯 Structural Archetype Directive: {spec.display_name}\n{spec.directives}")
        if spec.few_shot_examples:
            ex_text = "\n\n".join(f"Example {i+1}:\n\"{ex}\"" for i, ex in enumerate(spec.few_shot_examples))
            sections.append(f"## ✍️ Layout & Micro-Pacing Few-Shot Examples\n{ex_text}")
    elif persona.writing_style.examples:
        ex_formatted = "\n\n".join(f"Example {idx+1}:\n\"{ex}\"" for idx, ex in enumerate(persona.writing_style.examples[:5]))
        sections.append(f"## ✍️ High-Engagement Creator Style Examples\n{ex_formatted}")

    # 5. Anti-Duplication Guard
    if recent_posts:
        clean_recents = [f"- {p[:80]}..." for p in recent_posts[:6] if p]
        if clean_recents:
            sections.append(f"## 🚫 Do NOT Repeat These Recent Posts\n" + "\n".join(clean_recents))

    # 6. Output Type Directives
    if post_type == "thread":
        sections.append(
            "## 🧵 Multi-Tweet Thread Instructions (3-4 Tweets):\n"
            "- Tweet 1 (Hook): Scroll-stopping curiosity cliffhanger strictly < 100 characters before the mobile fold\n"
            "- Tweets 2-3 (Body): Atomic value nuggets with generous whitespace (\\n\\n) and bullet frameworks\n"
            "- Tweet 4 (Closer): High-conviction punchy takeaway + bookmark CTA"
        )
    elif post_type == "poll":
        sections.append(
            "## 📊 Interactive Poll Directives:\n"
            "- Question: Clear, polarizing dilemma or scenario with no obvious middle ground\n"
            "- Options: 2-4 punchy, distinct choices strictly under 25 characters each\n"
            "- Include context_hook explaining why this dilemma matters right now"
        )
    else:
        sections.append(
            "## 📝 Standalone Post Directives:\n"
            "- Mobile Fold Hook: Keep opening curiosity hook strictly < 100 characters before the mobile fold\n"
            "- High-Utility & Variety: Match authentic human cadence (micro-takes, staccato observations, bookmark-bait frameworks)\n"
            "- Structure: Clear line breaks (\\n\\n) between setup, observation, and punchline\n"
            "- Zero Emojis at the very end unless organically tied to humor\n"
            "- Character count: Strictly <= 260 characters\n"
            "- Native Text Only: DO NOT include external URLs in the post body (100% native text)."
        )

    return "\n\n".join(sections)


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
