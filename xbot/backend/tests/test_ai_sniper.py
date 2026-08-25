from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from xbot.ai.growth_scorer import OpportunityScore, score_tweet_opportunity
from xbot.ai.sniper import (
    SNIPER_PROMPT_TEMPLATE,
    SniperReplyResult,
    SniperResult,
    generate_sniper_reply,
    verify_sniper_reply,
)
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
    mock_result = SniperResult(
        reply_text="Compute is currency, but memory bandwidth is the tax rate. Scaling compute without fast interconnects just creates faster idle loops. How are you solving the memory wall?",
        debate_catalyst="How are you solving the memory wall?",
        angle="contrarian",
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

    assert isinstance(result, SniperResult)
    assert isinstance(result, SniperReplyResult)
    assert result.reply_text.startswith("Compute is currency")
    assert result.reply_text.endswith("?")
    assert result.debate_catalyst == "How are you solving the memory wall?"
    assert result.angle == "contrarian"
    assert result.angle_used == "contrarian"
    assert result.confidence == 0.95
    assert "memory bandwidth" in result.reasoning
    assert 140 <= len(result.reply_text) <= 260
    assert mock_client.beta.chat.completions.parse.called


@pytest.mark.asyncio
async def test_generate_sniper_reply_json_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests fallback to chat.completions.create with JSON parsing when structured parse fails."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Provider does not support parse")

    json_payload = {
        "reply_text": "The 3 layers of AI value: 1. Energy availability, 2. Memory bandwidth, 3. Compute density. Most only focus on compute. How are you indexing for interconnects?",
        "debate_catalyst": "How are you indexing for interconnects?",
        "angle": "framework",
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

    assert isinstance(result, SniperResult)
    assert result.angle == "framework"
    assert result.angle_used == "framework"
    assert "The 3 layers" in result.reply_text
    assert result.reply_text.endswith("?")
    assert result.debate_catalyst == "How are you indexing for interconnects?"
    assert result.confidence == 0.9
    assert len(result.reply_text) <= 260


@pytest.mark.asyncio
async def test_generate_sniper_reply_raw_text_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests fallback when response is plain unformatted text (not JSON)."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    raw_text = 'Compute scaling is only half the equation; thermal density at datacenter scale will be the true cap over the next decade. What is your cooling headroom?'
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

    assert isinstance(result, SniperResult)
    assert result.reply_text.endswith("?")
    assert result.angle == "insight"
    assert result.confidence > 0.0


@pytest.mark.asyncio
async def test_generate_sniper_reply_angles_and_prompts(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that various angles (witty, data, contrarian, framework, question, insight) are respected in prompt."""
    angles = ["witty", "data", "contrarian", "framework", "question", "insight"]

    for angle in angles:
        mock_client = AsyncMock()
        mock_result = SniperResult(
            reply_text=f"Response for {angle} angle providing high-density proof points and contrasting the thesis. What metrics are you tracking for this specific trade-off?",
            debate_catalyst="What metrics are you tracking for this specific trade-off?",
            angle=angle,
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

        assert res.angle == angle
        assert res.angle_used == angle
        assert res.reply_text.endswith("?")
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
    mock_result = SniperResult(
        reply_text="Energy constraints will hit before algorithmic limits; sub-station grid interconnects are the actual bottleneck. Have you secured dedicated capacity?",
        debate_catalyst="Have you secured dedicated capacity?",
        angle="insight",
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

    assert res.angle == "insight"
    assert res.reply_text.endswith("?")
    call_args = mock_client.beta.chat.completions.parse.call_args
    messages = call_args.kwargs.get("messages", [])
    prompt_content = " ".join(m["content"] for m in messages)
    assert "contrarian" in prompt_content
    assert "framework" in prompt_content
    assert "question" in prompt_content
    assert "witty" in prompt_content
    assert "data" in prompt_content


@pytest.mark.asyncio
async def test_generate_sniper_reply_exception_safe_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that complete LLM failure returns a safe fallback SniperResult without throwing."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = ConnectionError("Network down")
    mock_client.chat.completions.create.side_effect = ConnectionError("Network down")

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="witty",
        client=mock_client,
    )

    assert isinstance(result, SniperResult)
    assert result.confidence == 0.0
    assert "Network down" in result.reasoning or "failed" in result.reasoning.lower()
    assert result.angle == "witty"
    assert result.angle_used == "witty"


@pytest.mark.asyncio
async def test_generate_sniper_reply_default_client_resolution(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that when client is None, get_ai_client() is invoked."""
    mock_result = SniperResult(
        reply_text="Default client response with empirical data and concrete architecture proof points. How does this scale under 10x query load?",
        debate_catalyst="How does this scale under 10x query load?",
        angle="insight",
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

        assert res.reply_text.startswith("Default client response")
        assert res.reply_text.endswith("?")
        mock_get_ai_client.assert_called_once()


@pytest.mark.asyncio
async def test_generate_sniper_reply_length_constraint_enforcement(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that excessively long replies (> 260 chars) are trimmed to 260 chars and end with ?."""
    long_text = ("A" * 300) + " What is your take?"
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

    assert len(result.reply_text) <= 260
    assert result.reply_text.endswith("?")


@pytest.mark.asyncio
async def test_generate_sniper_reply_multimodal_vision(
    sample_persona: Persona,
) -> None:
    """Tests that attached images/media_urls generate multimodal vision user content."""
    image_tweet = {
        "author": "TechReviewer",
        "text": "Check out this leaked benchmark chart",
        "top_comments": ["Looks insane", "Fake chart"],
        "media_urls": ["https://pbs.twimg.com/media/leak_chart.jpg"],
        "media_alts": ["Geekbench 6 multi-core performance comparison between M4 and Snapdragon X Elite"],
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(
        content='{"reply_text": "Snapdragon closing the efficiency gap on multi-core is huge, but memory bandwidth remains 30% behind M4 Max. Will software optimization bridge this gap?", "debate_catalyst": "Will software optimization bridge this gap?", "angle": "insight", "confidence": 0.95, "reasoning": "Analyzed benchmark chart"}'
    )
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=image_tweet,
        client=mock_client,
    )

    assert "Snapdragon" in result.reply_text
    assert result.reply_text.endswith("?")
    assert result.debate_catalyst == "Will software optimization bridge this gap?"
    # Verify vision payload was sent in completions call
    call_args = mock_client.chat.completions.create.call_args
    messages = call_args.kwargs.get("messages", [])
    user_msg = next((m for m in messages if m["role"] == "user"), None)
    assert user_msg is not None
    assert isinstance(user_msg["content"], list)
    assert any(
        b.get("type") == "image_url"
        and b.get("image_url", {}).get("url") == "https://pbs.twimg.com/media/leak_chart.jpg"
        for b in user_msg["content"]
    )


def test_verify_sniper_reply_indian_politics_rejection() -> None:
    """Tests that any reply or target tweet mentioning Indian politics is rejected."""
    val1, reason1 = verify_sniper_reply("BJP policy announcements will impact the upcoming budget.")
    assert val1 is False
    assert "Indian political terms" in reason1

    val2, reason2 = verify_sniper_reply("Modi spoke about tech advancements in the conference today.")
    assert val2 is False
    assert "Indian political terms" in reason2

    val3, reason3 = verify_sniper_reply("Congress campaign rallies are trending across social media.")
    assert val3 is False
    assert "Indian political terms" in reason3

    val4, reason4 = verify_sniper_reply(
        reply_text="This looks like a massive crowd.",
        target_text="AAP and Kejriwal announced new electricity subsidies today.",
    )
    assert val4 is False
    assert "political safety filter" in reason4


def test_sniper_result_model_validation() -> None:
    """Tests SniperResult Pydantic schema validation and debate catalyst extraction."""
    # 1. Valid SniperResult ending with ?
    valid_res = SniperResult(
        reply_text="Compute scaling is sub-linear beyond 100k clusters; interconnect topology caps GPU utilization at 45%. How are you mitigating tail latency?",
        angle="data",
    )
    assert valid_res.reply_text.endswith("?")
    assert valid_res.debate_catalyst == "How are you mitigating tail latency?"
    assert valid_res.angle == "data"
    assert valid_res.angle_used == "data"

    # 2. Valid SniperResult without question mark (strong punchy statement / dry humor)
    punchy_res = SniperResult(
        reply_text="Compute scaling is sub-linear beyond 100k clusters; interconnect topology caps GPU utilization at 45%.",
        angle="data",
    )
    assert punchy_res.reply_text.startswith("Compute scaling")
    assert punchy_res.angle == "data"

    # 3. Empty reply_text in error fallbacks does not throw
    fallback_res = SniperResult(reply_text="", confidence=0.0)
    assert fallback_res.reply_text == ""
    assert fallback_res.confidence == 0.0


def test_sniper_3_part_structure_and_debate_catalyst() -> None:
    """Tests that replies adhere to Value Hook + Concrete Proof / Debate Catalyst formula without clichés."""
    reply = "Compute scaling is only half the equation; thermal density at datacenter scale will be the true cap over the next decade. What is your cooling headroom?"
    
    # 1. Assert length is within mobile tweet bounds
    assert 40 <= len(reply) <= 260
    
    # 2. Assert no generic AI clichés
    cliches = ["delve", "testament", "tapestry", "supercharge", "Great post!", "100% agree"]
    for c in cliches:
        assert c.lower() not in reply.lower()

    # 3. Instantiate model and verify catalyst extraction
    result = SniperResult(reply_text=reply, angle="contrarian")
    assert result.debate_catalyst == "What is your cooling headroom?"
    assert result.angle == "contrarian"


def test_verify_sniper_reply_banned_cliches() -> None:
    """Tests that verify_sniper_reply rejects banned AI clichés and bot praise."""
    # Cliché delve
    ok1, reason1 = verify_sniper_reply("Let us delve into the architecture of modern transformers.")
    assert ok1 is False
    assert "delve" in reason1

    # Cliché testament
    ok2, reason2 = verify_sniper_reply("This benchmark is a testament to the efficiency of ARM silicon.")
    assert ok2 is False
    assert "testament" in reason2

    # Cliché tapestry
    ok3, reason3 = verify_sniper_reply("We are witnessing a rich tapestry of neural network advances.")
    assert ok3 is False
    assert "tapestry" in reason3

    # Cliché supercharge
    ok4, reason4 = verify_sniper_reply("This tool will supercharge your developer productivity.")
    assert ok4 is False
    assert "supercharge" in reason4

    # Bot praise Great post!
    ok5, reason5 = verify_sniper_reply("Great post! This is really helpful for beginners.")
    assert ok5 is False
    assert "generic bot praise" in reason5

    # Robotic survey question
    ok6, reason6 = verify_sniper_reply("Compute scaling is accelerating. What do you think?")
    assert ok6 is False
    assert "robotic survey question" in reason6


def test_sniper_prompt_template_contents() -> None:
    """Tests that SNIPER_PROMPT_TEMPLATE includes high-impact archetypes, emoji rules, and banned words."""
    assert "HIGH-IMPACT SNIPER REPLY ARCHITECTURE" in SNIPER_PROMPT_TEMPLATE
    assert "NO TOPIC-LABELING EMOJIS" in SNIPER_PROMPT_TEMPLATE
    assert "EMOTION-DRIVEN CONTEXT ONLY" in SNIPER_PROMPT_TEMPLATE
    assert "delve" in SNIPER_PROMPT_TEMPLATE
    assert "testament" in SNIPER_PROMPT_TEMPLATE
    assert "tapestry" in SNIPER_PROMPT_TEMPLATE
    assert "supercharge" in SNIPER_PROMPT_TEMPLATE


@pytest.mark.asyncio
async def test_generate_sniper_reply_with_growth_opportunity_score(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests integrating OpportunityScore from growth_scorer with sniper reply generation."""
    opp_score = score_tweet_opportunity(sample_tweet)
    assert isinstance(opp_score, OpportunityScore)

    mock_result = SniperResult(
        reply_text="Compute scaling is bound by physics at wafer scale; interconnect latency dominates past 10k GPUs. How are you approaching optical interconnects?",
        debate_catalyst="How are you approaching optical interconnects?",
        angle="data",
        confidence=0.96,
        reasoning=f"High opportunity score ({opp_score.score}) warrants deep data angle.",
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=mock_result)
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="data",
        client=mock_client,
    )

    assert result.angle == "data"
    assert 140 <= len(result.reply_text) <= 260
    assert result.reply_text.endswith("?")
    assert result.debate_catalyst == "How are you approaching optical interconnects?"



