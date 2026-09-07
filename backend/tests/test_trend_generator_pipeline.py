import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.ai.poll_generator import GeneratedPoll
from xbot.ai.visual_engine import VisualPostSpec
from xbot.ai.thread_generator import GeneratedThreadResponse
from xbot.schemas.thread import ThreadItemCreate
from xbot.models.content import Content, ContentStatus, ContentType, ThreadItem
from xbot.models.pipeline import ResearchedTopic
from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.trend_generator_pipeline import (
    determine_creation_format,
    generate_content_for_topic,
    run_trend_generator_for_profile,
)


def test_determine_creation_format_matrix():
    # 1. Visual candidates (memes, infographics, cheatsheets, comics, lifestyle)
    topic_meme = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        topic="Late night debugging meme on Friday",
        summary="A relatable comic about pushing to prod at 5pm.",
        scraped_posts=[],
    )
    assert determine_creation_format(topic_meme) == "visual"

    topic_infographic = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        topic="System design cheatsheet for distributed cache",
        summary="Technical diagram showing cache invalidation.",
        scraped_posts=[],
    )
    assert determine_creation_format(topic_infographic) == "visual"

    # 2. Thread candidate (deep research: >= 8 scraped posts and long topic)
    topic_thread = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        topic="Open Source LLM Performance Across 10 Benchmarks and Reasoning Parities",
        summary="Comprehensive breakdown of open weights models.",
        scraped_posts=[{"text": f"Post {i}", "author": f"user{i}"} for i in range(9)],
    )
    assert determine_creation_format(topic_thread) == "thread"

    # 3. Poll candidate (polarizing dilemmas, comparisons, choices)
    topic_poll_vs = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        topic="PostgreSQL vs MongoDB for high write workloads",
        summary="Debate on relational vs document stores.",
        scraped_posts=[{"text": "PG is better", "author": "dev1"}],
    )
    assert determine_creation_format(topic_poll_vs) == "poll"

    topic_poll_which = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        topic="Which caching layer do you prefer in 2026?",
        summary="Community preference debate.",
        scraped_posts=[],
    )
    assert determine_creation_format(topic_poll_which) == "poll"

    # 4. Standalone take candidate (fast news, sharp takes)
    topic_take = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        topic="New GPU architecture breakthrough announced",
        summary="Quick analysis on throughput gains.",
        scraped_posts=[{"text": "Exciting silicon news", "author": "tech"}],
    )
    assert determine_creation_format(topic_take) == "post"


@pytest.mark.asyncio
async def test_generate_content_for_topic_visual_meme():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    topic = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic="Late night debugging meme on Friday",
        summary="The 4 stages of realizing the bug is in production.",
        scraped_posts=[{"author": "dev", "text": "Why do we deploy on Friday?"}],
        media_paths=["/path/to/meme.png"],
        processed=False,
    )

    mock_guard = MagicMock()
    mock_spec = VisualPostSpec(
        tweet_copy="The exact moment you realize the bug is in production.",
        image_prompt="4-panel comic in 4:5 vertical portrait aspect ratio (1080x1350) showing panic escalation.",
        aspect_ratio="4:5",
        format_type="storyboard_4panel",
        target_simcluster="Tech/AI",
        one_two_punch_strategy="Tweet copy sets up tension; 4-panel comic delivers visual punchline.",
    )

    with patch("xbot.pipelines.trend_generator_pipeline.generate_visual_post_spec", AsyncMock(return_value=mock_spec)) as mock_vis_gen:
        res = await generate_content_for_topic(mock_db, profile, topic, mock_guard)

        assert res["status"] == "success"
        assert res["creation_format"] == "visual"
        assert topic.processed is True
        mock_vis_gen.assert_called_once()

        mock_db.add.assert_called_once()
        added_content: Content = mock_db.add.call_args[0][0]
        assert isinstance(added_content, Content)
        assert added_content.status == ContentStatus.APPROVED
        assert added_content.content_type in (ContentType.ORIGINAL, ContentType.POST, "original")
        assert len(added_content.body) < 140
        assert "exact moment you realize" in added_content.body
        assert added_content.ai_metadata["aspect_ratio"] == "4:5"
        assert added_content.ai_metadata["format_type"] == "storyboard_4panel"
        assert added_content.ai_metadata["visual_post_spec"]["format_type"] == "storyboard_4panel"
        assert added_content.ai_metadata["media_paths"] == ["/path/to/meme.png"]


