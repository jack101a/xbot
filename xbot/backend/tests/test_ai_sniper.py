from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xbot.ai.sniper import SniperReplyResult, generate_sniper_reply
from xbot.persona.loader import (
    Identity,
    Interests,
    Personality,
    Persona,
    Rules,
    TargetKOL,
    WritingStyle,
    Goals,
)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="tech_analyst",
        display_name="Tech Analyst",
        x_handle="@techanalyst",
        identity=Identity(
            background="Senior distributed systems architect with 15 years experience.",
            occupation="Systems Architect",
        ),
        personality=Personality(
            traits=["analytical", "skeptical", "witty"],
            values=["rigor", "simplicity"],
            communication_style="Direct, concise, data-driven",
        ),
        interests=Interests(
            primary=["AI Infrastructure", "Databases", "Distributed Systems"],
            secondary=["High Performance Computing"],
            will_not_discuss=["partisan politics", "crypto pump schemes"],
        ),
        writing_style=WritingStyle(
            tone="sharp, analytical, witty",
            typical_length="short",
            formatting=["no emojis", "no hashtags"],
            examples=[
                "Most distributed databases fail because consensus is hard, not because disk is slow.",
                "If you can't describe your architecture in 3 boxes, it's already broken.",
            ],
        ),
        goals=Goals(
            short_term=["build technical credibility"],
            long_term=["industry influence"],
            content_pillars=["System design breakdowns", "AI scaling limits"],
        ),
        rules=Rules(
            always=["provide concrete technical nuance", "keep under 240 chars"],
            never=["use generic praise", "use hashtags", "say 'Great post!'"],
        ),
        target_kols=[
            TargetKOL(
                handle="sama",
                category="ai",
                priority="high",
                preferred_angle="framework",
            )
        ],
    )


@pytest.fixture
def sample_tweet() -> dict:
    return {
        "tweet_id": "1892837461928374",
        "author": "sama",
        "text": "Compute will be the currency of the future. The scaling laws for compute efficiency are continuing unabated.",
        "url": "https://x.com/sama/status/1892837461928374",
        "created_at": "2m",
        "is_pinned": False,
    }


