from __future__ import annotations

import datetime
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
import pytest_asyncio
import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.generator import ContentGenerator
from xbot.ai.hook_optimizer import HookCandidate, HookOptimizationResult
from xbot.ai.poll_generator import GeneratedPoll
from xbot.config import settings
from xbot.models.base import Base
from xbot.models.content import Content, ContentStatus, ContentType
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.session import Action, ActionStatus, ActionType, Session, SessionStatus
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Personality,
    Persona,
    Rules,
    WritingStyle,
)

TEST_DB_URL = "sqlite+aiosqlite:///test_temp_poll_integration.db"
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
    keys = r.keys("xbot:seen_tweets:*") + r.keys("lock:browser:*") + r.keys("rate:*") + r.keys("cooldown:*")
    if keys:
        r.delete(*keys)
    yield
    keys = r.keys("xbot:seen_tweets:*") + r.keys("lock:browser:*") + r.keys("rate:*") + r.keys("cooldown:*")
    if keys:
        r.delete(*keys)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="tech_founder",
        display_name="Alex River",
        x_handle="@alexriver",
        identity=Identity(
            background="Founder & Principal AI Systems Architect.",
            occupation="Systems Engineer",
        ),
        personality=Personality(
            traits=["analytical", "candid", "pragmatic"],
            values=["efficiency", "technical rigor"],
            communication_style="Direct, insight-dense",
        ),
        interests=Interests(
            primary=["Distributed Systems", "LLM Inference", "Backend Architecture"],
            secondary=["High-Performance Computing"],
            will_not_discuss=["speculative tokens"],
        ),
        writing_style=WritingStyle(
            tone="sharp, authoritative, actionable",
            typical_length="short",
            formatting=["no emojis", "no hashtags"],
            examples=["Most databases fail on write amplification, not memory leaks."],
        ),
        goals=Goals(
            short_term=["build authority in AI systems"],
            long_term=["industry leading voice"],
            content_pillars=["Systems Architecture", "Production Bottlenecks"],
        ),
        rules=Rules(
            always=["provide actionable value", "keep opening hook punchy"],
            never=["use hype keywords like 'game changer'", "use hashtags"],
        ),
    )


# ==============================================================================
# 1. Model Enums Tests
# ==============================================================================

def test_models_enums_support_poll() -> None:
    """Verifies that ActionType and ContentType include POLL enum members."""
    assert ActionType.POLL == "poll"
    assert ContentType.POLL == "poll"
    # ActionStatus should have COMPLETED / SUCCESS
    assert hasattr(ActionStatus, "COMPLETED")
    assert ActionStatus.COMPLETED == "completed"


