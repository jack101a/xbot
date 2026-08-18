from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
import pytest_asyncio
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.trend_generator import TrendEvaluation
from xbot.ai.trend_radar import TrendItem
from xbot.celery_app import celery_app
from xbot.config import settings
from xbot.models.base import Base
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Personality,
    Persona,
    Rules,
    WritingStyle,
)

TEST_DB_URL = "sqlite+aiosqlite:///test_temp_trend_task.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
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
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
def clean_redis() -> None:
    r = redis.from_url(settings.REDIS_URL)
    keys = r.keys("xbot:seen_trends:*")
    if keys:
        r.delete(*keys)
    yield
    keys = r.keys("xbot:seen_trends:*")
    if keys:
        r.delete(*keys)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="tech_analyst",
        display_name="Tech Analyst",
        x_handle="@techanalyst",
        identity=Identity(
            background="AI and systems researcher tracking breaking developments.",
            occupation="Systems Analyst",
        ),
        personality=Personality(
            traits=["analytical", "sharp", "insightful"],
            values=["truth", "clarity"],
            communication_style="Direct, high-density analysis",
        ),
        interests=Interests(
            primary=["AI Infrastructure", "LLMs", "Distributed Systems"],
            secondary=["Semiconductors"],
            will_not_discuss=["memecoins", "celebrity gossip"],
        ),
        writing_style=WritingStyle(
            tone="sharp, authoritative, insightful",
            typical_length="short",
            formatting=["no hashtags"],
            examples=["Hardware efficiency dictates model capability."],
        ),
        goals=Goals(
            short_term=["break down technical news fast"],
            long_term=["top tier technical voice"],
            content_pillars=["Infra scaling", "AI architecture"],
        ),
        rules=Rules(
            always=["provide technical insight", "keep hook punchy"],
            never=["use buzzwords", "use hashtags"],
        ),
    )


def test_celery_schedule_registered() -> None:
    """Verifies that the periodic schedule for check_trend_radar is registered in celery_app."""
    schedule = celery_app.conf.beat_schedule.get("check-trend-radar-every-1800-seconds")
    assert schedule is not None, "Schedule 'check-trend-radar-every-1800-seconds' not found in beat_schedule"
    assert schedule["task"] == "xbot.tasks.check_trend_radar"
    assert schedule["schedule"] == 1800.0