@pytest.mark.asyncio
async def test_generate_content_for_topic_deep_dive_thread_with_media():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    topic = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic="Open Source LLM Performance Across 10 Benchmarks and Reasoning Parities",
        summary="Deep analysis on distilled reasoning architectures.",
        scraped_posts=[{"author": f"researcher_{i}", "text": f"Insight {i}"} for i in range(10)],
        media_paths=["/path/to/benchmark_chart.png", "/path/to/loss_curve.png"],
        processed=False,
    )

    mock_guard = MagicMock()

    mock_thread_resp = GeneratedThreadResponse(
        topic=topic.topic,
        hook_score=94,
        archetype="Framework",
        tweets=[
            "Open source models have crossed reasoning parity 🧵 1/4",
            "Here is the breakdown of inference latency • 2/4",
            "Cost per million tokens drops 10x • 3/4",
            "Key takeaway: distill before fine-tuning • 4/4",
        ],
        items=[
            ThreadItemCreate(position=0, item_type="hook", text="Open source models have crossed reasoning parity 🧵 1/4"),
            ThreadItemCreate(position=1, item_type="body", text="Here is the breakdown of inference latency • 2/4"),
            ThreadItemCreate(position=2, item_type="body", text="Cost per million tokens drops 10x • 3/4"),
            ThreadItemCreate(position=3, item_type="closer", text="Key takeaway: distill before fine-tuning • 4/4"),
        ],
    )

    with patch("xbot.pipelines.trend_generator_pipeline.generate_thread", AsyncMock(return_value=mock_thread_resp)) as mock_thread_gen:
        res = await generate_content_for_topic(mock_db, profile, topic, mock_guard)

        assert res["status"] == "success"
        assert res["creation_format"] == "thread"
        assert res["content_type"] == "thread"
        assert topic.processed is True
        mock_thread_gen.assert_called_once()

        # Check added objects: 1 Content + 4 ThreadItem records = 5 calls
        assert mock_db.add.call_count == 5
        added_content: Content = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_content, Content)
        assert added_content.content_type == ContentType.THREAD
        assert added_content.status == ContentStatus.APPROVED

        # Verify ThreadItem records
        thread_items = [call[0][0] for call in mock_db.add.call_args_list[1:]]
        assert len(thread_items) == 4
        assert thread_items[0].position == 0
        assert thread_items[0].item_type == "hook"
        assert thread_items[0].media_url == "/path/to/benchmark_chart.png"
        assert thread_items[1].item_type == "body"
        assert thread_items[1].media_url is None
        assert thread_items[3].item_type == "closer"


