from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError

from xbot.ai.visual_engine import (
    VisualPostSpec,
    generate_visual_post_spec,
    infer_format_type,
    infer_simcluster,
    VISUAL_FORMAT_TEMPLATES,
    _build_visual_system_prompt,
    _build_visual_user_prompt,
)
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Persona,
    Personality,
    Rules,
    WritingStyle,
)


@pytest.fixture
def sample_creator_persona() -> Persona:
    return Persona(
        id="kaya_creator",
        display_name="Kaya",
        x_handle="@jackds1234",
        identity=Identity(background="Digital creator and cultural observer based in Mumbai"),
        personality=Personality(
            traits=["witty", "self-aware", "observant"],
            values=["authenticity", "creativity"],
            communication_style="Conversational and sharp",
        ),
        interests=Interests(
            primary=["creator reality", "cinema", "consumer tech"],
            secondary=["memes", "film photography"],
            will_not_discuss=["bjp", "modi"],
        ),
        writing_style=WritingStyle(
            tone="Witty and personal",
            typical_length="concise",
            formatting=["clean_sentence_casing"],
            examples=[
                "My biggest creator struggle is spending 4 hours editing B-roll only for a blurry selfie to go viral. ✨",
                "Christopher Nolan will build a locomotive before touching CGI. 🍿",
            ],
        ),
        goals=Goals(
            content_pillars=["creator humor", "cinema", "tech irony"],
            short_term=[],
            long_term=[],
        ),
        rules=Rules(always=["be authentic"], never=["no politics"]),
    )


def test_visual_post_spec_schema_and_defaults():
    spec = VisualPostSpec(
        tweet_copy="The exact moment you realize the client sent their logo in a Microsoft Word document.",
        image_prompt="4-panel comic in 4:5 aspect ratio (1080x1350), high contrast dark theme #0D1117, panel 1: confident dev...",
        format_type="storyboard_4panel",
        target_simcluster="Tech/AI",
        one_two_punch_strategy="Setup tensions around client feedback; image delivers visual punchline of Word doc panic.",
    )
    assert spec.aspect_ratio == "4:5"
    assert len(spec.tweet_copy) < 140
    assert spec.format_type == "storyboard_4panel"
    assert spec.target_simcluster == "Tech/AI"
    assert "one_two_punch_strategy" in spec.model_dump()


def test_visual_post_spec_tweet_copy_length_validation():
    # If tweet copy exceeds 140 chars, validator automatically remediates/trims or raises ValidationError
    long_copy = "A" * 150
    spec = VisualPostSpec(
        tweet_copy=long_copy,
        image_prompt="A 4:5 portrait photo of a desk setup with 35mm film grain, warm lighting, natural shadows.",
        format_type="urban_lifestyle",
        target_simcluster="Urban/Creator",
        one_two_punch_strategy="Setup creator workspace tension.",
    )
    assert len(spec.tweet_copy) < 140


def test_visual_post_spec_aspect_ratio_values():
    # 4:5 is standard mobile portrait takeover (~74% viewport); 1:1 is also valid
    spec_4_5 = VisualPostSpec(
        tweet_copy="When your model runs locally vs in production.",
        image_prompt="Side by side 4:5 portrait comparison...",
        aspect_ratio="4:5",
        format_type="side_by_side",
        target_simcluster="Tech/AI",
        one_two_punch_strategy="Left expectation vs right production reality.",
    )
    assert spec_4_5.aspect_ratio == "4:5"

    spec_1_1 = VisualPostSpec(
        tweet_copy="Square meme format test.",
        image_prompt="Square format 1:1 meme...",
        aspect_ratio="1:1",
        format_type="storyboard_4panel",
        target_simcluster="Anime/PopCulture",
        one_two_punch_strategy="Square meme test.",
    )
    assert spec_1_1.aspect_ratio == "1:1"

    with pytest.raises(ValidationError):
        VisualPostSpec(
            tweet_copy="Invalid aspect ratio post.",
            image_prompt="Some prompt...",
            aspect_ratio="16:9",  # Only 4:5 and 1:1 allowed
            format_type="storyboard_4panel",
            target_simcluster="Tech/AI",
            one_two_punch_strategy="Strategy.",
        )