@pytest.mark.asyncio
async def test_check_trend_radar_executes_and_stages_content(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Tests active profile fetches trends, evaluates relevance, stages Content record, and caches in Redis."""
    from xbot.tasks import _check_trend_radar_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@techanalyst",
        display_name="Tech Analyst",
        profile_slug="test_trend_profile",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    sample_items = [
        TrendItem(
            id="trend_item_1",
            title="Next-gen GPU cluster delivers 3x throughput for LLM inference",
            summary="New interconnect architecture removes memory bandwidth bottlenecks.",
            source_url="https://news.ycombinator.com/item?id=1001",
            source_name="Hacker News",
            published_at="2026-08-18T10:00:00Z",
        ),
        TrendItem(
            id="trend_item_2",
            title="OpenAI announces sub-millisecond spec decoding benchmark",
            summary="Speculative decoding achieves 5x speedups on commodity hardware.",
            source_url="https://news.ycombinator.com/item?id=1002",
            source_name="Hacker News",
            published_at="2026-08-18T10:30:00Z",
        ),
    ]

    mock_eval_1 = TrendEvaluation(
        is_relevant=True,
        relevance_score=0.94,
        reasoning="Directly impacts AI Infrastructure and LLM inference scaling.",
        key_takeaways=["3x throughput bump", "Removes memory bandwidth bottleneck"],
        hot_take="Interconnect topology is now more critical than raw FLOPS.",
        draft_post="3x throughput for LLM inference via new interconnect topology.\n\nRaw FLOPS mean nothing if memory bus stays saturated.",
        optimized_post="Interconnect topology just became the #1 bottleneck in AI inference.\n\nNew architectures show 3x throughput gains.",
    )

    mock_eval_2 = TrendEvaluation(
        is_relevant=True,
        relevance_score=0.91,
        reasoning="Speculative decoding is a key LLM inference optimization.",
        key_takeaways=["5x speedup with speculative decoding", "Runs on commodity chips"],
        hot_take="Model optimization software is eating hardware margins.",
        draft_post="Speculative decoding hits 5x speedups.\n\nSoftware optimization is moving faster than silicon iterations.",
        optimized_post="Software optimization is moving 3x faster than silicon.\n\nSpeculative decoding hits 5x speedups on standard GPUs.",
    )

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.fetch_rss_trends", AsyncMock(return_value=sample_items)) as mock_fetch, \
         patch("xbot.tasks.generate_trend_take", AsyncMock(side_effect=[mock_eval_1, mock_eval_2])) as mock_eval:

        result = await _check_trend_radar_async()

        assert result["status"] == "success"
        assert result["profiles_processed"] == 1
        assert result["items_scanned"] == 2
        assert result["items_staged"] == 2

        mock_fetch.assert_called_once()
        assert mock_eval.call_count == 2

        # Verify Content records created in DB
        stmt = select(Content).where(Content.profile_id == profile_id)
        res = await db_session.execute(stmt)
        staged_contents = res.scalars().all()
        assert len(staged_contents) == 2

        # Check content attributes
        c1 = next(c for c in staged_contents if "Interconnect topology" in c.body)
        assert c1.status in (ContentStatus.APPROVED, ContentStatus.DRAFT)
        assert c1.content_type in (ContentType.ORIGINAL, ContentType.TWEET)
        assert c1.text == c1.body
        assert c1.ai_metadata is not None
        assert c1.ai_metadata["trend_id"] == "trend_item_1"
        assert c1.ai_metadata["relevance_score"] == 0.94
        assert c1.ai_metadata["hot_take"] == "Interconnect topology is now more critical than raw FLOPS."

        # Verify Redis deduplication keys set
        r = redis.from_url(settings.REDIS_URL)
        assert r.exists(f"xbot:seen_trends:{profile_id}:trend_item_1")
        assert r.exists(f"xbot:seen_trends:{profile_id}:trend_item_2")
        assert r.sismember(f"xbot:seen_trends:{profile_id}", "trend_item_1")
        assert r.sismember(f"xbot:seen_trends:{profile_id}", "trend_item_2")


@pytest.mark.asyncio
async def test_check_trend_radar_redis_deduplication(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Tests that previously seen trend items are skipped and not re-evaluated."""
    from xbot.tasks import _check_trend_radar_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@techanalyst",
        display_name="Tech Analyst",
        profile_slug="test_trend_dedup",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    seen_item_id = "already_seen_100"
    r = redis.from_url(settings.REDIS_URL)
    r.set(f"xbot:seen_trends:{profile_id}:{seen_item_id}", "1", ex=604800)

    items = [
        TrendItem(
            id=seen_item_id,
            title="Already seen trend article",
            source_url="https://news.ycombinator.com/item?id=100",
            source_name="Hacker News",
        )
    ]

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.fetch_rss_trends", AsyncMock(return_value=items)), \
         patch("xbot.tasks.generate_trend_take", AsyncMock()) as mock_eval:

        result = await _check_trend_radar_async()

        assert result["status"] == "success"
        assert result["items_staged"] == 0
        mock_eval.assert_not_called()

        stmt = select(Content).where(Content.profile_id == profile_id)
        res = await db_session.execute(stmt)
        assert len(res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_check_trend_radar_skips_irrelevant_trends(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Tests that items deemed irrelevant by LLM are cached in Redis but not staged as Content."""
    from xbot.tasks import _check_trend_radar_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@techanalyst",
        display_name="Tech Analyst",
        profile_slug="test_trend_irrelevant",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    irrelevant_item = TrendItem(
        id="gossip_item_99",
        title="Celebrity red carpet fashion breakdown",
        source_url="https://popculture.com/item?id=99",
        source_name="Pop News",
    )

    mock_eval = TrendEvaluation(
        is_relevant=False,
        relevance_score=0.12,
        reasoning="Celebrity fashion has zero relevance to tech analyst niche.",
        key_takeaways=[],
        hot_take="",
        draft_post="",
        optimized_post="",
    )

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.fetch_rss_trends", AsyncMock(return_value=[irrelevant_item])), \
         patch("xbot.tasks.generate_trend_take", AsyncMock(return_value=mock_eval)):

        result = await _check_trend_radar_async()

        assert result["status"] == "success"
        assert result["items_staged"] == 0

        # Verify no Content record staged
        stmt = select(Content).where(Content.profile_id == profile_id)
        res = await db_session.execute(stmt)
        assert len(res.scalars().all()) == 0

        # Verify cached in Redis so we don't re-analyze
        r = redis.from_url(settings.REDIS_URL)
        assert r.exists(f"xbot:seen_trends:{profile_id}:gossip_item_99")


@pytest.mark.asyncio
async def test_check_trend_radar_profile_error_isolation(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Tests that a failure in one profile (e.g. corrupted persona) does not halt processing of other profiles."""
    from xbot.tasks import _check_trend_radar_async

    # Profile 1: will fail on persona load
    profile1 = Profile(
        id=uuid.uuid4(),
        x_handle="@failing_profile",
        display_name="Failing Profile",
        profile_slug="failing_slug",
        status=ProfileStatus.ACTIVE,
    )
    # Profile 2: healthy profile
    profile2 = Profile(
        id=uuid.uuid4(),
        x_handle="@healthy_profile",
        display_name="Healthy Profile",
        profile_slug="healthy_slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add_all([profile1, profile2])
    await db_session.commit()

    healthy_item = TrendItem(
        id="healthy_trend_1",
        title="Breakthrough in wafer-scale GPU interconnects",
        source_url="https://news.ycombinator.com/item?id=2001",
        source_name="Hacker News",
    )
    mock_eval = TrendEvaluation(
        is_relevant=True,
        relevance_score=0.95,
        reasoning="Core semiconductor and infra topic.",
        key_takeaways=["Wafer scale packaging"],
        hot_take="Packaging innovation is the new Moore's law.",
        draft_post="Wafer-scale packaging is rewriting interconnect physics.",
        optimized_post="Packaging innovation is the new Moore's law.\n\nWafer-scale chips eliminate off-die latency bottlenecks.",
    )

    def mock_load_persona(p_dir: Path) -> Persona:
        if "failing_slug" in str(p_dir):
            raise FileNotFoundError("Corrupted persona.yaml")
        return sample_persona

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", side_effect=mock_load_persona), \
         patch("xbot.tasks.fetch_rss_trends", AsyncMock(return_value=[healthy_item])), \
         patch("xbot.tasks.generate_trend_take", AsyncMock(return_value=mock_eval)):

        result = await _check_trend_radar_async()

        assert result["status"] == "partial_success"
        assert result["profiles_processed"] == 2
        assert result["items_staged"] == 1
        assert result["errors"] is not None
        assert any("failing_slug" in err for err in result["errors"])

        # Verify healthy profile staged content
        stmt = select(Content).where(Content.profile_id == profile2.id)
        res = await db_session.execute(stmt)
        assert len(res.scalars().all()) == 1


@pytest.mark.asyncio
async def test_check_trend_radar_custom_feed_urls_and_keywords(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Tests that custom trend_sources in persona are passed to fetch_rss_trends."""
    from xbot.tasks import _check_trend_radar_async

    # Add custom trend_sources to persona
    sample_persona.raw_character_card = {
        "trend_sources": {
            "rss_feeds": ["https://arxiv.org/rss/cs.AI", "https://github.blog/feed/"],
            "keywords": ["transformer", "inference", "kernel"],
        }
    }
    setattr(sample_persona, "trend_sources", {
        "rss_feeds": ["https://arxiv.org/rss/cs.AI", "https://github.blog/feed/"],
        "keywords": ["transformer", "inference", "kernel"],
    })

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@techanalyst",
        display_name="Tech Analyst",
        profile_slug="test_custom_feed_slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.fetch_rss_trends", AsyncMock(return_value=[])) as mock_fetch:

        result = await _check_trend_radar_async()

        assert result["status"] == "success"
        mock_fetch.assert_called_once_with(
            ["https://arxiv.org/rss/cs.AI", "https://github.blog/feed/"],
            keywords=["transformer", "inference", "kernel"],
        )


def test_celery_task_wrapper() -> None:
    """Tests calling the synchronous Celery task wrapper check_trend_radar."""
    from xbot.tasks import check_trend_radar

    with patch("xbot.tasks._check_trend_radar_async", AsyncMock(return_value={"status": "success", "items_staged": 3})):
        res = check_trend_radar()
        assert res == {"status": "success", "items_staged": 3}
