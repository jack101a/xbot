from __future__ import annotations

import datetime
import difflib
import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.ai.hook_optimizer import HookOptimizationResult, optimize_post_hook
from xbot.ai.poll_generator import GeneratedPoll, generate_poll
from xbot.config import settings
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile
from xbot.persona import load_config, load_persona, load_learned_state

logger = logging.getLogger(__name__)


from xbot.ai.content_models import (
    GeneratedContent,
    ContentGenerationResponse,
    calculate_similarity,
    clean_text_for_json,
)

class ContentGenerator:
    """
    Handles character-aligned content generation and validation against
    persona rules, length limits, and similarity heuristics.
    Supports up to 2 regeneration retries with feedback loops.
    Integrates 4-archetype viral hook optimization and native X polls.
    """

    def __init__(
        self,
        base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles",
        client: Any | None = None,
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)
        self.client = client

    async def generate_content(
        self,
        db: AsyncSession,
        profile_slug: str,
        context_prompt: str,
        max_chars: int = 280,
        similarity_threshold: float = 0.8,
    ) -> GeneratedContent:
        """
        Generates content, validates it, and handles automatic regeneration
        on failure (up to 2 retries).
        """
        # 1. Load Profile and Persona
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)
        learned_state = load_learned_state(profile_dir)

        # Job Overrides
        profile_config = profile.config or {}
        job_overrides = profile_config.get("job_routing_overrides", {})
        
        job_model = job_overrides.get("MODEL_POST_CREATION") or settings.MODEL_POST_CREATION
        job_prompt = job_overrides.get("PROMPT_POST_CREATION") or settings.PROMPT_POST_CREATION
        job_context = job_overrides.get("CONTEXT_POST_CREATION") or settings.CONTEXT_POST_CREATION
        context_flags = set(job_context.split(","))

        # 2. Retrieve last 20 posts
        stmt_posts = (
            select(Content)
            .where(
                Content.profile_id == profile.id,
                Content.status == ContentStatus.POSTED,
            )
            .order_by(Content.posted_at.desc())
            .limit(20)
        )
        res_posts = await db.execute(stmt_posts)
        recent_posts = [c.body for c in res_posts.scalars().all()]

        # 3. Construct System Prompt
        prompt_parts = [
            job_prompt,
            f"You are {persona.display_name} (@{persona.x_handle}). You are operating your X account.",
            "Write in your unique voice. Do NOT break character.\n",
            "=== CHARACTER BRIEF ==="
        ]
        
        if "characteristic" in context_flags:
            prompt_parts.append(f"Occupation/Background: {persona.identity.background}")
            prompt_parts.append("Always Do (Positive Characteristics):\n" + "\n".join(f"- {rule}" for rule in persona.rules.always))
            prompt_parts.append("Never Do (Negative Characteristics):\n" + "\n".join(f"- {rule}" for rule in persona.rules.never))
            if learned_state.characteristics.behavioral_adaptations:
                prompt_parts.append("Learned Behavioral Adaptations:\n" + "\n".join(f"- {b}" for b in learned_state.characteristics.behavioral_adaptations))
            
        if "personality" in context_flags:
            prompt_parts.append(f"Personality Traits: {', '.join(persona.personality.traits)}")
            prompt_parts.append(f"Personality Values: {', '.join(persona.personality.values)}")
            prompt_parts.append(f"Communication Style (Voice context): {persona.personality.communication_style}")
            prompt_parts.append(f"Tone: {persona.writing_style.tone}")
            if learned_state.personality.evolving_nuances:
                prompt_parts.append("Evolving Personality Nuances:\n" + "\n".join(f"- {n}" for n in learned_state.personality.evolving_nuances))
            
        if "habits" in context_flags:
            prompt_parts.append("Writing Style Heuristics:\n" + "\n".join(f"- {fmt}" for fmt in persona.writing_style.formatting))
            prompt_parts.append("Examples of how you write:\n" + "\n".join(f"- \"{ex}\"" for ex in persona.writing_style.examples))
            if learned_state.habits.learned_writing_patterns:
                prompt_parts.append("Learned Writing Patterns / Habits:\n" + "\n".join(f"- {h}" for h in learned_state.habits.learned_writing_patterns))
            if learned_state.habits.engagement_tactics:
                prompt_parts.append("Engagement Tactics:\n" + "\n".join(f"- {t}" for t in learned_state.habits.engagement_tactics))
            
        if "interests" in context_flags:
            prompt_parts.append(f"Interests (Positive): {', '.join(persona.interests.primary + persona.interests.secondary)}")
            if learned_state.interests.emerging_topics:
                prompt_parts.append(f"Learned Emerging Interests: {', '.join(learned_state.interests.emerging_topics)}")
            if learned_state.interests.decaying_topics:
                prompt_parts.append(f"Avoid Decaying Topics: {', '.join(learned_state.interests.decaying_topics)}")
            
        if "likes" in context_flags:
            if learned_state.likes.content_preferences:
                prompt_parts.append("Learned Likes / Content Preferences:\n" + "\n".join(f"- {l}" for l in learned_state.likes.content_preferences))
            if learned_state.likes.author_archetypes:
                prompt_parts.append("Favored Author Archetypes:\n" + "\n".join(f"- {a}" for a in learned_state.likes.author_archetypes))

        if "dislikes" in context_flags:
            prompt_parts.append(f"Will Not Discuss (Hard Taboos): {', '.join(persona.interests.will_not_discuss)}")
            if learned_state.dislikes.learned_taboos:
                prompt_parts.append("Learned Dislikes / Friction Points:\n" + "\n".join(f"- {d}" for d in learned_state.dislikes.learned_taboos))
            
        if "memory" in context_flags:
            prompt_parts.append("Note: Draw on your long-term relationship memory and past experiences to influence your message.")
            
        if getattr(persona, 'system_prompt', None):
            prompt_parts.append("\n=== CUSTOM MASTER SYSTEM PROMPT ===")
            prompt_parts.append(persona.system_prompt)
        if getattr(persona, 'raw_character_card', None):
            prompt_parts.append("\n=== FULL RAW CHARACTER CARD ANCHOR (ZERO HALLUCINATION) ===")
            card_str = json.dumps(persona.raw_character_card, indent=2) if isinstance(persona.raw_character_card, dict) else str(persona.raw_character_card)
            prompt_parts.append(card_str)

        system_prompt = "\n".join(prompt_parts)

        prompt_target = context_prompt.strip() if context_prompt and context_prompt.strip() else (settings.PROMPT_POST_CREATION or "Share an authentic, witty observation on trending technology, creator lifestyle, or cinema.")

        recent_posts_block = ""
        if recent_posts:
            recent_posts_block = "Do not write anything similar to these recent posts of yours:\n" + "\n".join(f"- \"{p}\"" for p in recent_posts[:5]) + "\n\n"

        user_instruction = (
            f"Generate an authentic post/take matching this premise:\n"
            f"\"{prompt_target}\"\n\n"
            f"{recent_posts_block}"
            f"Ensure that the generated primary text is strictly under {max_chars} characters.\n"
            "Return a JSON object containing:\n"
            "{\n"
            "  \"content\": {\n"
            "    \"primary_text\": \"The main tweet body matching your persona rules\",\n"
            "    \"alternatives\": [\n"
            "      \"Alternative version 1\",\n"
            "      \"Alternative version 2\"\n"
            "    ],\n"
            "    \"suggested_hashtags\": [\"tag1\", \"tag2\"]\n"
            "  }\n"
            "}\n"
            "Return ONLY the valid JSON object, with no extra text."
        )

        # Try-Loop for validation and feedback loop (max 3 total attempts)
        feedback = ""
        client = get_ai_client()

        for attempt in range(3):
            attempt_user_prompt = user_instruction
            if feedback:
                attempt_user_prompt += f"\n\n=== FEEDBACK FROM PREVIOUS ATTEMPT ===\n{feedback}\nFix the issues above and regenerate."

            logger.info("Content generation attempt %d for slug %s", attempt + 1, profile_slug)
            try:
                # Structured parsing call
                try:
                    completion = await client.beta.chat.completions.parse(
                        model=job_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": attempt_user_prompt},
                        ],
                        response_format=ContentGenerationResponse,
                    )
                    gen_response = completion.choices[0].message.parsed
                    if not gen_response or not gen_response.content:
                        raise ValueError("No content parsed from LLM.")
                    generated = gen_response.content
                except Exception as e:
                    logger.warning("Beta chat parse failed, falling back: %s", e)
                    completion = await client.chat.completions.create(
                        model=job_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": attempt_user_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                    raw_text = clean_text_for_json(completion.choices[0].message.content or "")
                    data = json.loads(raw_text)
                    parsed_obj = ContentGenerationResponse.model_validate(data)
                    generated = parsed_obj.content

                # Validation checks
                errors = []

                # A. Character count check
                if len(generated.primary_text) > max_chars:
                    errors.append(
                        f"Primary text is {len(generated.primary_text)} characters, exceeding the limit of {max_chars}."
                    )

                # B. Banned words check (rules.never case-insensitive search)
                for rule in persona.rules.never:
                    # Look for explicit forbidden keyword/phrases from persona never rules
                    if rule.lower() in generated.primary_text.lower():
                        errors.append(
                            f"Violated 'Never Do' rule: '{rule}' is present in primary text."
                        )

                # C. Similarity check
                for p in recent_posts:
                    sim = calculate_similarity(generated.primary_text, p)
                    if sim > similarity_threshold:
                        errors.append(
                            f"Primary text is too similar (similarity ratio {sim:.2f}) to your recent post: \"{p}\"."
                        )
                        break

                # D. Specific rules heuristics
                # e.g., if writing style formatting requires no emojis and emojis are found
                no_emojis = any("no emoji" in fmt.lower() for fmt in persona.writing_style.formatting)
                if no_emojis:
                    # Emoji regex check
                    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]", flags=re.UNICODE)
                    if emoji_pattern.search(generated.primary_text):
                        errors.append("Formatting rule violation: Emojis were used but formatting specifies no emojis.")

                if not errors:
                    logger.info("Successfully validated content on attempt %d", attempt + 1)
                    return generated
                else:
                    feedback = "\n".join(errors)
                    logger.warning("Validation failed on attempt %d: %s", attempt + 1, feedback)

            except Exception as e:
                logger.error("Error during content generation attempt %d: %s", attempt, e)
                feedback = f"Error during generation: {e}"

        raise ValueError(
            f"Failed to generate valid content after 3 attempts. Last validation error: {feedback}"
        )

    async def generate_tweet(
        self,
        persona: Any,
        topic: str = "",
        draft_tweet: str | None = None,
    ) -> HookOptimizationResult:
        from xbot.ai.generator_draft import generate_tweet_draft_and_optimize
        return await generate_tweet_draft_and_optimize(self, persona, topic, draft_tweet)

    async def generate_poll(
        self,
        persona: Any,
        topic: str | None = None,
    ) -> GeneratedPoll:
        """
        Generates a Native X poll tailored to the persona's voice and niche.
        Enforces strict 2-4 options and <=25 character limits.
        """
        client = self.client if self.client is not None else get_ai_client()
        return await generate_poll(
            persona=persona,
            topic=topic,
            client=client,
        )