@pytest.mark.asyncio
async def test_generate_sniper_reply_structured_parse(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests successful structured parsing via client.beta.chat.completions.parse."""
    mock_result = SniperReplyResult(
        reply_text="Compute is currency, but memory bandwidth is the tax rate. Scaling compute without fast interconnects just creates faster idle loops.",
        angle_used="contrarian",
        confidence=0.95,
        reasoning="Challenges compute-only premise with memory bandwidth bottleneck.",
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message = MagicMock(parsed=mock_result)
    mock_parse_response = MagicMock(choices=[mock_parsed_choice])

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = mock_parse_response

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="contrarian",
        client=mock_client,
    )

    assert isinstance(result, SniperReplyResult)
    assert result.reply_text.startswith("Compute is currency")
    assert result.angle_used == "contrarian"
    assert result.confidence == 0.95
    assert "memory bandwidth" in result.reasoning
    assert len(result.reply_text) <= 280
    assert mock_client.beta.chat.completions.parse.called


@pytest.mark.asyncio
async def test_generate_sniper_reply_json_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests fallback to chat.completions.create with JSON parsing when structured parse fails."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Provider does not support parse")

    json_payload = {
        "reply_text": "The 3 layers of AI value: 1. Energy availability, 2. Memory bandwidth, 3. Compute density. Most only focus on #3.",
        "angle_used": "framework",
        "confidence": 0.9,
        "reasoning": "Provides a 3-layer mental framework.",
    }

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_create_response = MagicMock(choices=[mock_choice])
    mock_client.chat.completions.create.return_value = mock_create_response

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="framework",
        client=mock_client,
    )

    assert isinstance(result, SniperReplyResult)
    assert result.angle_used == "framework"
    assert "The 3 layers" in result.reply_text
    assert result.confidence == 0.9
    assert len(result.reply_text) <= 280


@pytest.mark.asyncio
async def test_generate_sniper_reply_raw_text_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests fallback when response is plain unformatted text (not JSON)."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    raw_text = 'Compute scaling is only half the equation; thermal density at datacenter scale will be the true cap.'
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=raw_text)
    mock_create_response = MagicMock(choices=[mock_choice])
    mock_client.chat.completions.create.return_value = mock_create_response

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="insight",
        client=mock_client,
    )

    assert isinstance(result, SniperReplyResult)
    assert result.reply_text == raw_text
    assert result.angle_used == "insight"
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_generate_sniper_reply_angles_and_prompts(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that various angles (witty, data, contrarian, framework, insight) are respected in prompt."""
    angles = ["witty", "data", "contrarian", "framework", "insight"]

    for angle in angles:
        mock_client = AsyncMock()
        mock_result = SniperReplyResult(
            reply_text=f"Response for {angle} angle.",
            angle_used=angle,
            confidence=0.9,
            reasoning=f"Reasoning for {angle}",
        )
        mock_choice = MagicMock()
        mock_choice.message = MagicMock(parsed=mock_result)
        mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

        res = await generate_sniper_reply(
            persona=sample_persona,
            target_tweet=sample_tweet,
            preferred_angle=angle,
            client=mock_client,
        )

        assert res.angle_used == angle
        # Verify prompt received the preferred angle
        call_args = mock_client.beta.chat.completions.parse.call_args
        messages = call_args.kwargs.get("messages", [])
        prompt_content = " ".join(m["content"] for m in messages)
        assert angle.lower() in prompt_content.lower()


@pytest.mark.asyncio
async def test_generate_sniper_reply_auto_angle_selection(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that when preferred_angle is None, prompt instructs auto-selection among valid angles."""
    mock_client = AsyncMock()
    mock_result = SniperReplyResult(
        reply_text="Energy constraints will hit before algorithmic limits.",
        angle_used="insight",
        confidence=0.88,
        reasoning="Selected insight as most impactful angle",
    )
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=mock_result)
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    res = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle=None,
        client=mock_client,
    )

    assert res.angle_used == "insight"
    call_args = mock_client.beta.chat.completions.parse.call_args
    messages = call_args.kwargs.get("messages", [])
    prompt_content = " ".join(m["content"] for m in messages)
    assert "contrarian" in prompt_content
    assert "framework" in prompt_content
    assert "witty" in prompt_content
    assert "data" in prompt_content


@pytest.mark.asyncio
async def test_generate_sniper_reply_exception_safe_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that complete LLM failure returns a safe fallback SniperReplyResult without throwing."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = ConnectionError("Network down")
    mock_client.chat.completions.create.side_effect = ConnectionError("Network down")

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="witty",
        client=mock_client,
    )

    assert isinstance(result, SniperReplyResult)
    assert result.confidence == 0.0
    assert "Network down" in result.reasoning or "failed" in result.reasoning.lower()
    assert result.angle_used == "witty"


@pytest.mark.asyncio
async def test_generate_sniper_reply_default_client_resolution(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that when client is None, get_ai_client() is invoked."""
    mock_result = SniperReplyResult(
        reply_text="Default client response.",
        angle_used="insight",
        confidence=0.9,
        reasoning="Test",
    )
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=mock_result)
    mock_parse_response = MagicMock(choices=[mock_choice])

    with patch("xbot.ai.sniper.get_ai_client") as mock_get_ai_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_parse_response
        mock_get_ai_client.return_value = mock_client

        res = await generate_sniper_reply(
            persona=sample_persona,
            target_tweet=sample_tweet,
        )

        assert res.reply_text == "Default client response."
        mock_get_ai_client.assert_called_once()


@pytest.mark.asyncio
async def test_generate_sniper_reply_length_constraint_enforcement(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that excessively long replies (> 280 chars) are trimmed to 280 chars."""
    long_text = "A" * 320
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=long_text)
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        client=mock_client,
    )

    assert len(result.reply_text) <= 280
