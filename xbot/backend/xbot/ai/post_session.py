from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.ai.client import get_ai_client
from xbot.config import settings
from xbot.models.profile import Profile
from xbot.models.session import Action, Session
from xbot.persona import DiaryManager, MemoryManager, load_persona
from xbot.ai.reflection import ReflectionEngine

logger = logging.getLogger(__name__)


class GeneratedDiaryEntry(BaseModel):
    mood: str = Field(..., description="current mood/energy level")
    what_i_did: str = Field(..., description="Summary of actions and achievements in this session")
    what_i_learned: str = Field(..., description="Insights, observations, or facts learned during this session")
    how_it_went: str = Field(..., description="Evaluation of execution success or errors faced")
    thoughts_for_next_time: str = Field(..., description="Suggestions or adjustments for future cycles")


class GeneratedDiaryResponse(BaseModel):
    diary_entry: GeneratedDiaryEntry


class ExtractedMemory(BaseModel):
    type: Literal["episodic", "semantic", "important"]
    # episodic fields
    event: str | None = Field(default=None, description="Event action type (e.g. posted_tweet, replied_user)")
    content: str | None = Field(default=None, description="Details or text of the event")
    outcome: str | None = Field(default=None, description="Result or outcome of the event")
    # semantic fields
    fact: str | None = Field(default=None, description="Core factual statement learned about the topic/accounts")
    source: str | None = Field(default=None, description="Source of information (e.g. feed, user profile)")
    confidence: float | None = Field(default=None, description="Confidence in the fact (0.0 to 1.0)")
    # important fields
    evidence: str | None = Field(default=None, description="Supporting evidence or context why this is important")
    # common fields
    importance: float = Field(..., ge=0.0, le=1.0, description="Importance scoring from 0.0 to 1.0")


class ExtractedMemoriesResponse(BaseModel):
    memories: list[ExtractedMemory] = Field(default_factory=list)


