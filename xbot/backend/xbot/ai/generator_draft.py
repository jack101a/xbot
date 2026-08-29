from __future__ import annotations
import logging
from typing import Any
from xbot.ai.client import get_ai_client
from xbot.ai.hook_optimizer import HookOptimizationResult, optimize_post_hook
from xbot.config import settings

logger = logging.getLogger(__name__)

async def generate_tweet_draft_and_optimize(
    generator_inst: Any,
    persona: Any,
    topic: str = "",
    draft_tweet: str | None = None,
) -> HookOptimizationResult:
    """
    Generates a high-impact tweet matching the persona's voice and optimizes its opening hook
    for maximal dwell time and feed retention using the 4-archetype viral hook framework.
    """
    client = getattr(generator_inst, "client", None) if getattr(generator_inst, "client", None) is not None else get_ai_client()

    # 1. Generate initial draft if not provided
    if draft_tweet is None or not draft_tweet.strip():
        display_name = getattr(persona, "display_name", "Autonomous Creator")
        x_handle = getattr(persona, "x_handle", "creator")
        background = getattr(getattr(persona, "identity", None), "background", "")
        tone = getattr(getattr(persona, "writing_style", None), "tone", "sharp, authentic")
        examples = getattr(getattr(persona, "writing_style", None), "examples", [])
        formatting = getattr(getattr(persona, "writing_style", None), "formatting", [])
        always_rules = getattr(getattr(persona, "rules", None), "always", [])
        never_rules = getattr(getattr(persona, "rules", None), "never", [])

        sys_parts = [
            f"You are {display_name} (@{x_handle}). You are composing a post for your X account.",
            "Write in your authentic character voice.",
        ]
        if background:
            sys_parts.append(f"Background: {background}")
        if tone:
            sys_parts.append(f"Tone: {tone}")
        if formatting:
            fmt_str = chr(10).join(f"- {fmt}" for fmt in formatting)
            sys_parts.append(f"Formatting:{chr(10)}{fmt_str}")
        if examples:
            ex_str = chr(10).join(f"- {ex}" for ex in examples[:2])
            sys_parts.append(f"Examples:{chr(10)}{ex_str}")
        if always_rules:
            alw_str = chr(10).join(f"- {r}" for r in always_rules)
            sys_parts.append(f"Always Rules:{chr(10)}{alw_str}")
        if never_rules:
            nev_str = chr(10).join(f"- {r}" for r in never_rules)
            sys_parts.append(f"Never Rules:{chr(10)}{nev_str}")

        sys_prompt = chr(10).join(sys_parts)
        usr_prompt = (
            f"Write an insightful, scroll-stopping tweet about: {topic}"
            if topic
            else "Write an insightful, scroll-stopping tweet in your core niche."
        )

        model = getattr(settings, "MODEL_POST_CREATION", "litellm/gpt-oss-120b")
        try:
            comp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": usr_prompt},
                ],
            )
            draft_tweet = getattr(comp.choices[0].message, "content", "").strip()
        except Exception as e:
            logger.error("Draft tweet generation failed: %s. Discarding without template fallback.", e)
            draft_tweet = ""

    if not draft_tweet:
        return None

    # 2. Run viral hook optimization & dwell formatting
    return await optimize_post_hook(
        persona=persona,
        draft_content=draft_tweet,
        topic=topic,
        client=client,
    )
