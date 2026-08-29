import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.realgraph import ConversationThread, RealGraphEdge
from xbot.models.session import Action
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Personality,
    Persona,
    Rules,
    WritingStyle,
)
from xbot.tasks import _fast_response_sentinel_async


@pytest.mark.asyncio
async def test_fast_response_sentinel_turn_progression(tmp_path):
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    # Create dummy profile directory with config
    profile_dir = tmp_path / "test_fast_user"
    profile_dir.mkdir()
    (profile_dir / "config.yaml").write_text("mock_mode: true\nschedule:\n  timezone: 'UTC'\n")

    sample_persona = Persona(
        id="test_fast_user",
        display_name="Test Bot",
        x_handle="@testbot",
        identity=Identity(background="AI Systems Architect", occupation="Engineer"),
        personality=Personality(
            traits=["analytical", "concise"],
            values=["clarity"],
            communication_style="Direct and technical",
        ),
        interests=Interests(
            primary=["Distributed Systems", "LLM Inference"],
            secondary=["Compilers"],
            will_not_discuss=["Spam"],
        ),
        writing_style=WritingStyle(
            tone="sharp, witty, technical",
            typical_length="short",
            formatting=["clean spacing"],
            examples=["Latency is all about memory bandwidth."],
        ),
        goals=Goals(
            short_term=["Build technical community"],
            long_term=["Authority in AI systems"],
            content_pillars=["Inference optimizations"],
        ),
        rules=Rules(
            always=["Stay concise", "End with debate question"],
            never=["Generic fluff", "Banned buzzwords"],
        ),
    )

    async with session_maker() as session:
        profile = Profile(
            id=uuid.uuid4(),
            profile_slug="test_fast_user",
            x_handle="testbot",
            display_name="Test Bot",
            status=ProfileStatus.ACTIVE,
        )
        session.add(profile)
        await session.commit()

        # Add active thread
        now = datetime.datetime.utcnow()
        thread = ConversationThread(
            profile_id=profile.id,
            root_tweet_id="99887766",
            parent_tweet_id="99887766",
            target_handle="karpathy",
            target_is_verified=True,
            turn_count=1,
            max_turns=2,
            status="active",
            deadline_15m=now + datetime.timedelta(minutes=10),
            conversation_history=[{"turn": 1, "sender": "karpathy", "text": "What are your thoughts on token latency?"}],
        )
        session.add(thread)
        await session.commit()

    # Mock DB session in tasks, Redis, SafetyGuard and AI client
    mock_ai_resp = MagicMock()
    mock_ai_resp.choices = [MagicMock(message=MagicMock(content="We prioritize KV cache compression to maintain throughput. Is batch size your primary constraint?"))]

    mock_ai_client = MagicMock()
    mock_ai_client.chat.completions.create = AsyncMock(return_value=mock_ai_resp)

    mock_redis = MagicMock()
    mock_redis.set.return_value = True

    with patch("xbot.tasks.AsyncSessionLocal", session_maker), \
         patch("xbot.tasks.redis.from_url", return_value=mock_redis), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.SafetyGuard.is_action_safe", AsyncMock(return_value=True)), \
         patch("xbot.tasks.SafetyGuard.record_action_success", AsyncMock()), \
         patch("xbot.tasks.get_ai_client", return_value=mock_ai_client):
        res = await _fast_response_sentinel_async(base_profile_dir=tmp_path)
        assert res["status"] == "success"
        assert res["threads_checked"] == 1
        assert res["replies_posted"] == 1

    # Verify DB state after turn execution
    async with session_maker() as session:
        res_th = await session.execute(select(ConversationThread).where(ConversationThread.root_tweet_id == "99887766"))
        saved_th = res_th.scalar_one()

        assert saved_th.turn_count == 2
        # Max turns reached -> status closed
        assert saved_th.status == "closed"
        assert len(saved_th.conversation_history) == 2
        assert "?" in saved_th.conversation_history[-1]["text"]

        # Check RealGraphEdge created
        res_rg = await session.execute(select(RealGraphEdge).where(RealGraphEdge.target_handle == "karpathy"))
        saved_rg = res_rg.scalar_one()
        assert saved_rg is not None
        assert saved_rg.is_verified is True
        assert saved_rg.reciprocal_score >= 25.0

    await test_engine.dispose()
