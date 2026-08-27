from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from xbot.ai.growth_scorer import OpportunityScore, score_tweet_opportunity
from xbot.ai.sniper import (
    SNIPER_PROMPT_TEMPLATE,
    VALID_RESPONSE_MODES,
    DynamicReplyResult,
    SniperReplyResult,
    SniperResult,
    _build_sniper_system_prompt,
    _build_sniper_user_prompt,
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


@pytest.fixture(autouse=True)
def mock_live_fact_grounding():
    """Mock live fact grounder across unit tests for fast and deterministic execution."""
    with patch("xbot.ai.fact_grounder.ground_context_with_live_facts", new_callable=AsyncMock) as mock_ground:
        mock_ground.return_value = ""
        yield mock_ground


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


# =========================================================================
# 1. Schema & 6 Modalities Tests
# =========================================================================

def test_sniper_result_modalities_and_defaults() -> None:
    """Tests all 6 dynamic reply modalities and schema validation."""
    modalities = [
        ("pure_gif", "real", "side eye"),
        ("emoji_reaction", "💀", None),
        ("punchy_one_liner", "they are not gonna like this one", None),
        ("witty_sarcasm", "Marketing departments treating individual episodes like patch notes is crazy.", None),
        ("casual_take", "Honestly the latency trade-off isn't worth the architectural complexity.", None),
        ("in_depth_breakdown", "Wafer-scale integration solves interconnect bottlenecks by keeping memory on-die.", None),
    ]

    for mode, text, gif in modalities:
        result = SniperResult(
            response_mode=mode,
            reply_text=text,
            gif_query=gif,
            angle="insight",
        )
        assert result.response_mode == mode
        assert result.reply_text == text
        assert result.gif_query == gif
        assert result.angle == "insight"
        assert result.angle_used == "insight"


def test_dynamic_reply_result_alias_compatibility() -> None:
    """Tests DynamicReplyResult and SniperReplyResult aliases."""
    assert DynamicReplyResult is SniperResult
    assert SniperReplyResult is SniperResult

    dyn = DynamicReplyResult(
        response_mode="punchy_one_liner",
        reply_text="ok i agree",
        angle="witty",
    )
    assert isinstance(dyn, SniperResult)
    assert dyn.response_mode == "punchy_one_liner"
    assert dyn.reply_text == "ok i agree"


def test_sniper_result_quote_stripping() -> None:
    """Tests that leading and trailing quotes are stripped on model initialization."""
    res1 = SniperResult(
        response_mode="witty_sarcasm",
        reply_text='"The M4 Max efficiency gap is absurd."',
        debate_catalyst='"What is your cooling headroom?"',
    )
    assert res1.reply_text == "The M4 Max efficiency gap is absurd."
    assert res1.debate_catalyst == "What is your cooling headroom?"

    res2 = SniperResult(
        response_mode="punchy_one_liner",
        reply_text="'pure cinema'",
    )
    assert res2.reply_text == "pure cinema"


def test_sniper_result_debate_catalyst_extraction() -> None:
    """Tests that debate_catalyst is extracted only when a question mark is present."""
    # With question
    res_with_q = SniperResult(
        reply_text="Compute scaling is sub-linear beyond 100k clusters. How are you mitigating tail latency?",
        angle="data",
    )
    assert res_with_q.debate_catalyst == "How are you mitigating tail latency?"

    # Without question (must NOT invent catalyst or append question)
    res_no_q = SniperResult(
        reply_text="Compute scaling is sub-linear beyond 100k clusters; interconnect topology caps GPU utilization.",
        angle="data",
    )
    assert res_no_q.debate_catalyst == ""
    assert not res_no_q.reply_text.endswith("?")


# =========================================================================
# 2. NO Forced Question Mark ('?') & Natural Length Tests
# =========================================================================

@pytest.mark.asyncio
async def test_generate_sniper_reply_no_forced_question_structured_parse(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that structured parse does NOT force '?' onto declarative replies."""
    mock_result = SniperResult(
        response_mode="punchy_one_liner",
        reply_text="masahide fujii returning as rocks is pure cinema.",
        debate_catalyst="",
        angle="witty",
        confidence=0.95,
        reasoning="Punchy hype reaction.",
    )

    mock_parsed_choice = MagicMock()
    mock_parsed_choice.message = MagicMock(parsed=mock_result)
    mock_parse_response = MagicMock(choices=[mock_parsed_choice])

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = mock_parse_response

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        preferred_angle="witty",
        client=mock_client,
    )

    assert isinstance(result, SniperResult)
    assert result.reply_text == "masahide fujii returning as rocks is pure cinema."
    assert not result.reply_text.endswith("?")
    assert result.response_mode == "punchy_one_liner"


@pytest.mark.asyncio
async def test_generate_sniper_reply_no_forced_question_json_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that JSON fallback does NOT force '?' onto replies."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse unsupported")

    json_payload = {
        "response_mode": "casual_take",
        "reply_text": "The M4 Max efficiency gap is actually absurd. Intel needs a miracle!",
        "debate_catalyst": "",
        "angle": "insight",
        "confidence": 0.92,
        "reasoning": "Clear opinion delivered with conviction.",
    }

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        client=mock_client,
    )

    assert result.reply_text == "The M4 Max efficiency gap is actually absurd. Intel needs a miracle!"
    assert not result.reply_text.endswith("?")
    assert result.response_mode == "casual_take"


@pytest.mark.asyncio
async def test_generate_sniper_reply_no_forced_question_raw_text_fallback(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that raw text fallback does NOT force '?' onto replies."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    raw_text = 'Compute scaling is only half the equation; thermal density at datacenter scale will be the true cap.'
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=raw_text)
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=sample_tweet,
        client=mock_client,
    )

    assert isinstance(result, SniperResult)
    assert result.reply_text == "Compute scaling is only half the equation; thermal density at datacenter scale will be the true cap."
    assert not result.reply_text.endswith("?")


@pytest.mark.asyncio
async def test_generate_sniper_reply_short_replies_accepted(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests that short replies (<40 chars) like 'real', '💀', 'pure cinema' are accepted."""
    short_samples = [
        ("pure_gif", "real", "side eye"),
        ("emoji_reaction", "💀", None),
        ("punchy_one_liner", "ok i agree", None),
        ("punchy_one_liner", "pure cinema 😭", None),
    ]

    for mode, text, gif in short_samples:
        mock_client = AsyncMock()
        mock_result = SniperResult(
            response_mode=mode,
            reply_text=text,
            gif_query=gif,
            angle="witty",
            confidence=0.95,
            reasoning="Short room reaction.",
        )
        mock_choice = MagicMock()
        mock_choice.message = MagicMock(parsed=mock_result)
        mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

        result = await generate_sniper_reply(
            persona=sample_persona,
            target_tweet=sample_tweet,
            client=mock_client,
        )

        assert result.reply_text == text
        assert result.response_mode == mode
        assert not result.reply_text.endswith("?")


# =========================================================================
# 3. Context Injection Tests (Top Comments & Media Alts)
# =========================================================================

def test_build_sniper_user_prompt_context_injection() -> None:
    """Tests that top_comments (with author + likes) and media_alts are formatted into user prompt."""
    target_tweet = {
        "author": "ylecun",
        "text": "Autoregressive LLMs cannot achieve AGI because they lack world models.",
        "top_comments": [
            {"author": "sama", "text": "scaling compute has worked so far", "likes": 1420},
            {"author": "karpathy", "text": "transformers are better than you think", "likes": 890},
            "just train it more bro",
        ],
        "media_alts": [
            "Architecture diagram comparing JEPA world models with autoregressive token prediction",
        ],
    }

    prompt = _build_sniper_user_prompt(target_tweet, preferred_angle="contrarian")

    # Author and tweet content
    assert "@ylecun" in prompt
    assert "Autoregressive LLMs cannot achieve AGI" in prompt

    # Top comments with author and likes
    assert "TOP COMMENTS IN THREAD" in prompt
    assert "@sama:" in prompt
    assert "scaling compute has worked so far" in prompt
    assert "(1420 likes)" in prompt
    assert "@karpathy:" in prompt
    assert "(890 likes)" in prompt
    assert "just train it more bro" in prompt

    # Media alts
    assert "ATTACHED IMAGE VISUAL DESCRIPTIONS" in prompt
    assert "Architecture diagram comparing JEPA" in prompt

    # Response modes instruction
    assert "response_mode" in prompt
    assert "pure_gif" in prompt or "witty_sarcasm" in prompt


def test_build_sniper_system_prompt_6_modalities(sample_persona: Persona) -> None:
    """Tests that system prompt includes 6 dynamic reply modalities and anti-cliché rules."""
    sys_prompt = _build_sniper_system_prompt(sample_persona)

    assert "pure_gif" in sys_prompt
    assert "emoji_reaction" in sys_prompt
    assert "punchy_one_liner" in sys_prompt
    assert "witty_sarcasm" in sys_prompt
    assert "casual_take" in sys_prompt
    assert "in_depth_breakdown" in sys_prompt
    assert "NO FORCED QUESTIONS" in sys_prompt or "NO forced" in sys_prompt or "DO NOT force" in sys_prompt


# =========================================================================
# 4. Verification & Safety Filter Tests
# =========================================================================

def test_verify_sniper_reply_short_and_pure_gif() -> None:
    """Tests verify_sniper_reply accepts short replies, emoji reactions, and GIF queries."""
    ok1, reason1 = verify_sniper_reply("real", response_mode="pure_gif", gif_query="side eye")
    assert ok1 is True
    assert reason1 is None

    ok2, reason2 = verify_sniper_reply("💀", response_mode="emoji_reaction")
    assert ok2 is True
    assert reason2 is None

    ok3, reason3 = verify_sniper_reply("ok i agree", response_mode="punchy_one_liner")
    assert ok3 is True
    assert reason3 is None


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


def test_verify_sniper_reply_banned_cliches() -> None:
    """Tests that verify_sniper_reply rejects banned AI clichés and bot praise."""
    ok1, reason1 = verify_sniper_reply("Let us delve into the architecture of modern transformers.")
    assert ok1 is False
    assert "delve" in reason1

    ok2, reason2 = verify_sniper_reply("This benchmark is a testament to the efficiency of ARM silicon.")
    assert ok2 is False
    assert "testament" in reason2

    ok3, reason3 = verify_sniper_reply("We are witnessing a rich tapestry of neural network advances.")
    assert ok3 is False
    assert "tapestry" in reason3

    ok4, reason4 = verify_sniper_reply("This tool will supercharge your developer productivity.")
    assert ok4 is False
    assert "supercharge" in reason4

    ok5, reason5 = verify_sniper_reply("Great post! This is really helpful for beginners.")
    assert ok5 is False
    assert "generic bot praise" in reason5

    ok6, reason6 = verify_sniper_reply("Compute scaling is accelerating. What do you think?")
    assert ok6 is False
    assert "robotic survey question" in reason6


# =========================================================================
# 5. Multimodal & Opportunity Score Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_generate_sniper_reply_multimodal_vision(sample_persona: Persona) -> None:
    """Tests that attached images generate multimodal vision user content."""
    image_tweet = {
        "author": "TechReviewer",
        "text": "Check out this leaked benchmark chart",
        "top_comments": ["Looks insane", "Fake chart"],
        "media_urls": ["https://pbs.twimg.com/media/leak_chart.jpg"],
        "media_alts": ["Geekbench 6 multi-core comparison between M4 and Snapdragon X Elite"],
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(
        content=json.dumps({
            "response_mode": "witty_sarcasm",
            "reply_text": "Snapdragon closing the efficiency gap on multi-core is huge, but memory bandwidth remains behind.",
            "debate_catalyst": "",
            "angle": "insight",
            "confidence": 0.95,
            "reasoning": "Analyzed benchmark chart",
        })
    )
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_sniper_reply(
        persona=sample_persona,
        target_tweet=image_tweet,
        client=mock_client,
    )

    assert "Snapdragon" in result.reply_text
    assert not result.reply_text.endswith("?")
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


@pytest.mark.asyncio
async def test_generate_sniper_reply_with_growth_opportunity_score(
    sample_persona: Persona, sample_tweet: dict
) -> None:
    """Tests integrating OpportunityScore from growth_scorer with sniper reply generation."""
    opp_score = score_tweet_opportunity(sample_tweet)
    assert isinstance(opp_score, OpportunityScore)

    mock_result = SniperResult(
        response_mode="in_depth_breakdown",
        reply_text="Compute scaling is bound by physics at wafer scale; interconnect latency dominates past 10k GPUs.",
        debate_catalyst="",
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
    assert result.response_mode == "in_depth_breakdown"
    assert not result.reply_text.endswith("?")


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




