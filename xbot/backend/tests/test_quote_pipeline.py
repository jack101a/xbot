import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.quote_pipeline import run_quote_pipeline_for_profile


@pytest.mark.asyncio
async def test_run_quote_pipeline_for_profile():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        display_name="Test Creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)
    mock_guard.is_target_acted_upon = MagicMock(return_value=False)
    mock_guard.record_action = AsyncMock()

    with patch("xbot.pipelines.quote_pipeline.enqueue_browser_job", return_value="job-q-1"):
        with patch("xbot.pipelines.quote_pipeline.get_browser_job_result") as mock_res:
            mock_res.side_effect = [
                {
                    "status": "success",
                    "tweets": [
                        {
                            "id": "viral-1",
                            "text": "Why AI agents will replace traditional SaaS in 24 months.",
                            "author": "tech_founder",
                            "views": "75K",
                        },
                    ],
                },
                {"status": "quoted"},
            ]

            with patch("xbot.ai.sniper.generate_sniper_reply", new_callable=AsyncMock) as mock_sniper:
                mock_sniper_res = MagicMock()
                mock_sniper_res.reply_text = "Distribution beats models every single time."
                mock_sniper.return_value = mock_sniper_res

                res = await run_quote_pipeline_for_profile(mock_db, profile, mock_guard, max_quotes=1)
                assert res["status"] == "success"
                assert res["quotes_executed"] == 1
                mock_guard.record_action.assert_called_once()
