from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field
from xbot.persona.loader import Persona
from xbot.ai.formatting_engine import PostFormattingArchetype, ARCHETYPE_REGISTRY

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
        sections.append(
            f"## 📸 Visual Image Analysis (From Multimodal Vision)\n{vision_summary}\n\n"
            f"ATTACHED MEDIA DIRECTIVE: This image will be attached to the tweet. Your copy MUST directly reference or reflect what is depicted in the image so the visual and text form a cohesive, unified post."
        )

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
            "- Explicit Naming: Explicitly name the subject/movie/company (e.g. 'Toxic', 'Yash') in Tweet 1\n"
            "- Tweets 2-3 (Body): Atomic value nuggets with generous whitespace (\\n\\n) and bullet frameworks\n"
            "- Tweet 4 (Closer): High-conviction punchy takeaway + 1-2 relevant hashtags"
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
            "- Explicit Subject Naming: Always explicitly state the specific person, project, movie, or brand (e.g. 'Toxic', 'Yash', 'GTA 6') so readers immediately know what is being discussed\n"
            "- Relevant Hashtags: If topic hashtags were discovered (e.g. #Toxic #Yash), include 1-2 clean hashtags naturally at the end\n"
            "- High-Utility & Variety: Match authentic human cadence (micro-takes, staccato observations, bookmark-bait frameworks)\n"
            "- Structure: Clear line breaks (\\n\\n) between setup, observation, and punchline\n"
            "- Character count: Strictly <= 260 characters\n"
            "- Native Text Only: DO NOT include external URLs in the post body (100% native text)."
        )

    return "\n\n".join(sections)