# ==============================================================================
# 2. ContentGenerator.generate_tweet Hook Optimization Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_content_generator_generate_tweet_with_existing_draft(sample_persona: Persona) -> None:
    """Verifies generate_tweet passes draft_tweet through optimize_post_hook and applies winning hook."""
    mock_client = AsyncMock()
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.candidates = [
        HookCandidate(
            archetype="contrarian",
            hook_text="90% of microservices are just distributed monoliths in disguise.",
            score=9.6,
            reasoning="Challenging conventional microservices dogma.",
        ),
        HookCandidate(
            archetype="curiosity_gap",
            hook_text="Why your latency spikes every midnight.",
            score=8.1,
            reasoning="Creates curiosity on latency.",
        ),
    ]
    mock_client.beta.chat.completions.parse.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(parsed=mock_parsed_obj))]
    )

    generator = ContentGenerator(client=mock_client)
    draft = "Microservices architecture is often misunderstood.\n\nHere is how to properly decouple database locks and event queues across services."
    
    result = await generator.generate_tweet(
        persona=sample_persona,
        topic="Microservices architecture",
        draft_tweet=draft,
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.winning_hook.archetype == "contrarian"
    assert result.winning_hook.score == 9.6
    assert "90% of microservices are just distributed monoliths" in result.winning_hook.hook_text
    assert "90% of microservices are just distributed monoliths" in result.optimized_content
    assert "Here is how to properly decouple database locks" in result.optimized_content


@pytest.mark.asyncio
async def test_content_generator_generate_tweet_without_draft_generates_and_optimizes(sample_persona: Persona) -> None:
    """Verifies generate_tweet creates a draft tweet from LLM then runs hook optimization."""
    mock_client = AsyncMock()
    
    # 1. Draft generation response
    draft_response = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="Caching invalidation is the root cause of 80% stale data bugs in distributed setups."
                )
            )
        ]
    )
    
    # 2. Hook optimization parsed response
    mock_parsed_obj = MagicMock()
    mock_parsed_obj.candidates = [
        HookCandidate(
            archetype="framework_breakdown",
            hook_text="The 3-layer cache invalidation hierarchy that never serves stale reads.",
            score=9.4,
            reasoning="Actionable breakdown.",
        )
    ]
    
    mock_client.chat.completions.create.return_value = draft_response
    mock_client.beta.chat.completions.parse.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(parsed=mock_parsed_obj))]
    )

    generator = ContentGenerator(client=mock_client)
    result = await generator.generate_tweet(
        persona=sample_persona,
        topic="Cache invalidation",
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.winning_hook.archetype == "framework_breakdown"
    assert "The 3-layer cache invalidation hierarchy" in result.optimized_content


# ==============================================================================
# 3. ContentGenerator.generate_poll Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_content_generator_generate_poll(sample_persona: Persona) -> None:
    """Verifies ContentGenerator.generate_poll generates validated Native X polls."""
    mock_client = AsyncMock()
    expected_poll = GeneratedPoll(
        question="Which layer fails first during a 10x traffic surge?",
        options=["Database connection pool", "Redis cache memory", "API gateway routing", "Network bandwidth"],
        duration_days=2,
        context_hook="Scaling under pressure reveals real bottlenecks.",
        reasoning="Sparks architecture debates across backend engineers.",
    )
    
    mock_client.beta.chat.completions.parse.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(parsed=expected_poll))]
    )

    generator = ContentGenerator(client=mock_client)
    poll = await generator.generate_poll(
        persona=sample_persona,
        topic="High traffic scaling",
    )

    assert isinstance(poll, GeneratedPoll)
    assert poll.question == "Which layer fails first during a 10x traffic surge?"
    assert len(poll.options) == 4
    assert poll.options[0] == "Database connection pool"
    assert poll.duration_days == 2
    assert poll.context_hook == "Scaling under pressure reveals real bottlenecks."


# ==============================================================================
# 4. Tasks Session Async Poll Execution Tests (Mock Mode)
# ==============================================================================

