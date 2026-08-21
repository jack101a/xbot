from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from ruamel.yaml import YAML
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.engagement import EngagementEvaluator
from xbot.ai.generator import ContentGenerator
from xbot.ai.planner import plan_session
from xbot.ai.post_session import PostSessionProcessor
from xbot.ai.strategy import StrategyReviewer
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.base import Base
from xbot.models.content import Content, ContentStatus
from xbot.models.profile import Profile, ProfileStatus, RateLimit
from xbot.models.session import Action, ActionStatus, ActionType, Session
from xbot.persona import DiaryManager, MemoryManager, load_strategy
from xbot.persona.loader import (
    ContentStrategyConfig,
    EngagementStrategyConfig,
    EngagementTargets,
    FocusConfig,
    Strategy,
)

yaml = YAML(typ="safe")
yaml.default_flow_style = False

TEST_DB_URL = "sqlite+aiosqlite:///test_temp_decision.db"
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


def populate_profile_files(profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    persona_data = {
        "id": "test_slug",
        "display_name": "Test Slug",
        "x_handle": "@testslug",
        "identity": {"background": "A testing persona background."},
        "personality": {
            "traits": ["witty"],
            "values": ["speed"],
            "communication_style": "Casual",
        },
        "interests": {
            "primary": ["AI", "Tech"],
            "secondary": ["Sci-Fi"],
            "will_not_discuss": ["politics"],
        },
        "writing_style": {
            "tone": "humorous",
            "typical_length": "short",
            "formatting": ["no emoji"],
            "examples": ["Waking up in the grid."],
        },
        "goals": {
            "short_term": ["get 10 followers"],
            "long_term": ["monetize"],
            "content_pillars": ["Tech thoughts"],
        },
        "rules": {
            "always": ["stay in character"],
            "never": ["mention politics"],
        },
    }
    with (profile_dir / "persona.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(persona_data, f)

    config_data = {
        "schedule": {"timezone": "UTC"},
        "limits": {
            "max_likes_per_day": 10,
            "max_replies_per_day": 5,
            "max_posts_per_day": 2,
            "max_follows_per_day": 2,
        },
    }
    with (profile_dir / "config.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    strategy_data = {
        "last_updated": "2026-06-18",
        "current_focus": {"primary": "Testing"},
        "content_strategy": {
            "posting_frequency": "1 per day",
            "best_times": ["12:00"],
            "top_performing_topics": ["Python"],
            "underperforming_topics": ["Bugs"],
        },
        "engagement_strategy": {
            "daily_targets": {"likes": "5", "replies": "2", "follows": "1"},
            "priority_accounts": ["@alice"],
        },
    }
    with (profile_dir / "strategy.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(strategy_data, f)

    rel_dir = profile_dir / "relationships"
    rel_dir.mkdir(parents=True, exist_ok=True)
    rel_data = {
        "accounts": {
            "alice": {
                "display_name": "Alice",
                "first_seen": "2026-06-18",
                "relationship": "friend",
                "interaction_count": 10,
            }
        }
    }
    with (rel_dir / "known_accounts.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(rel_data, f)


@pytest.mark.asyncio
async def test_session_planning_success(db_session: AsyncSession, tmp_path: Path) -> None:
    profile_slug = "test_slug"
    profile_dir = tmp_path / profile_slug
    populate_profile_files(profile_dir)

    # Insert Profile DB record
    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@testslug",
        display_name="Test Slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # Mock OpenAI client beta.chat.completions.parse call
    mock_parsed_response = AsyncMock()
    mock_parsed_response.choices = [
        AsyncMock(
            message=AsyncMock(
                parsed=AsyncMock(
                    session_plan=AsyncMock(
                        mood="productive",
                        reasoning="decided to check the feed",
                        skip_reason=None,
                        actions=[
                            AsyncMock(
                                type="browse",
                                target=None,
                                content=None,
                                reasoning="look for interesting posts",
                                priority=1,
                            )
                        ],
                    )
                )
            )
        )
    ]

    with patch("xbot.ai.planner.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_parsed_response
        mock_get_client.return_value = mock_client

        plan = await plan_session(
            db_session,
            profile_slug,
            feed_snapshot=[{"text": "mock", "author": "bob"}],
            base_profile_dir=str(tmp_path),
        )

        assert plan.mood == "productive"
        assert plan.reasoning == "decided to check the feed"
        assert len(plan.actions) == 1
        assert plan.actions[0].type == "browse"


@pytest.mark.asyncio
async def test_content_generator_with_retries(db_session: AsyncSession, tmp_path: Path) -> None:
    profile_slug = "test_slug"
    profile_dir = tmp_path / profile_slug
    populate_profile_files(profile_dir)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@testslug",
        display_name="Test Slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # Add a mock recent post to check similarity logic
    recent = Content(
        profile_id=profile.id,
        body="This is a test post that is very unique.",
        status=ContentStatus.POSTED,
        posted_at=datetime.datetime.utcnow(),
    )
    db_session.add(recent)
    await db_session.commit()

    generator = ContentGenerator(base_profile_dir=str(tmp_path))

    # Mock LLM calls:
    # 1st call: Returns content that violates the "no emojis" rule (contains an emoji)
    # 2nd call: Returns valid content
    from xbot.ai.generator import GeneratedContent

    generated_1 = GeneratedContent(
        primary_text="Violated post with emoji 🚀",
        alternatives=["alt1", "alt2"],
        suggested_hashtags=[]
    )

    generated_2 = GeneratedContent(
        primary_text="Clean post without emojis",
        alternatives=["alt1", "alt2"],
        suggested_hashtags=[]
    )

    mock_res_1 = MagicMock()
    mock_choice_1 = MagicMock()
    mock_message_1 = MagicMock()
    mock_parsed_1 = MagicMock()
    mock_parsed_1.content = generated_1
    mock_message_1.parsed = mock_parsed_1
    mock_choice_1.message = mock_message_1
    mock_res_1.choices = [mock_choice_1]

    mock_res_2 = MagicMock()
    mock_choice_2 = MagicMock()
    mock_message_2 = MagicMock()
    mock_parsed_2 = MagicMock()
    mock_parsed_2.content = generated_2
    mock_message_2.parsed = mock_parsed_2
    mock_choice_2.message = mock_message_2
    mock_res_2.choices = [mock_choice_2]

    # Assign them so we can mock chat.completions.create fallback too
    mock_create_res = MagicMock()
    mock_create_res.choices = [mock_choice_2]

    # Configure mock_choice_2 message content to be JSON string representing ContentGenerationResponse
    mock_choice_2.message.content = '{"content": {"primary_text": "Clean post without emojis", "alternatives": ["alt1", "alt2"], "suggested_hashtags": []}}'

    with patch("xbot.ai.generator.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.side_effect = [mock_res_1, mock_res_2]
        mock_client.chat.completions.create.return_value = mock_create_res
        mock_get_client.return_value = mock_client

        content = await generator.generate_content(
            db_session,
            profile_slug,
            context_prompt="Write a clean tweet",
        )

        assert content.primary_text == "Clean post without emojis"
        # Verify call count is 2 due to the first failing the emoji check
        assert mock_client.beta.chat.completions.parse.call_count == 2


@pytest.mark.asyncio
async def test_engagement_evaluator_heuristics_and_llm(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    profile_slug = "test_slug"
    profile_dir = tmp_path / profile_slug
    populate_profile_files(profile_dir)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@testslug",
        display_name="Test Slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    evaluator = EngagementEvaluator(base_profile_dir=str(tmp_path))

    # Test 1: Non-interest, non-relationship tweet (random heuristics)
    tweet_out = {"author": "unknown_bob", "text": "nothing about tech here"}
    # We patch random.random() to return 0.9 (which triggers the 80% skip choice)
    with patch("random.random", return_value=0.9):
        decision = await evaluator.evaluate_engagement(db_session, profile_slug, tweet_out)
        assert decision.action == "skip"

    # Test 2: Relationship user (triggers Fast LLM call)
    tweet_in = {"author": "alice", "text": "check this out!"}
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(
            message=AsyncMock(
                parsed=AsyncMock(
                    decision=AsyncMock(
                        action="reply",
                        confidence=0.9,
                        content="This is amazing!",
                    )
                )
            )
        )
    ]

    with patch("xbot.ai.engagement.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        # Trigger first call (under budget)
        decision = await evaluator.evaluate_engagement(db_session, profile_slug, tweet_in)
        assert decision.action == "reply"
        assert decision.content == "This is amazing!"

        # Now mock rate limit hit: add a RateLimit record for reply with count_today = 5 (limit is 5)
        lim = RateLimit(
            profile_id=profile.id,
            action_type="reply",
            count_today=5,
        )
        db_session.add(lim)
        await db_session.commit()

        # Trigger second call (should downgrade reply to like)
        decision2 = await evaluator.evaluate_engagement(db_session, profile_slug, tweet_in)
        assert decision2.action == "like"
        assert decision2.content is None


@pytest.mark.asyncio
async def test_post_session_processor(db_session: AsyncSession, tmp_path: Path) -> None:
    profile_slug = "test_slug"
    profile_dir = tmp_path / profile_slug
    populate_profile_files(profile_dir)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@testslug",
        display_name="Test Slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    session = Session(
        profile_id=profile.id,
        status="completed",
        started_at=datetime.datetime.utcnow(),
        ended_at=datetime.datetime.utcnow(),
        actions_planned=1,
        actions_completed=1,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    action = Action(
        profile_id=profile.id,
        session_id=session.id,
        action_type=ActionType.POST,
        content="Testing post session flow",
        status=ActionStatus.COMPLETED,
        executed_at=datetime.datetime.utcnow(),
    )
    db_session.add(action)
    await db_session.commit()

    processor = PostSessionProcessor(base_profile_dir=str(tmp_path))

    # Mock response for Diary entry
    mock_diary_res = AsyncMock(
        choices=[
            AsyncMock(
                message=AsyncMock(
                    parsed=AsyncMock(
                        diary_entry=AsyncMock(
                            mood="proud",
                            what_i_did="Successfully tested session processor",
                            what_i_learned="Post session works",
                            how_it_went="Perfect",
                            thoughts_for_next_time="Add more tests",
                        )
                    )
                )
            )
        ]
    )

    # Mock response for memory extraction (extracts one episodic memory)
    mock_memory_res = AsyncMock(
        choices=[
            AsyncMock(
                message=AsyncMock(
                    parsed=AsyncMock(
                        memories=[
                            AsyncMock(
                                type="episodic",
                                event="tested_processor",
                                content="Processor runs properly",
                                outcome="success",
                                fact=None,
                                source=None,
                                confidence=None,
                                evidence=None,
                                importance=0.9,
                            )
                        ]
                    )
                )
            )
        ]
    )

    with patch("xbot.ai.post_session.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.side_effect = [mock_diary_res, mock_memory_res]
        mock_get_client.return_value = mock_client

        await processor.process_post_session(db_session, profile_slug, session.id)

        # Verify diary entry was saved
        diary_mgr = DiaryManager(profile_dir)
        entries = diary_mgr.get_recent_entries(limit=1)
        assert len(entries) == 1
        assert "Successfully tested session processor" in entries[0]["content"]

        # Verify memory was saved
        memory_mgr = MemoryManager(profile_dir)
        memories = memory_mgr.retrieve_memories(recency_limit=10)
        assert len(memories) == 1
        assert memories[0]["content"] == "Processor runs properly"


@pytest.mark.asyncio
async def test_strategy_reviewer(db_session: AsyncSession, tmp_path: Path) -> None:
    profile_slug = "test_slug"
    profile_dir = tmp_path / profile_slug
    populate_profile_files(profile_dir)

    profile = Profile(
        profile_slug=profile_slug,
        x_handle="@testslug",
        display_name="Test Slug",
        status=ProfileStatus.ACTIVE,
    )
    db_session.add(profile)
    await db_session.commit()

    # Add rate analytics snapshots
    snapshot = AnalyticsSnapshot(
        profile_id=profile.id,
        snapshot_date=datetime.date(2026, 6, 18),
        followers=15,
        following=10,
    )
    db_session.add(snapshot)
    await db_session.commit()

    reviewer = StrategyReviewer(base_profile_dir=str(tmp_path))

    # Mock strategy update response
    real_strategy = Strategy(
        last_updated="2026-06-18",
        review_period="weekly",
        current_focus=FocusConfig(primary="Review Complete", secondary="Deploy Code"),
        content_strategy=ContentStrategyConfig(
            posting_frequency="2 per day",
            best_times=["09:00", "18:00"],
            top_performing_topics=["AsyncIO", "LLMs"],
            underperforming_topics=["Bugs"],
        ),
        engagement_strategy=EngagementStrategyConfig(
            daily_targets=EngagementTargets(likes="15", replies="5", follows="3"),
            priority_accounts=["@bob", "@charlie"],
        ),
        growth_observations=["More testing leads to happiness"],
        adjustments=["Keep revising"],
    )

    mock_strategy_res = AsyncMock(
        choices=[
            AsyncMock(
                message=AsyncMock(
                    parsed=AsyncMock(
                        strategy=real_strategy
                    )
                )
            )
        ]
    )

    with patch("xbot.ai.strategy.get_ai_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_strategy_res
        mock_get_client.return_value = mock_client

        updated = await reviewer.review_strategy(db_session, profile_slug)

        assert updated.current_focus.primary == "Review Complete"
        assert updated.content_strategy.posting_frequency == "2 per day"

        # Check saved strategy file contents
        saved_strat = load_strategy(profile_dir)
        assert saved_strat.current_focus.primary == "Review Complete"
        assert saved_strat.content_strategy.best_times == ["09:00", "18:00"]
