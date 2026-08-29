import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.ai.sniper import SniperResult
from xbot.models.profile import Profile, ProfileStatus
from xbot.models.realgraph import ConversationThread
from xbot.pipelines.reply_pipeline import (
    execute_fast_response_replies,
    execute_feed_replies,
    execute_kol_sniper_replies,
    run_reply_pipeline_for_profile,
)


@pytest.mark.asyncio
async def test_execute_kol_sniper_replies_enriched_context():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
        config={"target_kols": ["@elonmusk"]},
    )

    mock_guard = MagicMock()
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = AsyncMock()

    captured_jobs = []

    def mock_enqueue_job(job):
        captured_jobs.append(job)
        return f"job-{len(captured_jobs)}"

    with patch("xbot.pipelines.reply_pipeline.enqueue_browser_job", side_effect=mock_enqueue_job):
        with patch("xbot.pipelines.reply_pipeline.get_browser_job_result") as mock_res:
            mock_res.side_effect = [
                {
                    "found_fresh_tweet": True,
                    "tweet_data": {
                        "id": "tweet-kol-1",
                        "text": "Starship launch scheduled for tomorrow with new Raptor 3 engines.",
                        "author": "elonmusk",
                        "url": "https://x.com/elonmusk/status/tweet-kol-1",
                        "views": 250000,
                        "likes": 12000,
                        "replies": 3500,
                        "retweets": 1800,
                        "top_comments": [
                            {"author": "space_enthusiast", "text": "Raptor 3 plumbing is insane", "likes": 420},
                            {"author": "rocket_fan", "text": "Will it attempt a booster catch?", "likes": 180},
                        ],
                        "media_alts": ["Raptor 3 engine test firing with green flame"],
                        "media_urls": ["https://pbs.twimg.com/media/raptor3.jpg"],
                    },
                },
                {"status": "replied"},
            ]

            with patch("xbot.pipelines.reply_pipeline.generate_sniper_reply") as mock_sniper:
                mock_sniper.return_value = SniperResult(
                    response_mode="in_depth_breakdown",
                    reply_text="Raptor 3 removing external heat shields is the real step change for rapid reuse.",
                    gif_query=None,
                    angle="data",
                    confidence=0.95,
                    reasoning="Technical analysis matching the comments.",
                )

                count = await execute_kol_sniper_replies(mock_db, profile, mock_guard, max_replies=1)
                assert count == 1
                mock_guard.record_action.assert_called_once_with(
                    mock_db, "test_slug", "reply", target_id="tweet-kol-1"
                )

                # Verify enriched context was passed to generate_sniper_reply
                mock_sniper.assert_called_once()
                call_kwargs = mock_sniper.call_args.kwargs
                target_tweet = call_kwargs.get("target_tweet", {})
                assert target_tweet.get("id") == "tweet-kol-1"
                assert target_tweet.get("author") == "elonmusk"
                assert len(target_tweet.get("top_comments", [])) == 2
                assert target_tweet.get("top_comments")[0]["likes"] == 420
                assert target_tweet.get("media_alts") == ["Raptor 3 engine test firing with green flame"]
                assert target_tweet.get("views") == 250000

                # Verify BrowserJob params
                assert len(captured_jobs) == 3
                reply_job = captured_jobs[1]
                assert reply_job.action_type == "reply"
                assert reply_job.params.get("tweet_id") == "tweet-kol-1"
                assert reply_job.params.get("tweet_url") == "https://x.com/elonmusk/status/tweet-kol-1"
                assert "Raptor 3" in reply_job.params.get("text")
                assert reply_job.params.get("gif_query") is None

                # Verify auto-like job
                like_job = captured_jobs[2]
                assert like_job.action_type == "like"
                assert like_job.params.get("tweet_url") == "https://x.com/elonmusk/status/tweet-kol-1"