@pytest.mark.asyncio
async def test_run_session_async_executes_poll_action_mock_mode(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Verifies that _run_session_async executes ActionType.POLL in mock mode and records DB Action and Content."""
    from xbot.ai.planner import PlannedAction, SessionPlan
    from xbot.tasks import _run_session_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@alexriver",
        display_name="Alex River",
        profile_slug="test_poll_mock_slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    planned_poll_action = PlannedAction(
        type="poll",  # ActionType.POLL
        target=None,
        content=json.dumps({
            "question": "Best approach for async job queues?",
            "options": ["Redis Celery", "Temporal", "SQS + Lambdas", "Kafka Consumers"],
            "duration_days": 1,
            "context_hook": "Queue architectures matter.",
            "reasoning": "Drives backend discussions.",
        }),
        reasoning="Engage community with queue architectures debate.",
        priority=1,
    )

    mock_plan = SessionPlan(
        mood="curious",
        reasoning="Run poll on queue systems",
        actions=[planned_poll_action],
        skip_reason=None,
    )

    mock_config = MagicMock()
    mock_config.mock_mode = True
    mock_config.proxy_url = None
    mock_config.schedule = MagicMock(timezone="UTC")

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_config", return_value=mock_config), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.plan_session", AsyncMock(return_value=mock_plan)), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.PostSessionProcessor.process_post_session", AsyncMock()):

        result = await _run_session_async(str(profile_id))

        assert result["status"] == "success"
        assert result["actions_completed"] == 1
        assert result["actions_failed"] == 0

        # Verify Action recorded in DB
        stmt_act = select(Action).where(
            Action.profile_id == profile_id,
            Action.action_type == ActionType.POLL,
        )
        res_act = await db_session.execute(stmt_act)
        actions = res_act.scalars().all()
        assert len(actions) == 1
        action = actions[0]
        assert action.status == ActionStatus.COMPLETED
        assert "Best approach for async job queues?" in action.content
        assert action.result is not None
        assert "poll" in action.result
        assert action.result["poll"]["options"] == ["Redis Celery", "Temporal", "SQS + Lambdas", "Kafka Consumers"]

        # Verify Content recorded in DB
        stmt_cnt = select(Content).where(
            Content.profile_id == profile_id,
            Content.content_type == ContentType.POLL,
        )
        res_cnt = await db_session.execute(stmt_cnt)
        contents = res_cnt.scalars().all()
        assert len(contents) == 1
        content_rec = contents[0]
        assert content_rec.status == ContentStatus.POSTED
        assert "Best approach for async job queues?" in content_rec.body


# ==============================================================================
# 5. Tasks Session Async Poll Execution Tests (Live Browser Mode)
# ==============================================================================

@pytest.mark.asyncio
async def test_run_session_async_executes_poll_action_live_mode(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Verifies that _run_session_async in live mode executes CreatePoll browser action."""
    from xbot.ai.planner import PlannedAction, SessionPlan
    from xbot.tasks import _run_session_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@alexriver",
        display_name="Alex River",
        profile_slug="test_poll_live_slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    planned_poll_action = PlannedAction(
        type="poll",
        target=None,
        content="Distributed consensus bottlenecks",  # Plain topic -> triggers generate_poll
        reasoning="Provoke debate on Paxos vs Raft.",
        priority=1,
    )

    mock_plan = SessionPlan(
        mood="analytical",
        reasoning="Execute distributed consensus poll",
        actions=[planned_poll_action],
        skip_reason=None,
    )

    mock_config = MagicMock()
    mock_config.mock_mode = False
    mock_config.proxy_url = None
    mock_config.schedule = MagicMock(timezone="UTC")

    mock_poll_gen_result = GeneratedPoll(
        question="Which consensus protocol causes the most operational pain in production?",
        options=["Raft", "Multi-Paxos", "Zab", "Two-Phase Commit"],
        duration_days=1,
        context_hook="Distributed consensus is deceptively hard.",
        reasoning="Forces architects to pick their battle.",
    )

    mock_browser_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser_context.new_page.return_value = mock_page

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_config", return_value=mock_config), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.plan_session", AsyncMock(return_value=mock_plan)), \
         patch("xbot.tasks.generate_poll", AsyncMock(return_value=mock_poll_gen_result)) as mock_gen_poll, \
         patch("xbot.tasks.CreatePoll.execute", AsyncMock(return_value=True)) as mock_create_poll, \
         patch("xbot.tasks.BrowseFeed.execute", AsyncMock(return_value=[])), \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock(return_value=mock_browser_context)), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.PostSessionProcessor.process_post_session", AsyncMock()):

        result = await _run_session_async(str(profile_id))

        assert result["status"] == "success"
        assert result["actions_completed"] == 1
        assert result["actions_failed"] == 0

        # Verify generate_poll was called with topic
        mock_gen_poll.assert_called_once()

        # Verify CreatePoll.execute was called with page and poll parameters
        mock_create_poll.assert_called_once()
        call_kwargs = mock_create_poll.call_args.kwargs
        assert "Which consensus protocol" in call_kwargs["question"]
        assert call_kwargs["options"] == ["Raft", "Multi-Paxos", "Zab", "Two-Phase Commit"]
        assert call_kwargs["duration_days"] == 1

        # Verify DB Action recorded
        stmt_act = select(Action).where(
            Action.profile_id == profile_id,
            Action.action_type == ActionType.POLL,
        )
        res_act = await db_session.execute(stmt_act)
        actions = res_act.scalars().all()
        assert len(actions) == 1
        assert actions[0].status == ActionStatus.COMPLETED
        assert actions[0].result["poll"]["options"] == ["Raft", "Multi-Paxos", "Zab", "Two-Phase Commit"]

        # Verify DB Content recorded
        stmt_cnt = select(Content).where(
            Content.profile_id == profile_id,
            Content.content_type == ContentType.POLL,
        )
        res_cnt = await db_session.execute(stmt_cnt)
        contents = res_cnt.scalars().all()
        assert len(contents) == 1
        assert contents[0].status == ContentStatus.POSTED