@pytest.mark.parametrize("format_type,expected_simcluster", [
    ("storyboard_4panel", "Tech/AI"),
    ("side_by_side", "Tech/AI"),
    ("urban_lifestyle", "Urban/Creator"),
    ("dark_infographic", "Tech/AI"),
])
@pytest.mark.asyncio
async def test_generate_visual_post_spec_four_pillars(
    format_type: str,
    expected_simcluster: str,
    sample_creator_persona: Persona,
):
    mock_client = AsyncMock()
    mock_payload = {
        "tweet_copy": f"Setup tension hook for format {format_type}.",
        "image_prompt": f"Detailed prompt for {format_type} in 4:5 portrait (1080x1350), dark mode #0D1117, high contrast lighting.",
        "aspect_ratio": "4:5",
        "format_type": format_type,
        "target_simcluster": expected_simcluster,
        "one_two_punch_strategy": f"Tension setup hook with visual payoff in {format_type}.",
    }
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content=json.dumps(mock_payload)))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    spec = await generate_visual_post_spec(
        topic=f"Exploring {format_type} trends in modern workflows",
        format_type=format_type,
        persona=sample_creator_persona,
        client=mock_client,
    )

    assert isinstance(spec, VisualPostSpec)
    assert spec.format_type == format_type
    assert spec.aspect_ratio == "4:5"
    assert len(spec.tweet_copy) < 140
    assert len(spec.image_prompt) > 20
    assert spec.target_simcluster == expected_simcluster
    assert spec.one_two_punch_strategy


@pytest.mark.asyncio
async def test_generate_visual_post_spec_ai_fallback(sample_creator_persona: Persona):
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = TimeoutError("Heavy AI model timed out")

    spec = await generate_visual_post_spec(
        topic="Debugging in production on a Friday at 5 PM",
        format_type="storyboard_4panel",
        persona=sample_creator_persona,
        client=mock_client,
    )

    assert isinstance(spec, VisualPostSpec)
    assert spec.aspect_ratio == "4:5"
    assert len(spec.tweet_copy) < 140
    assert len(spec.image_prompt) > 30
    assert spec.format_type == "storyboard_4panel"
    assert spec.target_simcluster in ["Tech/AI", "Urban/Creator", "Cinema/Prestige", "Anime/PopCulture"]
    assert spec.one_two_punch_strategy


@pytest.mark.asyncio
async def test_generate_visual_post_spec_format_inference_when_none():
    mock_client = AsyncMock()
    # Mock returning valid json inferred from topic
    mock_payload = {
        "tweet_copy": "Why system design cheat sheets look so peaceful until latency spikes.",
        "image_prompt": "High-contrast dark-mode infographic (#0D1117) in 4:5 portrait (1080x1350) with neon cyan accents.",
        "aspect_ratio": "4:5",
        "format_type": "dark_infographic",
        "target_simcluster": "Tech/AI",
        "one_two_punch_strategy": "Setup calm system design vs chaotic production failure.",
    }
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content=json.dumps(mock_payload)))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    spec = await generate_visual_post_spec(
        topic="Distributed caching system architecture cheatsheet",
        format_type=None,
        persona=None,
        client=mock_client,
    )

    assert spec.format_type == "dark_infographic"
    assert spec.aspect_ratio == "4:5"
    assert len(spec.tweet_copy) < 140


def test_infer_format_type_keywords():
    assert infer_format_type("PostgreSQL vs MongoDB indexing shootout") == "side_by_side"
    assert infer_format_type("System design cheatsheet and framework for microservices") == "dark_infographic"
    assert infer_format_type("Street photography vlog behind the scenes in Mumbai") == "urban_lifestyle"
    assert infer_format_type("4-step comic of deploying on Friday") == "storyboard_4panel"


