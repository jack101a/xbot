from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from xbot.ai.x_researcher import (
    DownloadedMedia,
    TopicResearchReport,
    ViralTweet,
    _parse_engagement_number,
    generate_search_phrases,
    research_topic_comprehensively,
)
from xbot.persona.loader import Persona, Identity, Personality, Interests, WritingStyle, Goals, Rules


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="pop_culture_creator",
        display_name="Kaya",
        x_handle="@kayatwt",
        identity=Identity(
            background="Delhi University culture commentator.",
            occupation="Creator",
        ),
        personality=Personality(
            traits=["witty", "sharp", "conversational"],
            values=["authenticity", "creativity"],
            communication_style="Sharp, culturally plugged-in sarcasm",
        ),
        interests=Interests(
            primary=["Cinema & Pop Culture", "Delhi Lifestyle", "Brand PR Disasters"],
            secondary=["Fashion"],
            will_not_discuss=["electoral politics"],
        ),
        writing_style=WritingStyle(
            tone="witty, conversational",
            typical_length="short",
            formatting=["no hashtags"],
            examples=["Brands pulling ads at the first hint of outrage is predictable."],
        ),
        goals=Goals(
            short_term=["break down viral pop culture moments"],
            long_term=["top cultural voice"],
            content_pillars=["Pop Culture", "Brand Strategy"],
        ),
        rules=Rules(
            always=["provide cultural context", "keep hook punchy"],
            never=["use buzzwords", "use hashtags"],
        ),
    )


def test_parse_engagement_number():
    assert _parse_engagement_number("12.4K") == 12400
    assert _parse_engagement_number("1.5M") == 1500000
    assert _parse_engagement_number("534") == 534
    assert _parse_engagement_number("10,250") == 10250
    assert _parse_engagement_number("0") == 0
    assert _parse_engagement_number("") == 0
    assert _parse_engagement_number("No data") == 0


def test_viral_tweet_model_validation():
    vt = ViralTweet(
        author="John Doe",
        handle="@johndoe",
        verified=True,
        text="Breaking down the massive marketing blunder.",
        views=150000,
        likes=3500,
        retweets=400,
        replies=120,
        media_urls=["https://pbs.twimg.com/media/sample.jpg"],
        tweet_url="https://x.com/johndoe/status/123",
        is_thread=True,
    )
    assert vt.author == "John Doe"
    assert vt.views == 150000
    assert len(vt.media_urls) == 1
    assert vt.is_thread is True


def test_downloaded_media_model():
    dm = DownloadedMedia(
        local_path="/tmp/test.jpg",
        source_url="https://pbs.twimg.com/media/sample.jpg",
        caption="Official statement released by brand.",
        author_handle="@official",
    )
    assert dm.local_path == "/tmp/test.jpg"
    assert dm.author_handle == "@official"


@pytest.mark.asyncio
async def test_generate_search_phrases(sample_persona: Persona):
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(message=MagicMock(content='["Kriti Sanon GIVA", "Kriti Sanon ad controversy", "GIVA Rakhi"]'))
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    queries = await generate_search_phrases("Kriti Sanon controversy", persona=sample_persona, client=mock_client)
    assert len(queries) >= 2
    assert any("Kriti" in q for q in queries)


@pytest.mark.asyncio
async def test_research_topic_comprehensively_pipeline(sample_persona: Persona):
    mock_tweets = [
        ViralTweet(
            author="ANI",
            handle="@ANI",
            verified=True,
            text="GIVA withdraws its Raksha Bandhan ad featuring actress Kriti Sanon.",
            views=1200000,
            likes=12000,
            retweets=2500,
            replies=900,
            media_urls=["https://pbs.twimg.com/media/test_ani.png"],
        ),
        ViralTweet(
            author="Commentator",
            handle="@commentator",
            verified=False,
            text="People outrage over anything. The ad was completely harmless.",
            views=450000,
            likes=3400,
            retweets=300,
            replies=150,
        ),
    ]

    mock_web = [
        {"title": "GIVA Withdraws Ad", "snippet": "Brand pulls ad after criticism on social media.", "url": "https://news.com/1"},
    ]

    mock_client = MagicMock()
    mock_resp_query = MagicMock()
    mock_resp_query.choices = [
        MagicMock(message=MagicMock(content='["Kriti Sanon GIVA", "GIVA controversy"]'))
    ]
    mock_resp_summary = MagicMock()
    mock_resp_summary.choices = [
        MagicMock(message=MagicMock(content='''{
            "summary": "GIVA pulled down its advertisement after facing backlash over traditional styling.",
            "consensus_view": "Ad was disrespectful to tradition.",
            "contrarian_view": "Moral policing of women attire is hypocritical.",
            "key_debates": ["Traditional modesty vs Modern styling", "Brand spine in crisis PR"]
        }'''))
    ]
    mock_client.chat.completions.create = AsyncMock(side_effect=[mock_resp_query, mock_resp_summary])

    with patch("xbot.ai.x_researcher.scrape_x_top_tweets", AsyncMock(return_value=mock_tweets)), \
         patch("xbot.ai.x_researcher.search_web_grounding", AsyncMock(return_value=mock_web)), \
         patch("xbot.ai.x_researcher.download_viral_media", AsyncMock(return_value=[
             DownloadedMedia(local_path="/tmp/ad.jpg", source_url="https://pbs.twimg.com/media/test_ani.png", caption="GIVA ad statement", author_handle="@ANI")
         ])):

        report = await research_topic_comprehensively(
            topic="Kriti Sanon controversy",
            persona=sample_persona,
            client=mock_client,
        )

        assert report.topic == "Kriti Sanon controversy"
        assert len(report.viral_tweets) == 2
        assert len(report.downloaded_media) == 1
        assert "GIVA" in report.summary
        assert report.community_sentiment["consensus_view"] == "Ad was disrespectful to tradition."
        assert len(report.community_sentiment["primary_debates"]) == 2
