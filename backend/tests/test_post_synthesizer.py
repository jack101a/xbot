import pytest
from unittest.mock import AsyncMock, patch
from xbot.ai.post_synthesizer import synthesize_creator_post, _build_clean_creator_prompt
from xbot.persona.loader import Persona, Identity, Personality, Interests, WritingStyle, Goals, Rules

@pytest.fixture
def sample_creator_persona():
    return Persona(
        id="test_creator",
        display_name="Kaya",
        x_handle="@jackds1234",
        identity=Identity(background="Digital creator and cultural observer"),
        personality=Personality(
            traits=["witty", "self-aware", "observant"],
            values=["authenticity", "creativity"],
            communication_style="Conversational and sharp",
        ),
        interests=Interests(
            primary=["creator reality", "cinema", "consumer tech"],
            secondary=["memes"],
            will_not_discuss=["bjp", "modi"],
        ),
        writing_style=WritingStyle(
            tone="Witty and personal",
            typical_length="concise",
            formatting=["clean_sentence_casing"],
            examples=[
                "My biggest creator struggle is spending 4 hours editing B-roll only for a blurry selfie to go viral. ✨",
                "Christopher Nolan will build a locomotive before touching CGI. 🍿"
            ],
        ),
        goals=Goals(
            content_pillars=["creator humor", "cinema"],
            short_term=[],
            long_term=[],
        ),
        rules=Rules(always=["be authentic"], never=["no politics"]),
    )

def test_build_clean_creator_prompt_strips_db_bloat(sample_creator_persona):
    prompt = _build_clean_creator_prompt(
        topic="Filming 4k video on modern smartphones vs dedicated cameras",
        persona=sample_creator_persona,
        vision_summary="Photo shows a tripod setup with an iPhone next to a Sony mirrorless camera.",
        search_facts=[{"title": "Camera Shootout 2026", "snippet": "Smartphone dynamic range is now within 1 stop of APS-C sensors."}],
        recent_posts=["Previous post about editing workflows"],
        post_type="post",
    )
    # Verify high-signal sections exist
    assert "Topic / Event Premise" in prompt
    assert "Visual Image Analysis" in prompt
    assert "Live Web Search Facts" in prompt
    assert "High-Engagement Creator Style Examples" in prompt
    assert "Do NOT Repeat These Recent Posts" in prompt
    # Verify zero database/budget bloat
    assert "Rate budget remaining" not in prompt
    assert "Your Strategy" not in prompt
    assert "Your Performance (Last 7 Days)" not in prompt

@pytest.mark.asyncio
async def test_synthesize_creator_post_success(sample_creator_persona):
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"content": "Smartphone sensors are getting so good that 90% of the reason people buy dedicated cameras now is just to look like an artistic genius at family weddings. 📸", "reasoning": "Sharp creator irony on modern camera tech."}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("xbot.ai.post_synthesizer.search_web_grounding", return_value=[{"title": "Sensor News", "snippet": "New sensor released"}]), \
         patch("xbot.ai.post_synthesizer.analyze_image_context", return_value="Camera setup on desk"):
        res = await synthesize_creator_post(
            topic="Smartphone vs mirrorless cameras",
            persona=sample_creator_persona,
            image_url="https://example.com/camera.jpg",
            client=mock_client,
        )

        assert res.status == "success"
        assert len(res.content) > 20
        assert "family weddings" in res.content
        assert res.vision_context == "Camera setup on desk"
        assert len(res.search_facts) == 1

@pytest.mark.asyncio
async def test_synthesize_creator_post_heavy_failure_discards_cleanly(sample_creator_persona):
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = TimeoutError("All writing models timed out")

    res = await synthesize_creator_post(
        topic="New movie trailer release",
        persona=sample_creator_persona,
        client=mock_client,
    )

    assert res.status == "failed"
    assert res.content == ""
    assert "unavailable or timed out" in res.reasoning


@pytest.mark.asyncio
async def test_synthesize_creator_post_link_extraction_and_open_loop_hook(sample_creator_persona):
    """Tests that external links in synthesized posts are stripped to extracted_link and open-loop hook is <100 chars."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"content": "Most people misunderstand cinema lighting completely.\\n\\nHere is the 3-step cheat sheet:\\n1. Key light at 45 degrees\\n2. 2:1 fill ratio\\n3. Rim light separation\\n\\nFull tutorial at https://cinematography.dev/lighting", "reasoning": "High bookmark cheat sheet."}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("xbot.ai.post_synthesizer.search_web_grounding", return_value=[]), \
         patch("xbot.ai.post_synthesizer.analyze_image_context", return_value=None):
        res = await synthesize_creator_post(
            topic="Cinematic lighting tips",
            persona=sample_creator_persona,
            client=mock_client,
        )

        assert res.status == "success"
        assert res.extracted_link == "https://cinematography.dev/lighting"
        assert "https://" not in res.content
        assert "1. Key light at 45 degrees" in res.content
        assert res.open_loop_hook is not None
        assert len(res.open_loop_hook) < 100
        assert res.open_loop_hook == "Most people misunderstand cinema lighting completely."


@pytest.mark.asyncio
async def test_synthesize_creator_thread_link_extraction(sample_creator_persona):
    """Tests link stripping from thread items and open-loop hook extraction."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content='{"content": "The camera market is shifting faster than smartphones in 2012 🧵", "thread_items": ["Tweet 1: Mirrorless sensors are peaking.", "Tweet 2: Computational optics taking over. Full whitepaper at https://imaging.tech/paper", "Tweet 3: The future is software."], "reasoning": "Thread on camera trends."}'))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("xbot.ai.post_synthesizer.search_web_grounding", return_value=[]), \
         patch("xbot.ai.post_synthesizer.analyze_image_context", return_value=None):
        res = await synthesize_creator_post(
            topic="Future of camera hardware",
            persona=sample_creator_persona,
            post_type="thread",
            client=mock_client,
        )

        assert res.status == "success"
        assert res.extracted_link == "https://imaging.tech/paper"
        assert res.thread_items is not None
        assert len(res.thread_items) == 3
        assert "https://" not in res.thread_items[1]
        assert len(res.open_loop_hook) < 100


def test_build_clean_creator_prompt_includes_open_loop_and_bookmark_directives(sample_creator_persona):
    """Tests that prompt directives include <100 char open-loop hook, bookmark-bait, and zero link rules."""
    prompt = _build_clean_creator_prompt(
        topic="Engineering cheat sheets",
        persona=sample_creator_persona,
        post_type="post",
    )
    assert "< 100 characters" in prompt or "<100 chars" in prompt
    assert "bookmark" in prompt.lower()
    assert "external url" in prompt.lower() or "link" in prompt.lower()

