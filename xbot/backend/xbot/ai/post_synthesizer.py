from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Literal
from pydantic import BaseModel, Field

from xbot.ai.anti_ai_gatekeeper import ANTI_AI_TYPOGRAPHY_DIRECTIVE, AntiAIGatekeeper
from xbot.ai.client import get_ai_client
from xbot.ai.fact_grounder import search_web_grounding
from xbot.ai.hook_optimizer import extract_links, trim_open_loop_hook
from xbot.ai.vision import analyze_image_context
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)


class SynthesizedPostResult(BaseModel):
    post_type: Literal["post", "thread", "poll"] = "post"
    content: str
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

    # 4. Few-Shot Creator Examples
    examples = persona.writing_style.examples if persona.writing_style.examples else []
    if examples:
        ex_formatted = "\n\n".join(f"Example {idx+1}:\n\"{ex}\"" for idx, ex in enumerate(examples[:5]))
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
            "- Tweet 1 (Hook): Scroll-stopping curiosity cliffhanger strictly < 100 characters before the mobile fold with 1 emoji ending in 🧵\n"
            "- Tweets 2-3 (Body): 1 punchy takeaway per tweet formatted as high-utility bookmark-bait (numbered action steps or minimal bullets `•` / `-`)\n"
            "- Tweet 4 (Closer): Concluding natural takeaway or debate question (NEVER write 'TL;DR:' or 'TLDR:') + 1 authentic research hashtag\n"
            "- Spacing: Use clean double line breaks (\\n\\n) between thoughts for mobile readability\n"
            "- Zero external URLs in tweets (links belong in 1st reply)"
        )
    elif post_type == "poll":
        sections.append(
            "## 📊 Interactive Poll Instructions:\n"
            "- Question: Punchy dilemma or debate hook (< 160 chars)\n"
            "- Options: Exactly 2 to 4 choices, each strictly under 25 characters"
        )
    else:
        sections.append(
            "## ✍️ Standalone Post Instructions:\n"
            "- Creative Freedom & Variety: Match human creator cadence. Choose naturally among:\n"
            "  • Ultra-short punchy take (1-10 words: 'real', 'pure cinema', 'W', 'who approved this')\n"
            "  • Dry observation or relatable irony with natural wit\n"
            "  • Open-loop curiosity hook (< 100 characters before the mobile fold)\n"
            "  • High-utility numbered framework, cheat sheet, or bookmark-bait (+50x reach)\n"
            "- Emojis & Formatting: Include 1-2 authentic emojis (e.g. 🍿, ☕, 💀, 💅, 🧵, 👀, 🤌) and 1-2 research-grounded hashtags (e.g. #Bollywood, #AppleEvent). Use clean double line breaks (\\n\\n) for spacing.\n"
            "- Single Topic Focus: Centered on ONE clear premise. Grounded in actual research from X and search engines.\n"
            "- Native Text Only: DO NOT include external URLs in the post body (100% native text)."
        )

    return "\n\n".join(sections)


async def synthesize_creator_post(
    topic: str,
    persona: Persona,
    image_url: str | None = None,
    recent_posts: list[str] | None = None,
    post_type: Literal["post", "thread", "poll"] = "post",
    client: Any | None = None,
) -> SynthesizedPostResult:
    """
    Unified 5-Stage Creator Post Synthesis Pipeline:
    1. Vision Analysis via Gemini Flash Lite (2 retries) if image present.
    2. Real-Time Fact Grounding via SearXNG (search.ajaxhs.duckdns.org).
    3. Few-Shot Creator Examples Injection.
    4. Clean, Zero-Bloat Prompt Assembly (with open-loop hook & bookmark directives).
    5. Heavy Writing Model Generation (Gemini Flash Latest -> DeepSeek Flash) with safe discard,
       link stripping to isolated extracted_link for 1st-reply injection, and <100 char open-loop hook extraction.
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

    # Step 3 & 4: Clean, Uncluttered User Prompt
    user_prompt = _build_clean_creator_prompt(
        topic=topic,
        persona=persona,
        vision_summary=vision_summary,
        search_facts=search_facts,
        recent_posts=recent_posts,
        post_type=post_type,
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
        logger.info("Synthesizing creator post via heavy writing cascade (%s) on topic: '%s'", writing_model, topic[:50])
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
        raw_content = data.get("content", "").strip()

        # Gatekeeper check & minor typography remediation
        remediated_content = gatekeeper.remediate_minor_issues(raw_content)

        # Enforce link extraction: strip external URLs into extracted_link for 1st-reply injection
        clean_content, extracted_link = extract_links(remediated_content)

        # Extract <100 char open-loop curiosity hook
        open_loop_hook = None
        if clean_content:
            first_line = clean_content.strip().split("\n")[0].strip()
            open_loop_hook = trim_open_loop_hook(first_line, max_len=99)

        thread_items = data.get("thread_items")
        if thread_items and isinstance(thread_items, list):
            cleaned_threads = []
            for t in thread_items:
                if t:
                    rem_t = gatekeeper.remediate_minor_issues(str(t).strip())
                    clean_t, t_link = extract_links(rem_t)
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
            reasoning="Writing failed: Heavy writing models were unavailable or timed out. Discarded to prevent posting low-quality slop.",
            status="failed",
            error=str(e),
        )
