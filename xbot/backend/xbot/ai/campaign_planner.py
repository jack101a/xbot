"""
Campaign Planner (AI Creative Director & Intent Decomposer).

Decomposes freeform natural-language creator prompts (e.g.,
"build a thread on giva jewellery kriti senon controversy with multiple media,
a thread and some polls on apple upcoming launch event, multiple posts on toxic film")
into discrete, typed deliverables with specific search queries, media targets,
and creative directions.
"""

from __future__ import annotations

import enum
import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.persona.loader import Persona

logger = logging.getLogger(__name__)


class DeliverableType(str, enum.Enum):
    THREAD = "thread"
    POLL = "poll"
    VISUAL = "visual"
    POST = "post"


class DeliverableSpec(BaseModel):
    """Specification for an individual campaign deliverable."""
    id: str = Field(..., description="Unique deliverable identifier, e.g. 'deliv_1'")
    type: DeliverableType = Field(..., description="Format: thread, poll, visual, or post")
    topic: str = Field(..., description="Clear topic description")
    search_query: str = Field(..., description="Focused X/Twitter search query for research and media scraping")
    target_media_count: int = Field(0, description="Target number of images/screenshots to scrape and attach (0-4)")
    instructions: str = Field("", description="Specific creator nuances or instructions for synthesis")


class CampaignPlan(BaseModel):
    """Complete campaign plan decomposed from user prompt."""
    campaign_title: str = Field(..., description="Engaging campaign title")
    theme: str = Field(..., description="Core theme connecting deliverables")
    overall_strategy: str = Field(..., description="High-level posting and audience engagement strategy")
    deliverables: list[DeliverableSpec] = Field(default_factory=list, description="List of deliverables to research and generate")


CAMPAIGN_PLANNER_SYSTEM_PROMPT = """You are the AI Creative Director for XBot Pro.
Your job is to analyze natural-language instructions from a creator and decompose them into a structured, multi-asset Campaign Plan for X (Twitter).

CRITICAL RULES:
1. Parse every explicit request in the prompt:
   - If user asks for "a thread on X with media" -> create a 'thread' deliverable with target_media_count between 2 and 4.
   - If user asks for "some polls on Y" -> create 2 distinct 'poll' deliverables (e.g. A vs B dilemmas, purchasing decisions).
   - If user asks for "multiple posts on Z" -> create 2 distinct 'post' deliverables (hot takes, punchy observations).
   - If user asks for "memes / visuals on W" -> create a 'visual' deliverable with target_media_count=1.
2. Formulate high-signal search queries:
   - Each search_query MUST be 3-6 targeted keywords likely to surface top viral tweets on X.
3. Return ONLY valid JSON adhering strictly to the required schema:
{
  "campaign_title": "...",
  "theme": "...",
  "overall_strategy": "...",
  "deliverables": [
    {
      "id": "deliv_1",
      "type": "thread" | "poll" | "visual" | "post",
      "topic": "...",
      "search_query": "...",
      "target_media_count": 0-4,
      "instructions": "..."
    }
  ]
}
"""


async def plan_campaign_from_prompt(
    prompt: str,
    persona: Persona | None = None,
    client: Any | None = None,
) -> CampaignPlan:
    """
    Decomposes a user prompt into a structured CampaignPlan.
    Falls back gracefully if LLM output fails parsing.
    """
    if client is None:
        client = get_ai_client()

    persona_context = ""
    if persona:
        persona_context = f"\nCreator Persona:\n- Name: {persona.display_name} (@{persona.x_handle})\n- Style: {persona.personality.communication_style if hasattr(persona, 'personality') and persona.personality else 'authentic'}\n"

    user_msg = f"Creator Instruction:\n\"{prompt}\"\n{persona_context}\nDecompose this instruction into a high-impact Campaign Plan."

    try:
        model = getattr(settings, "MODEL_PLANNER", "litellm/deepseek-v4-flash-0731,litellm/gemini-flash-latest")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CAMPAIGN_PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
        )

        content = response.choices[0].message.content or ""
        # Strip markdown json codeblocks if present
        cleaned_json = re.sub(r"^```json\s*", "", content.strip(), flags=re.MULTILINE)
        cleaned_json = re.sub(r"```$", "", cleaned_json.strip(), flags=re.MULTILINE)

        parsed = json.loads(cleaned_json)
        return CampaignPlan.model_validate(parsed)

    except Exception as e:
        logger.warning("CampaignPlanner: Failed to parse LLM campaign plan: %s. Falling back.", e)
        # Fallback single deliverable
        deliv_type = DeliverableType.POST
        p_lower = prompt.lower()
        if "thread" in p_lower:
            deliv_type = DeliverableType.THREAD
        elif "poll" in p_lower:
            deliv_type = DeliverableType.POLL
        elif "meme" in p_lower or "visual" in p_lower:
            deliv_type = DeliverableType.VISUAL

        media_count = 2 if ("media" in p_lower or "image" in p_lower or "screenshot" in p_lower) else 0

        clean_topic = prompt[:80].strip()
        search_q = " ".join([w for w in clean_topic.split() if len(w) > 3][:5])

        return CampaignPlan(
            campaign_title=f"Campaign: {clean_topic[:40]}",
            theme=clean_topic,
            overall_strategy="Focus on viral engagement and authentic community resonance.",
            deliverables=[
                DeliverableSpec(
                    id="deliv_1",
                    type=deliv_type,
                    topic=clean_topic,
                    search_query=search_q or clean_topic,
                    target_media_count=media_count,
                    instructions=prompt,
                )
            ],
        )