# ==============================================================================
# 6. Tasks Session Async Poll Failure Handling Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_run_session_async_handles_poll_failure(
    db_session: AsyncSession,
    sample_persona: Persona,
) -> None:
    """Verifies that _run_session_async records failure when CreatePoll returns False or throws."""
    from xbot.ai.planner import PlannedAction, SessionPlan
    from xbot.tasks import _run_session_async

    profile_id = uuid.uuid4()
    profile = Profile(
        id=profile_id,
        x_handle="@alexriver",
        display_name="Alex River",
        profile_slug="test_poll_fail_slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    planned_poll_action = PlannedAction(
        type="poll",
        target=None,
        content=json.dumps({
            "question": "Failing poll question?",
            "options": ["Opt A", "Opt B"],
            "duration_days": 1,
        }),
        reasoning="Test error path",
        priority=1,
    )

    mock_plan = SessionPlan(
        mood="neutral",
        reasoning="Testing poll failure",
        actions=[planned_poll_action],
        skip_reason=None,
    )

    mock_config = MagicMock()
    mock_config.mock_mode = False
    mock_config.proxy_url = None
    mock_config.schedule = MagicMock(timezone="UTC")

    mock_browser_context = AsyncMock()
    mock_page = AsyncMock()
    mock_browser_context.new_page.return_value = mock_page

    with patch("xbot.tasks.AsyncSessionLocal", return_value=db_session), \
         patch("xbot.tasks.load_config", return_value=mock_config), \
         patch("xbot.tasks.load_persona", return_value=sample_persona), \
         patch("xbot.tasks.plan_session", AsyncMock(return_value=mock_plan)), \
         patch("xbot.tasks.CreatePoll.execute", AsyncMock(return_value=False)), \
         patch("xbot.tasks.BrowseFeed.execute", AsyncMock(return_value=[])), \
         patch("xbot.tasks.BrowserManager.get_context", AsyncMock(return_value=mock_browser_context)), \
         patch("xbot.tasks.BrowserManager.acquire_lock", return_value=True), \
         patch("xbot.tasks.BrowserManager.release_lock", return_value=True), \
         patch("xbot.tasks.PostSessionProcessor.process_post_session", AsyncMock()):

        result = await _run_session_async(str(profile_id))

        assert result["status"] == "success"
        assert result["actions_completed"] == 0
        assert result["actions_failed"] == 1

        # Verify Action recorded as FAILED
        stmt_act = select(Action).where(
            Action.profile_id == profile_id,
            Action.action_type == ActionType.POLL,
        )
        res_act = await db_session.execute(stmt_act)
        actions = res_act.scalars().all()
        assert len(actions) == 1
        assert actions[0].status == ActionStatus.FAILED
        assert "Browser action script returned False" in actions[0].error