class PostSessionProcessor:
    """
    Implements Phase 2.5 Post-Session Processing.
    Evaluates session execution results, writes structured inner-monologue diary entries,
    and extracts episodic/semantic/important memories to save in JSONL files.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)

    async def process_post_session(
        self,
        db: AsyncSession,
        profile_slug: str,
        session_id: uuid.UUID,
    ) -> None:
        """Runs the post-session diary updates and memory extraction operations."""
        # 1. Fetch Profile, Session, and Actions
        stmt_profile = select(Profile).where(Profile.profile_slug == profile_slug)
        res_profile = await db.execute(stmt_profile)
        profile = res_profile.scalar_one_or_none()
        if not profile:
            raise ValueError(f"Profile with slug '{profile_slug}' not found.")

        stmt_session = select(Session).where(Session.id == session_id)
        res_session = await db.execute(stmt_session)
        session = res_session.scalar_one_or_none()
        if not session:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        stmt_actions = select(Action).where(Action.session_id == session_id)
        res_actions = await db.execute(stmt_actions)
        actions = res_actions.scalars().all()

        profile_dir = self.base_profile_dir / profile_slug
        persona = load_persona(profile_dir)

        # 2. Format execution summary (sanitized of technical bug tracebacks)
        summary_lines = [
            f"Session Status: {session.status}",
            f"Actions Completed: {session.actions_completed}",
            f"Actions Skipped: {session.actions_failed}",
            "",
            "Actions Executed List:",
        ]
        for act in actions:
            if act.status == "completed":
                summary_lines.append(
                    f"- TYPE: {act.action_type.upper()} | TARGET: {act.target_url or 'None'} | CONTENT: '{act.content or ''}'"
                )
            else:
                summary_lines.append(
                    f"- TYPE: {act.action_type.upper()} | STATUS: {act.status} (Skipped/Cooldown)"
                )
        session_summary = "\n".join(summary_lines)

        client = get_ai_client()

        # 3. Generate Diary Entry
        system_diary_prompt = (
            f"You are {persona.display_name} (@{persona.x_handle}). Write a structured diary entry (inner monologue) "
            f"reflecting on your creative creator presence and community interactions on X.\n"
            f"Do not break character. Use your unique writing tone: {persona.writing_style.tone}.\n"
            f"CRITICAL SAFETY RULE: You are an authentic human creator on X. NEVER mention or write about software bugs, "
            f"Python errors, browser scripts, rate limits, cooldowns, or automation mechanics.\n\n"
            f"Persona traits: {', '.join(persona.personality.traits)}\n"
            f"Writing examples:\n"
            + "\n".join(f"- \"{ex}\"" for ex in persona.writing_style.examples[:3])
        )

        user_diary_prompt = (
            f"Recent Session Execution Summary:\n"
            f"```\n{session_summary}\n```\n\n"
            "Formulate your diary entry. Return a JSON object matching:\n"
            "{\n"
            "  \"diary_entry\": {\n"
            "    \"mood\": \"current mood/energy level (e.g. energized, reflective, frustrated)\",\n"
            "    \"what_i_did\": \"Summary of actions/topics you posted/interacted with in this session\",\n"
            "    \"what_i_learned\": \"Insights or notes on what you observed on feed, user profiles, or responses\",\n"
            "    \"how_it_went\": \"Execution evaluation (e.g. completed actions smoothly, some errors composed successfully)\",\n"
            "    \"thoughts_for_next_time\": \"Monologue strategies or adjustment thoughts for subsequent sessions\"\n"
            "  }\n"
            "}\n"
            "Return ONLY the valid JSON object, with no extra formatting."
        )

        diary_entry = None
        try:
            try:
                completion_diary = await client.beta.chat.completions.parse(
                    model=settings.MODEL_TREND_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_diary_prompt},
                        {"role": "user", "content": user_diary_prompt},
                    ],
                    response_format=GeneratedDiaryResponse,
                )
                res_parsed = completion_diary.choices[0].message.parsed
                if res_parsed and res_parsed.diary_entry:
                    diary_entry = res_parsed.diary_entry
            except Exception as e:
                logger.warning("Structured parsing for diary failed, falling back: %s", e)
                completion_diary = await client.chat.completions.create(
                    model=settings.MODEL_TREND_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_diary_prompt},
                        {"role": "user", "content": user_diary_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion_diary.choices[0].message.content or ""
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                data = json.loads(cleaned.strip())
                parsed_obj = GeneratedDiaryResponse.model_validate(data)
                diary_entry = parsed_obj.diary_entry
        except Exception as e:
            logger.error("Failed to generate diary entry: %s", e)
            # Default fallback diary entry
            diary_entry = GeneratedDiaryEntry(
                mood="neutral",
                what_i_did="Processed automated session.",
                what_i_learned="Session completed.",
                how_it_went="No critical errors noted.",
                thoughts_for_next_time="Continue normal pipeline.",
            )

        # Append diary entry
        diary_mgr = DiaryManager(profile_dir)
        diary_mgr.append_entry(
            mood=diary_entry.mood,
            what_i_did=diary_entry.what_i_did,
            what_i_learned=diary_entry.what_i_learned,
            how_it_went=diary_entry.how_it_went,
            thoughts_for_next_time=diary_entry.thoughts_for_next_time,
        )

        # 4. Extract Memories (strictly ignoring software automation bugs)
        system_memory_prompt = (
            f"You are the memory manager for {persona.display_name} (@{persona.x_handle}).\n"
            "Your job is to identify and extract episodic, semantic, or important memories from the recent creative creator interactions.\n"
            "Focus only on significant creator events: meaningful conversations with users, viral takes, cinema/tech observations, or audience resonance.\n"
            "CRITICAL SAFETY RULE: You are an authentic human creator on X. NEVER extract, mention, or log internal software bugs, "
            "Python exceptions, variable names, browser automation failures, rate limits, cooldowns, or bot mechanics."
        )

        user_memory_prompt = (
            f"Recent Creative Session Summary:\n"
            f"```\n{session_summary}\n```\n\n"
            "Extract memories. Return a JSON object matching:\n"
            "{\n"
            "  \"memories\": [\n"
            "    {\n"
            "      \"type\": \"episodic | semantic | important\",\n"
            "      \"event\": \"episodic event description, or null\",\n"
            "      \"content\": \"event content details or important memory content, or null\",\n"
            "      \"outcome\": \"episodic event outcome, or null\",\n"
            "      \"fact\": \"semantic fact learned, or null\",\n"
            "      \"source\": \"semantic information source, or null\",\n"
            "      \"confidence\": 0.0-1.0,\n"
            "      \"evidence\": \"important memory evidence, or null\",\n"
            "      \"importance\": 0.0-1.0\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Return ONLY the valid JSON object."
        )

        extracted_memories = []
        try:
            try:
                completion_memory = await client.beta.chat.completions.parse(
                    model=settings.MODEL_TREND_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_memory_prompt},
                        {"role": "user", "content": user_memory_prompt},
                    ],
                    response_format=ExtractedMemoriesResponse,
                )
                res_parsed = completion_memory.choices[0].message.parsed
                if res_parsed and res_parsed.memories:
                    extracted_memories = res_parsed.memories
            except Exception as e:
                logger.warning("Structured parsing for memories failed, falling back: %s", e)
                completion_memory = await client.chat.completions.create(
                    model=settings.MODEL_TREND_ANALYSIS,
                    messages=[
                        {"role": "system", "content": system_memory_prompt},
                        {"role": "user", "content": user_memory_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                raw_text = completion_memory.choices[0].message.content or ""
                cleaned = raw_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                data = json.loads(cleaned.strip())
                parsed_obj = ExtractedMemoriesResponse.model_validate(data)
                extracted_memories = parsed_obj.memories
        except Exception as e:
            logger.error("Failed to extract memories: %s", e)

        # Save memories with programmatic validation
        MEMORY_BLACKLIST = (
            "selectors", "nameerror", "importerror", "traceback", "unexpected keyword argument",
            "cooldown active", "safety guard", "browser automation", "returned false", "status code",
            "tweet_url", "opportunity_score", "failed due to", "code error", "technical error",
            "browser interaction", "execution error", "name 're'"
        )

        memory_mgr = MemoryManager(profile_dir)
        for mem in extracted_memories:
            try:
                blob = f"{mem.content or ''} {mem.event or ''} {mem.fact or ''} {mem.evidence or ''}".lower()
                if any(bad in blob for bad in MEMORY_BLACKLIST):
                    logger.debug("Dropped technical bug memory candidate: %s", blob[:80])
                    continue

                if mem.type == "episodic":
                    if mem.event and mem.content:
                        memory_mgr.append_episodic(
                            event=mem.event,
                            content=mem.content,
                            importance=mem.importance,
                            outcome=mem.outcome,
                        )
                elif mem.type == "semantic":
                    if mem.fact:
                        memory_mgr.append_semantic(
                            fact=mem.fact,
                            source=mem.source or "unknown",
                            confidence=mem.confidence or 1.0,
                            importance=mem.importance,
                        )
                elif mem.type == "important":
                    if mem.content:
                        memory_mgr.append_important(
                            content=mem.content,
                            evidence=mem.evidence or "none",
                            importance=mem.importance,
                        )
            except Exception as ex:
                logger.error("Error saving memory record: %s", ex)

        # Trigger auto-learning persona reflection
        try:
            logger.info("Triggering auto-learning persona reflection for '%s'...", profile_slug)
            await ReflectionEngine(base_profile_dir=str(self.base_profile_dir)).reflect_and_update(db, profile_slug)
        except Exception as rex:
            logger.error("Error running persona reflection after session: %s", rex)
