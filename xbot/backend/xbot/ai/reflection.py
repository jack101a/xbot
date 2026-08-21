from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile
from xbot.persona import (
    LearnedCharacteristics,
    LearnedDislikes,
    LearnedHabits,
    LearnedInterests,
    LearnedLikes,
    LearnedPersonality,
    LearnedState,
    MemoryManager,
    load_learned_state,
    load_persona,
    save_learned_state,
)

logger = logging.getLogger(__name__)


class ReflectionResponse(BaseModel):
    behavioral_adaptations: list[str] = Field(default_factory=list)
    evolving_nuances: list[str] = Field(default_factory=list)
    learned_writing_patterns: list[str] = Field(default_factory=list)
    engagement_tactics: list[str] = Field(default_factory=list)
    emerging_topics: list[str] = Field(default_factory=list)
    decaying_topics: list[str] = Field(default_factory=list)
    content_preferences: list[str] = Field(default_factory=list)
    author_archetypes: list[str] = Field(default_factory=list)
    learned_taboos: list[str] = Field(default_factory=list)


class ReflectionEngine:
    """
    Evaluates recent session logs, episodic memories, and content performance
    to synthesize updates to the profile's dynamic LearnedState.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def reflect_and_update(
        self, db: AsyncSession, profile_slug: str
    ) -> LearnedState:
        stmt = select(Profile).where(Profile.profile_slug == profile_slug)
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile '{profile_slug}' not found.")

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)
        learned_state = load_learned_state(profile_dir)
        memory_mgr = MemoryManager(profile_dir)

        # Retrieve recent episodic memories and recent posted content
        recent_memories = memory_mgr.retrieve_memories(recency_limit=40)
        stmt_posts = (
            select(Content)
            .where(
                Content.profile_id == profile.id,
                Content.status == ContentStatus.POSTED,
            )
            .order_by(Content.posted_at.desc())
            .limit(15)
        )
        res_posts = await db.execute(stmt_posts)
        recent_posts = [f"- {c.body}" for c in res_posts.scalars().all()]

        memory_summary = "\n".join(
            [f"- [{m.get('type')}] {m.get('event', '')}: {m.get('content', '')}" for m in recent_memories]
        )
        posts_summary = "\n".join(recent_posts)

        system_prompt = (
            f"You are the analytical subconscious reflection engine for X persona @{persona.x_handle} ({persona.display_name}).\n"
            f"Your job is to review recent interactions, memories, and posted tweets, and synthesize an updated LearnedState across 7 categories:\n"
            f"1. Characteristics (behavioral adaptations based on what succeeds)\n"
            f"2. Personality (evolving emotional nuances or voice adjustments)\n"
            f"3. Habits (learned writing patterns, formatting preferences, engagement tactics)\n"
            f"4. Interests (emerging niche topics discovered, decaying topics to avoid)\n"
            f"5. Likes (content preferences, author archetypes that yield positive ROI)\n"
            f"6. Dislikes (learned taboos, toxic hashtags or thread styles to skip)\n\n"
            f"=== IMMUTABLE BEDROCK (DO NOT CONFLICT WITH THIS) ===\n"
            f"Core Background: {persona.identity.background}\n"
            f"Core Traits: {', '.join(persona.personality.traits)}\n"
            f"Primary Interests: {', '.join(persona.interests.primary)}\n"
            f"Hard Taboos: {', '.join(persona.interests.will_not_discuss)}\n\n"
            f"=== CURRENT LEARNED STATE ===\n"
            f"{json.dumps(learned_state.model_dump(), indent=2)}\n\n"
            f"Synthesize the updated lists. Retain existing good lessons while adding new ones or removing outdated/bad ones."
        )

        user_prompt = (
            f"Recent Memories & Events:\n{memory_summary or 'No recent memories.'}\n\n"
            f"Recent Outgoing Posts/Replies:\n{posts_summary or 'No recent posts.'}\n\n"
            "Return a JSON object matching ReflectionResponse schema."
        )

        client = get_ai_client()
        model_name = settings.MODEL_TREND_ANALYSIS or settings.LITELLM_PRIMARY_MODEL

        try:
            try:
                completion = await client.beta.chat.completions.parse(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=ReflectionResponse,
                )
                parsed = completion.choices[0].message.parsed
            except Exception as e:
                logger.warning("Beta parse failed for reflection, falling back to json_object: %s", e)
                completion = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion.choices[0].message.content or "{}"
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                parsed = ReflectionResponse.model_validate(json.loads(cleaned.strip()))

            if parsed:
                learned_state.characteristics = LearnedCharacteristics(behavioral_adaptations=parsed.behavioral_adaptations[:10])
                learned_state.personality = LearnedPersonality(evolving_nuances=parsed.evolving_nuances[:10])
                learned_state.habits = LearnedHabits(
                    learned_writing_patterns=parsed.learned_writing_patterns[:10],
                    engagement_tactics=parsed.engagement_tactics[:10],
                )
                learned_state.interests = LearnedInterests(
                    emerging_topics=parsed.emerging_topics[:10],
                    decaying_topics=parsed.decaying_topics[:10],
                )
                learned_state.likes = LearnedLikes(
                    content_preferences=parsed.content_preferences[:10],
                    author_archetypes=parsed.author_archetypes[:10],
                )
                learned_state.dislikes = LearnedDislikes(learned_taboos=parsed.learned_taboos[:10])
                learned_state.last_reflected_at = datetime.datetime.utcnow().isoformat() + "Z"
                learned_state.reflection_count += 1

                save_learned_state(profile_dir, learned_state)
                logger.info("Successfully reflected and updated learned_state for profile '%s'.", profile_slug)
                return learned_state
            else:
                raise ValueError("No reflection parsed.")
        except Exception as e:
            logger.error("Reflection failed for profile '%s': %s", profile_slug, e)
            return learned_state
