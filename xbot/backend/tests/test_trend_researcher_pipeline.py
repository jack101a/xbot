import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.trend_researcher_pipeline import (
    discover_candidate_trends,
    run_trend_researcher_for_profile,
)


@pytest.mark.asyncio
async def test_discover_candidate_trends():
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )
    mock_redis = MagicMock()

    with patch("xbot.pipelines.trend_researcher_pipeline.enqueue_browser_job", return_value="job-t-1"):
        with patch("xbot.pipelines.trend_researcher_pipeline.get_browser_job_result") as mock_res:
            mock_res.side_effect = [
                # Trending tab results
                {
                    "status": "success",
                    "trends": [{"name": "#OpenAI", "category": "Technology"}],
                },
                # Feed viral tweets
                {
                    "status": "success",
                    "tweets": [{"text": "DeepSeek just dropped a breakthrough research paper on distillation.", "views": 100000}],
                },
            ]

            with patch("xbot.pipelines.trend_researcher_pipeline.fetch_rss_trends", AsyncMock(return_value=[])):
                candidates = await discover_candidate_trends(profile, mock_redis)
                assert len(candidates) >= 2
                topics = [c["topic"] for c in candidates]
                assert any("#OpenAI" in t for t in topics)


@pytest.mark.asyncio
async def test_run_trend_researcher_for_profile_success():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    profile = Profile(

        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)
    mock_guard.r = MagicMock()
    mock_guard.r.exists.return_value = 0

    with patch("xbot.pipelines.trend_researcher_pipeline.discover_candidate_trends") as mock_disc:
        mock_disc.return_value = [{"topic": "AI Hardware Advances", "source": "x_trending"}]

        with patch("xbot.pipelines.trend_researcher_pipeline.research_topic_comprehensively") as mock_research:
            mock_report = MagicMock()
            mock_report.viral_posts = [MagicMock(tweet_id="1", author="a", text="t", likes=1, retweets=1, replies=1, views=1, media_urls=[])]
            mock_report.downloaded_media = []
            mock_report.synthesis_summary = "Summary"
            mock_research.return_value = mock_report

            res = await run_trend_researcher_for_profile(mock_db, profile, mock_guard, max_topics_to_research=1)
            assert res["status"] == "success"
            assert res["topics_researched"] == 1
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