@pytest.mark.asyncio
async def test_execute_kol_sniper_replies_pure_gif_and_short_reactions():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
        config={"target_kols": ["@sama"]},
    )

    mock_guard = MagicMock()
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = AsyncMock()

    captured_jobs = []

    def mock_enqueue_job(job):
        captured_jobs.append(job)
        return f"job-{len(captured_jobs)}"

    with patch("xbot.pipelines.reply_pipeline.enqueue_browser_job", side_effect=mock_enqueue_job):
        with patch("xbot.pipelines.reply_pipeline.get_browser_job_result") as mock_res:
            mock_res.side_effect = [
                {
                    "found_fresh_tweet": True,
                    "tweet_data": {
                        "id": "tweet-sama-1",
                        "text": "AGI in 2026.",
                        "author": "sama",
                        "url": "https://x.com/sama/status/tweet-sama-1",
                        "views": 500000,
                        "likes": 25000,
                    },
                },
                {"status": "replied"},
            ]

            with patch("xbot.pipelines.reply_pipeline.generate_sniper_reply") as mock_sniper:
                mock_sniper.return_value = SniperResult(
                    response_mode="pure_gif",
                    reply_text="real",
                    gif_query="popcorn eating",
                    angle="witty",
                    confidence=0.9,
                    reasoning="Meme reaction fits the hype.",
                )

                count = await execute_kol_sniper_replies(mock_db, profile, mock_guard, max_replies=1)
                assert count == 1
                mock_guard.record_action.assert_called_once()

                assert len(captured_jobs) == 3
                reply_job = captured_jobs[1]
                assert reply_job.action_type == "reply"
                assert reply_job.params.get("text") == "real"
                assert reply_job.params.get("gif_query") == "popcorn eating"
                like_job = captured_jobs[2]
                assert like_job.action_type == "like"
                assert like_job.params.get("tweet_url") == "https://x.com/sama/status/tweet-sama-1"