@pytest.mark.asyncio
async def test_generate_content_for_topic_interactive_poll():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    topic = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic="PostgreSQL vs MySQL: Which database handles high write concurrency better?",
        summary="Community debate on lock contention vs MVCC overhead.",
        scraped_posts=[{"author": "dba", "text": "Postgres MVCC has vacuum overhead."}],
        processed=False,
    )

    mock_guard = MagicMock()

    mock_poll = GeneratedPoll(
        question="Which database handles heavy write concurrency better in production?",
        options=["PostgreSQL MVCC", "MySQL InnoDB", "SQLite (WAL mode)", "CockroachDB"],
        duration_days=1,
        context_hook="Lock contention vs vacuum overhead.",
        reasoning="Sparks passionate database architecture debates.",
    )

    with patch("xbot.pipelines.trend_generator_pipeline.generate_poll", AsyncMock(return_value=mock_poll)) as mock_poll_gen:
        res = await generate_content_for_topic(mock_db, profile, topic, mock_guard)

        assert res["status"] == "success"
        assert res["creation_format"] == "poll"
        assert res["content_type"] == "poll"
        assert topic.processed is True
        mock_poll_gen.assert_called_once()

        mock_db.add.assert_called_once()
        added_content: Content = mock_db.add.call_args[0][0]
        assert isinstance(added_content, Content)
        assert added_content.content_type == ContentType.POLL
        assert added_content.status == ContentStatus.APPROVED
        assert "Which database handles heavy write concurrency" in added_content.body
        assert added_content.ai_metadata["poll_options"] == ["PostgreSQL MVCC", "MySQL InnoDB", "SQLite (WAL mode)", "CockroachDB"]
        assert added_content.ai_metadata["duration_days"] == 1
        assert added_content.ai_metadata["poll"]["question"] == mock_poll.question


@pytest.mark.asyncio
async def test_generate_content_for_topic_standalone_hot_take():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    topic = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic="Open Source LLM Performance",
        summary="Deep analysis on distilled reasoning architectures.",
        scraped_posts=[{"author": "researcher", "text": "Distillation changes inference economics."}],
        media_paths=["/path/to/chart.png"],
        processed=False,
    )

    mock_guard = MagicMock()

    mock_synth_result = MagicMock(
        content="Open source models have officially crossed the reasoning parity threshold.",
        post_type="post",
    )

    with patch("xbot.pipelines.trend_generator_pipeline.synthesize_creator_post", AsyncMock(return_value=mock_synth_result)) as mock_synth, \
         patch("xbot.pipelines.trend_generator_pipeline.optimize_post_for_virality") as mock_opt:
        mock_opt.return_value = MagicMock(
            full_optimized_text="Open source models have officially crossed the reasoning parity threshold.",
            extracted_link="https://arxiv.org/abs/2608.12345",
            open_loop_hook="Open source models just crossed the parity threshold.",
        )

        res = await generate_content_for_topic(mock_db, profile, topic, mock_guard)
        assert res["status"] == "success"
        assert res["creation_format"] == "post"
        assert topic.processed is True
        mock_synth.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        added_content: Content = mock_db.add.call_args[0][0]
        assert isinstance(added_content, Content)
        assert added_content.status == ContentStatus.APPROVED
        assert added_content.content_type in (ContentType.ORIGINAL, ContentType.POST, "original")
        assert "Open source models" in added_content.body
        assert added_content.ai_metadata["extracted_link"] == "https://arxiv.org/abs/2608.12345"
        assert "https://arxiv.org/abs/2608.12345" in added_content.ai_metadata["first_reply_text"]


@pytest.mark.asyncio
async def test_run_trend_generator_for_profile_processes_pending():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        status=ProfileStatus.ACTIVE,
    )

    topic1 = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic="AI Dev Tools",
        processed=False,
    )
    topic2 = ResearchedTopic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        topic="Cloud Native DBs",
        processed=False,
    )

    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [topic1, topic2]))
    mock_guard = MagicMock()

    with patch("xbot.pipelines.trend_generator_pipeline.generate_content_for_topic") as mock_gen_topic:
        mock_gen_topic.side_effect = [
            {"status": "success", "content_id": str(uuid.uuid4()), "topic": "AI Dev Tools"},
            {"status": "success", "content_id": str(uuid.uuid4()), "topic": "Cloud Native DBs"},
        ]

        res = await run_trend_generator_for_profile(mock_db, profile, mock_guard, max_items=2)
        assert res["status"] == "success"
        assert res["items_generated"] == 2
        assert len(res["details"]) == 2
        assert mock_gen_topic.call_count == 2
