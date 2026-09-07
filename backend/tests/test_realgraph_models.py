import datetime
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.realgraph import RealGraphEdge, ConversationThread


@pytest.mark.asyncio
async def test_realgraph_edge_creation_and_affinity():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as async_db:
        profile = Profile(
            id=uuid.uuid4(),
            profile_slug="test_realgraph_user",
            x_handle="testuser",
            display_name="Test User",
            status=ProfileStatus.ACTIVE,
        )
        async_db.add(profile)
        await async_db.commit()

        edge = RealGraphEdge(
            profile_id=profile.id,
            target_handle="karpathy",
            target_user_id="123456",
            is_verified=True,
            niche="tech",
            outbound_replies_count=3,
            inbound_author_replies_count=2,
            reciprocal_score=75.5,
            author_reply_rate=0.66,
            topics_discussed=["vllm", "kv cache", "speculative decoding"],
            recent_interactions=[{"tweet_id": "999888", "type": "author_reply", "text": "Spot on!"}],
        )
        async_db.add(edge)
        await async_db.commit()

        res = await async_db.execute(select(RealGraphEdge).where(RealGraphEdge.target_handle == "karpathy"))
        saved_edge = res.scalar_one()

        assert saved_edge is not None
        assert saved_edge.is_verified is True
        assert saved_edge.reciprocal_score == 75.5
        assert len(saved_edge.topics_discussed) == 3
        assert saved_edge.topics_discussed[0] == "vllm"
        assert "karpathy" in repr(saved_edge)

    await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_thread_and_15m_sla():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as async_db:
        profile = Profile(
            id=uuid.uuid4(),
            profile_slug="test_thread_user",
            x_handle="threaduser",
            display_name="Thread User",
            status=ProfileStatus.ACTIVE,
        )
        async_db.add(profile)
        await async_db.commit()

        now = datetime.datetime.utcnow()
        deadline = now + datetime.timedelta(minutes=15)

        thread = ConversationThread(
            profile_id=profile.id,
            root_tweet_id="111222333",
            parent_tweet_id="111222444",
            target_handle="sama",
            target_is_verified=True,
            turn_count=2,
            max_turns=3,
            status="awaiting_reply",
            deadline_15m=deadline,
            conversation_history=[
                {"turn": 1, "sender": "bot", "text": "What about latency?"},
                {"turn": 2, "sender": "sama", "text": "Hardware limits are easing."},
            ],
        )
        async_db.add(thread)
        await async_db.commit()

        res = await async_db.execute(select(ConversationThread).where(ConversationThread.root_tweet_id == "111222333"))
        saved_thread = res.scalar_one()

        assert saved_thread.target_handle == "sama"
        assert saved_thread.turn_count == 2
        assert saved_thread.status == "awaiting_reply"
        assert len(saved_thread.conversation_history) == 2
        assert saved_thread.deadline_15m >= now

    await engine.dispose()