@pytest.mark.asyncio
async def test_execute_fast_response_replies_with_persona_and_gif():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    thread = ConversationThread(
        id=uuid.uuid4(),
        profile_id=profile.id,
        root_tweet_id="root-100",
        parent_tweet_id="parent-101",
        target_handle="tech_lead",
        turn_count=1,
        max_turns=3,
        status="active",
        last_action_at=datetime.datetime.utcnow(),
        conversation_history=[
            {"author": "test_creator", "text": "What stack are you using for edge compute?"},
            {"author": "tech_lead", "text": "Cloudflare Workers + Rust for cold start < 5ms."},
        ],
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [thread]
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_guard = MagicMock()
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = AsyncMock()

    captured_jobs = []

    def mock_enqueue_job(job):
        captured_jobs.append(job)
        return f"job-{len(captured_jobs)}"

    with patch("xbot.pipelines.reply_pipeline.enqueue_browser_job", side_effect=mock_enqueue_job):
        with patch("xbot.pipelines.reply_pipeline.get_browser_job_result") as mock_res:
            mock_res.return_value = {"status": "replied"}

            with patch("xbot.pipelines.reply_pipeline._get_persona_for_profile") as mock_get_persona:
                mock_get_persona.return_value = MagicMock()
                with patch("xbot.pipelines.reply_pipeline.generate_sniper_reply") as mock_sniper:
                    mock_sniper.return_value = SniperResult(
                        response_mode="punchy_one_liner",
                        reply_text="Rust cold starts on V8 isolates are unmatched.",
                        gif_query=None,
                        angle="insight",
                        confidence=0.92,
                    )

                    count = await execute_fast_response_replies(mock_db, profile, mock_guard, max_replies=1)
                    assert count == 1
                    assert thread.turn_count == 2
                    mock_guard.record_action.assert_called_once()

                    assert len(captured_jobs) == 2
                    reply_job = captured_jobs[0]
                    assert reply_job.action_type == "reply"
                    assert reply_job.priority == 1
                    assert "Rust cold starts" in reply_job.params.get("text")
                    like_job = captured_jobs[1]
                    assert like_job.action_type == "like"
                    assert like_job.params.get("tweet_url") == "https://x.com/tech_lead/status/parent-101"


@pytest.mark.asyncio
async def test_execute_feed_replies_enriched_context_and_gif():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = AsyncMock()

    captured_jobs = []

    def mock_enqueue_job(job):
        captured_jobs.append(job)
        return f"job-{len(captured_jobs)}"

    with patch("xbot.pipelines.reply_pipeline.enqueue_browser_job", side_effect=mock_enqueue_job):
        with patch("xbot.pipelines.reply_pipeline.get_browser_job_result") as mock_res:
            mock_res.side_effect = [
                {
                    "status": "success",
                    "tweets": [
                        {
                            "id": "feed-tweet-1",
                            "text": "The M4 Max efficiency gap is unbelievable.",
                            "author": "tech_reviewer",
                            "url": "https://x.com/tech_reviewer/status/feed-tweet-1",
                            "views": 85000,
                            "likes": 3200,
                            "top_comments": [
                                {"author": "fan1", "text": "Battery life is 18h+", "likes": 95}
                            ],
                            "media_alts": ["Geekbench performance graph"],
                        }
                    ],
                },
                {"status": "replied"},
            ]

            with patch("xbot.pipelines.reply_pipeline.generate_sniper_reply") as mock_sniper:
                mock_sniper.return_value = SniperResult(
                    response_mode="pure_gif",
                    reply_text="💀",
                    gif_query="side eye",
                    angle="witty",
                    confidence=0.88,
                )

                count = await execute_feed_replies(mock_db, profile, mock_guard, max_replies=1)
                assert count == 1
                mock_guard.record_action.assert_called_once_with(
                    mock_db, "test_slug", "reply", target_id="feed-tweet-1"
                )

                # Verify context passed to sniper
                mock_sniper.assert_called_once()
                target_tweet = mock_sniper.call_args.kwargs.get("target_tweet", {})
                assert target_tweet.get("id") == "feed-tweet-1"
                assert target_tweet.get("views") == 85000
                assert len(target_tweet.get("top_comments", [])) == 1
                assert target_tweet.get("media_alts") == ["Geekbench performance graph"]

                # Verify reply job params
                reply_job = captured_jobs[1]
                assert reply_job.action_type == "reply"
                assert reply_job.priority == 2
                assert reply_job.params.get("text") == "💀"
                assert reply_job.params.get("gif_query") == "side eye"


@pytest.mark.asyncio
async def test_run_reply_pipeline_for_profile_skipped():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=False)

    res = await run_reply_pipeline_for_profile(mock_db, profile, mock_guard)
    assert res["status"] == "skipped"
    assert res["replies_executed"] == 0


@pytest.mark.asyncio
async def test_run_reply_pipeline_for_profile_success():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)

    with patch("xbot.pipelines.reply_pipeline.execute_kol_sniper_replies", AsyncMock(return_value=1)) as mock_kol:
        with patch("xbot.pipelines.reply_pipeline.execute_fast_response_replies", AsyncMock(return_value=1)) as mock_fast:
            with patch("xbot.pipelines.reply_pipeline.execute_feed_replies", AsyncMock(return_value=1)) as mock_feed:
                res = await run_reply_pipeline_for_profile(mock_db, profile, mock_guard, max_total_replies=3)
                assert res["status"] == "success"
                assert res["replies_executed"] == 3
                assert res["sniper_replies"] == 1
                assert res["sentinel_replies"] == 1
                assert res["feed_replies"] == 1
                mock_kol.assert_called_once_with(mock_db, profile, mock_guard, max_replies=2)
                mock_fast.assert_called_once_with(mock_db, profile, mock_guard, max_replies=2)
                mock_feed.assert_called_once_with(mock_db, profile, mock_guard, max_replies=1)


