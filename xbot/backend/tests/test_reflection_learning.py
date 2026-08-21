from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from ruamel.yaml import YAML
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.reflection import ReflectionEngine, ReflectionResponse
from xbot.api.sessions import normalize_event_payload
from xbot.models.base import Base
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona import (
    LearnedCharacteristics,
    LearnedDislikes,
    LearnedHabits,
    LearnedInterests,
    LearnedLikes,
    LearnedPersonality,
    LearnedState,
    load_learned_state,
)

yaml = YAML(typ="safe")
yaml.default_flow_style = False

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
SessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


def populate_test_profile(profile_dir: Path, profile_slug: str = "test_persona") -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    persona_data = {
        "id": profile_slug,
        "display_name": "Test Persona AI",
        "x_handle": "@testpersona",
        "identity": {
            "background": "AI and engineering builder discussing cutting-edge tech."
        },
        "personality": {
            "traits": ["analytical", "concise", "opinionated"],
            "values": ["truth", "builder mentality"],
            "communication_style": "direct and clear",
        },
        "interests": {
            "primary": ["artificial intelligence", "software engineering", "distributed systems"],
            "secondary": ["startups", "open source"],
            "will_not_discuss": ["politics", "celebrity gossip"],
        },
        "writing_style": {
            "tone": "confident and technical",
            "typical_length": "short",
            "formatting": ["bullet points", "code snippets"],
            "examples": ["Build in public.", "Latency matters."],
        },
        "goals": {
            "short_term": ["Grow high-signal tech audience"],
            "long_term": ["Establish authority in AI tooling"],
            "content_pillars": ["AI Architecture", "Performance Optimization"],
        },
        "rules": {
            "always": ["Provide actionable takeaways"],
            "never": ["Use generic corporate buzzwords"],
        },
    }
    with (profile_dir / "persona.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(persona_data, f)


@pytest.mark.asyncio
async def test_reflection_with_performance_feedback(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    profile_slug = "tech_creator"
    profile_dir = tmp_path / profile_slug
    populate_test_profile(profile_dir, profile_slug)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@techcreator",
        display_name="Tech Creator",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    # Add past posted tweet
    content = Content(
        profile_id=profile.id,
        body="Deep dive into vector databases and indexing strategies for LLMs.",
        status=ContentStatus.POSTED,
        posted_at=datetime.datetime.utcnow(),
    )
    db_session.add(content)
    await db_session.commit()

    engine = ReflectionEngine(base_profile_dir=str(tmp_path))

    # Mock response from LLM
    mock_reflection = ReflectionResponse(
        behavioral_adaptations=[
            "Focus on deep technical teardowns rather than high-level summaries",
            "Post benchmark diagrams with concrete latency figures",
        ],
        evolving_nuances=[
            "More authoritative and analytical tone on indexing internals",
        ],
        learned_writing_patterns=[
            "Lead with unexpected performance bottleneck, followed by resolution",
        ],
        engagement_tactics=[
            "Ask clarifying implementation questions in replies to lead engineers",
        ],
        emerging_topics=[
            "HNSW vs IVF indexing trade-offs",
            "Quantized embeddings in production",
        ],
        decaying_topics=[
            "Generic AI hype news",
        ],
        content_preferences=[
            "Code snippet comparisons",
            "Production post-mortems",
        ],
        author_archetypes=[
            "Infrastructure engineers",
            "Open source maintainers",
        ],
        learned_taboos=[
            "Overly broad listicle threads with no benchmark numbers",
        ],
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = mock_reflection
    mock_completion = MagicMock()
    mock_completion.choices = [mock_parsed_choice]

    recent_performance = {
        "follower_delta": 42,
        "impressions": 85000,
        "engagement_rate": "4.2%",
        "top_tweets": [
            {
                "text": "Vector search latency dropped 4x after tuning HNSW M and efConstruction parameters.",
                "likes": 320,
                "retweets": 84,
                "impressions": 45000,
                "replies": 28,
            }
        ],
        "low_performing_tweets": [
            {
                "text": "AI is changing the world very quickly today!",
                "likes": 2,
                "retweets": 0,
                "impressions": 120,
            }
        ],
    }

    with patch("xbot.ai.reflection.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        mock_get_client.return_value = mock_client

        updated_state = await engine.reflect_and_update(
            db=db_session,
            profile_slug=profile_slug,
            recent_performance=recent_performance,
        )

        # Verify client was called
        mock_client.beta.chat.completions.parse.assert_called_once()
        call_kwargs = mock_client.beta.chat.completions.parse.call_args.kwargs
        messages = call_kwargs["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")

        # Verify performance metrics are included in the prompt
        assert "Audience Feedback & Tweet Performance:" in user_content
        assert "Follower Change: +42" in user_content
        assert "Total Impressions: 85000" in user_content
        assert "Engagement Rate: 4.2%" in user_content
        assert "Top Performing Posts (High Engagement):" in user_content
        assert "Vector search latency dropped 4x" in user_content
        assert "320 likes, 84 reposts, 28 replies, 45000 impressions" in user_content
        assert "Low Performing Posts (Low Engagement):" in user_content
        assert "AI is changing the world very quickly today!" in user_content

        # Verify learned state was synthesized and updated
        assert updated_state.reflection_count == 1
        assert updated_state.last_reflected_at is not None
        assert "Focus on deep technical teardowns rather than high-level summaries" in updated_state.characteristics.behavioral_adaptations
        assert "HNSW vs IVF indexing trade-offs" in updated_state.interests.emerging_topics
        assert "Generic AI hype news" in updated_state.interests.decaying_topics
        assert "Overly broad listicle threads with no benchmark numbers" in updated_state.dislikes.learned_taboos

        # Verify state is persisted to disk
        persisted_state = load_learned_state(profile_dir)
        assert persisted_state.reflection_count == 1
        assert len(persisted_state.characteristics.behavioral_adaptations) > 0


@pytest.mark.asyncio
async def test_reflection_fallback_json_parsing(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    profile_slug = "fallback_creator"
    profile_dir = tmp_path / profile_slug
    populate_test_profile(profile_dir, profile_slug)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@fallback",
        display_name="Fallback Creator",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    engine = ReflectionEngine(base_profile_dir=str(tmp_path))

    fallback_payload = {
        "behavioral_adaptations": ["Use concise code snippets"],
        "evolving_nuances": ["Calm and deliberate cadence"],
        "learned_writing_patterns": ["Short opening hooks"],
        "engagement_tactics": ["Reply quickly to domain experts"],
        "emerging_topics": ["Agent memory systems"],
        "decaying_topics": ["Basic Python tutorials"],
        "content_preferences": ["Architecture blueprints"],
        "author_archetypes": ["Principal Engineers"],
        "learned_taboos": ["Clickbait titles"],
    }

    mock_chat_choice = MagicMock()
    mock_chat_choice.message.content = f"```json\n{json.dumps(fallback_payload)}\n```"
    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = [mock_chat_choice]

    with patch("xbot.ai.reflection.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Schema validation failed")
        mock_client.chat.completions.create.return_value = mock_chat_completion
        mock_get_client.return_value = mock_client

        updated_state = await engine.reflect_and_update(
            db=db_session,
            profile_slug=profile_slug,
            recent_performance={"follower_delta": 5},
        )

        mock_client.chat.completions.create.assert_called_once()
        assert updated_state.reflection_count == 1
        assert "Agent memory systems" in updated_state.interests.emerging_topics


@pytest.mark.asyncio
async def test_reflection_without_explicit_performance_uses_db_metrics(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    profile_slug = "db_metric_creator"
    profile_dir = tmp_path / profile_slug
    populate_test_profile(profile_dir, profile_slug)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@dbmetrics",
        display_name="DB Metrics Creator",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    # Add content with performance
    content = Content(
        profile_id=profile.id,
        body="Benchmarks on SQLite vs PostgreSQL async engines.",
        status=ContentStatus.POSTED,
        posted_at=datetime.datetime.utcnow(),
        performance={"likes": 120, "retweets": 45, "impressions": 15000},
    )
    db_session.add(content)
    await db_session.commit()

    engine = ReflectionEngine(base_profile_dir=str(tmp_path))

    mock_reflection = ReflectionResponse(
        behavioral_adaptations=["Benchmark comparisons drive high engagement"],
        emerging_topics=["Database performance tuning"],
    )
    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message.parsed = mock_reflection
    mock_completion = MagicMock()
    mock_completion.choices = [mock_parsed_choice]

    with patch("xbot.ai.reflection.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_completion
        mock_get_client.return_value = mock_client

        # Calling with recent_performance=None
        updated_state = await engine.reflect_and_update(
            db=db_session,
            profile_slug=profile_slug,
            recent_performance=None,
        )

        mock_client.beta.chat.completions.parse.assert_called_once()
        call_kwargs = mock_client.beta.chat.completions.parse.call_args.kwargs
        messages = call_kwargs["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")

        assert "Recent Post Metrics:" in user_content
        assert "Benchmarks on SQLite vs PostgreSQL async engines." in user_content
        assert "likes" in user_content
        assert updated_state.reflection_count == 1
        assert "Benchmark comparisons drive high engagement" in updated_state.characteristics.behavioral_adaptations


@pytest.mark.asyncio
async def test_reflection_missing_profile_raises(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    engine = ReflectionEngine(base_profile_dir=str(tmp_path))
    with pytest.raises(ValueError, match="Profile 'non_existent' not found."):
        await engine.reflect_and_update(db_session, "non_existent")


def test_normalize_event_payload() -> None:
    # Test dictionary with existing keys
    payload = {
        "event": "action_complete",
        "timestamp": "2026-08-21T12:00:00Z",
        "session_id": "11111111-1111-1111-1111-111111111111",
        "action_type": "post",
        "status": "completed",
        "content": "Hello World",
        "error": None,
        "custom_field": 42,
    }
    normalized = normalize_event_payload(payload)
    assert normalized["event"] == "action_complete"
    assert normalized["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert normalized["action_type"] == "post"
    assert normalized["status"] == "completed"
    assert normalized["content"] == "Hello World"
    assert normalized["custom_field"] == 42

    # Test JSON string payload
    raw_str = json.dumps({"event": "mock_mode_active", "message": "Simulation active"})
    normalized_str = normalize_event_payload(raw_str, fallback_session_id="22222222-2222-2222-2222-222222222222")
    assert normalized_str["event"] == "mock_mode_active"
    assert normalized_str["session_id"] == "22222222-2222-2222-2222-222222222222"
    assert "timestamp" in normalized_str
    assert normalized_str["message"] == "Simulation active"

    # Test byte payload
    raw_bytes = b'{"status": "queued", "action_type": "like"}'
    normalized_bytes = normalize_event_payload(raw_bytes, fallback_session_id="33333333-3333-3333-3333-333333333333")
    assert normalized_bytes["session_id"] == "33333333-3333-3333-3333-333333333333"
    assert normalized_bytes["action_type"] == "like"
    assert normalized_bytes["status"] == "queued"
