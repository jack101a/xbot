from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.persona.models import KOLChannel, TargetKOL, Persona, Identity, Personality, Interests, WritingStyle, Goals, Rules
from xbot.pipelines.reply_pipeline.kol_sniper import execute_kol_sniper_replies


@pytest.fixture
def sample_categorized_persona():
    return Persona(
        id="test_profile",
        display_name="Kaya",
        x_handle="@test_profile",
        identity=Identity(background="Tech and culture creator"),
        personality=Personality(communication_style="Witty and sharp"),
        interests=Interests(primary=["Tech", "Anime", "Cinema"]),
        writing_style=WritingStyle(tone="Conversational", typical_length="Short"),
        goals=Goals(),
        rules=Rules(),
        kol_channels=[
            KOLChannel(name="anime_manga", display_title="Anime & Manga", is_active=True, preferred_angle="insight"),
            KOLChannel(name="movies_cinema", display_title="Cinema", is_active=False, preferred_angle="contrarian"),
            KOLChannel(name="consumer_tech", display_title="Tech", is_active=True, preferred_angle="witty"),
        ],
        target_kols=[
            TargetKOL(handle="pewpiece", category="anime_manga", is_active=True, preferred_angle="insight"),
            TargetKOL(handle="DiscussingFilm", category="movies_cinema", is_active=True, preferred_angle="contrarian"),
            TargetKOL(handle="MKBHD", category="consumer_tech", is_active=True, preferred_angle="witty"),
        ]
    )


@pytest.mark.asyncio
async def test_kol_sniper_respects_active_channels(sample_categorized_persona):
    mock_db = AsyncMock()
    mock_profile = MagicMock()
    mock_profile.profile_slug = "test_profile"
    mock_profile.config = {}

    mock_guard = MagicMock()
    mock_guard.is_target_acted_upon.return_value = False
    mock_guard.record_action = AsyncMock()

    res_data = {
        "found_fresh_tweet": True,
        "tweet_data": {"id": "123456", "text": "New anime release announcement", "author": "pewpiece", "url": "https://x.com/pewpiece/status/123456"},
        "status": "success"
    }

    with patch("xbot.pipelines.reply_pipeline.kol_sniper.load_config", return_value=sample_categorized_persona), \
         patch("xbot.pipelines.reply_pipeline.kol_sniper._get_persona_for_profile", return_value=sample_categorized_persona), \
         patch("xbot.pipelines.reply_pipeline.kol_sniper.enqueue_browser_job", return_value="job_123"), \
         patch("xbot.pipelines.reply_pipeline.kol_sniper.get_browser_job_result", return_value=res_data), \
         patch("xbot.pipelines.reply_pipeline.kol_sniper._get_pkg") as mock_pkg:

        mock_pkg_mod = MagicMock()
        mock_pkg_mod.enqueue_browser_job = MagicMock(return_value="job_123")
        mock_pkg_mod.get_browser_job_result = MagicMock(return_value=res_data)
        mock_pkg_mod.score_tweet_opportunity.return_value = MagicMock(recommended_action="reply", score=85.0)
        mock_pkg_mod.generate_sniper_reply = AsyncMock(return_value=MagicMock(reply_text="Clean take", gif_query=None, response_mode="text"))
        mock_pkg_mod.format_content.return_value = "Clean take"
        mock_pkg_mod.strip_surrounding_quotes.return_value = "Clean take"
        mock_pkg.return_value = mock_pkg_mod

        count = await execute_kol_sniper_replies(mock_db, mock_profile, mock_guard, max_replies=1)
        assert count == 1