def test_infer_simcluster_keywords():
    assert infer_simcluster("New AI GPU benchmarks", "dark_infographic") == "Tech/AI"
    assert infer_simcluster("Oppenheimer 70mm IMAX cinematography breakdown", "side_by_side") == "Cinema/Prestige"
    assert infer_simcluster("Daily cafe vlog editing routine", "urban_lifestyle") == "Urban/Creator"
    assert infer_simcluster("Anime seasonal tier list", "storyboard_4panel") == "Anime/PopCulture"


@pytest.mark.asyncio
async def test_generate_visual_post_spec_enforces_max_140_chars():
    mock_client = AsyncMock()
    # Simulate an AI returning an overly verbose 200-char hook
    overly_long_text = "This is an extremely long tweet copy returned by the language model that definitely exceeds the one hundred and forty character limit mandated for the One-Two Punch tension hook architecture on mobile viewports."
    assert len(overly_long_text) > 140

    mock_payload = {
        "tweet_copy": overly_long_text,
        "image_prompt": "A 4:5 portrait photo of a creator editing video on a laptop at midnight with ambient lighting.",
        "aspect_ratio": "4:5",
        "format_type": "urban_lifestyle",
        "target_simcluster": "Urban/Creator",
        "one_two_punch_strategy": "Tension hook around late night editing.",
    }
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content=json.dumps(mock_payload)))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    spec = await generate_visual_post_spec(
        topic="Late night creator editing grind",
        format_type="urban_lifestyle",
        client=mock_client,
    )

    assert len(spec.tweet_copy) < 140
    assert spec.aspect_ratio == "4:5"


@pytest.mark.asyncio
async def test_generate_visual_post_spec_markdown_json_cleaning():
    mock_client = AsyncMock()
    raw_markdown = """```json
    {
      "tweet_copy": "That 1% battery panic during a live stream.",
      "image_prompt": "4-panel meme comic in 4:5 portrait (1080x1350) showing battery dropping.",
      "aspect_ratio": "4:5",
      "format_type": "storyboard_4panel",
      "target_simcluster": "Urban/Creator",
      "one_two_punch_strategy": "Tension setup on battery drop; visual panic escalation."
    }
    ```"""
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content=raw_markdown))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    spec = await generate_visual_post_spec(
        topic="Streaming on low battery",
        client=mock_client,
    )

    assert spec.tweet_copy == "That 1% battery panic during a live stream."
    assert spec.format_type == "storyboard_4panel"


@pytest.mark.asyncio
async def test_generate_visual_post_spec_default_client_resolution():
    mock_client = AsyncMock()
    mock_payload = {
        "tweet_copy": "Default client resolution hook.",
        "image_prompt": "A 4:5 portrait image prompt.",
        "aspect_ratio": "4:5",
        "format_type": "urban_lifestyle",
        "target_simcluster": "Urban/Creator",
        "one_two_punch_strategy": "Default client test.",
    }
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content=json.dumps(mock_payload)))]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("xbot.ai.visual_engine.get_ai_client", return_value=mock_client):
        spec = await generate_visual_post_spec(
            topic="Testing default client",
        )
        assert spec.tweet_copy == "Default client resolution hook."


def test_visual_prompt_builders(sample_creator_persona: Persona):
    sys_prompt = _build_visual_system_prompt(persona=sample_creator_persona, format_type="dark_infographic")
    assert "Kaya" in sys_prompt
    assert "One-Two Punch" in sys_prompt
    assert "4:5" in sys_prompt

    user_prompt = _build_visual_user_prompt(
        topic="Microservices vs Monoliths in 2026",
        format_type="side_by_side",
        persona=sample_creator_persona,
    )
    assert "Microservices vs Monoliths in 2026" in user_prompt
    assert "side_by_side" in user_prompt
