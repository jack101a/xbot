from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from xbot.ai.hook_optimizer import HookCandidate, HookOptimizationResult
from xbot.ai.trend_radar import TrendItem
from xbot.ai.trend_generator import (
    TrendEvaluation,
    _TrendAnalysisResponse,
    _clean_text_for_json,
    _parse_trend_evaluation_from_json,
    generate_trend_take,
)
from xbot.persona.loader import (
    Goals,
    Identity,
    Interests,
    Persona,
    Personality,
    Rules,
    TargetKOL,
    WritingStyle,
)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="systems_architect",
        display_name="Distributed Dev",
        x_handle="@distdev",
        identity=Identity(
            background="Principal engineer specialized in distributed databases and cloud infrastructure.",
            occupation="Principal Systems Architect",
        ),
        personality=Personality(
            traits=["pragmatic", "skeptical", "sharp"],
            values=["reliability", "low-latency", "simplicity"],
            communication_style="Direct, technical, contrarian",
        ),
        interests=Interests(
            primary=["Distributed Systems", "PostgreSQL", "Rust", "Database Performance"],
            secondary=["Linux Kernel", "High-throughput Networking"],
            will_not_discuss=["celebrity gossip", "political drama", "get-rich-quick crypto"],
        ),
        writing_style=WritingStyle(
            tone="sharp, technical, authoritative",
            typical_length="short",
            formatting=["no emojis", "no hashtags"],
            examples=[
                "90% of microservices should have been a well-structured monolith.",
                "Your database isn't slow. Your queries are unindexed.",
            ],
        ),
        goals=Goals(
            short_term=["share systems engineering lessons"],
            long_term=["establish architectural authority"],
            content_pillars=["Database optimization", "System scaling"],
        ),
        rules=Rules(
            always=["provide actionable technical insights", "be concise"],
            never=["use generic AI buzzwords", "say 'Let's dive in'", "use hashtags"],
        ),
        target_kols=[
            TargetKOL(
                handle="sama",
                category="ai",
                priority="high",
                preferred_angle="infrastructure",
            )
        ],
    )


@pytest.fixture
def relevant_trend_item() -> TrendItem:
    return TrendItem(
        id="trend_pg17",
        title="PostgreSQL 17 Released with Major Query Optimization & Memory Management",
        summary="PostgreSQL 17 introduces improved memory management in vacuuming, better query execution for partitioned tables, and SIMD JSON acceleration.",
        source_url="https://www.postgresql.org/about/news/postgres-17-released/",
        source_name="PostgreSQL News",
        published_at="2026-08-18T10:00:00Z",
    )


@pytest.fixture
def irrelevant_trend_item() -> TrendItem:
    return TrendItem(
        id="trend_gossip",
        title="Pop Star Red Carpet Drama at Summer Gala",
        summary="Viral fashion showdown and celebrity feud heats up at the annual gala.",
        source_url="https://celebritynews.example.com/gala-drama",
        source_name="Celebrity Wire",
        published_at="2026-08-18T12:00:00Z",
    )


def test_trend_evaluation_model_validation() -> None:
    """Tests Pydantic validation and field constraints on TrendEvaluation."""
    eval_res = TrendEvaluation(
        is_relevant=True,
        relevance_score=0.92,
        reasoning="Directly aligns with PostgreSQL and database scaling niche.",
        key_takeaways=[
            "Postgres 17 vacuuming memory footprint cut by 2x.",
            "SIMD acceleration for JSON operations.",
        ],
        hot_take="Most teams rebuilding on NoSQL just need Postgres 17 vacuum optimizations.",
        draft_post="Postgres 17 cuts vacuum memory by 2x.\n\nYou probably don't need a new database.",
        optimized_post="Postgres 17 just killed 90% of niche database migrations.\n\nVacuum memory is down 2x.",
    )
    assert eval_res.is_relevant is True
    assert eval_res.relevance_score == 0.92
    assert len(eval_res.key_takeaways) == 2
    assert "vacuum" in eval_res.hot_take

    # Test score bounds (0.0 to 1.0)
    with pytest.raises(ValidationError):
        TrendEvaluation(is_relevant=True, relevance_score=1.5)

    with pytest.raises(ValidationError):
        TrendEvaluation(is_relevant=True, relevance_score=-0.1)

    # Test default values
    minimal = TrendEvaluation(is_relevant=False)
    assert minimal.is_relevant is False
    assert minimal.relevance_score == 0.5
    assert minimal.reasoning == ""
    assert minimal.key_takeaways == []
    assert minimal.hot_take == ""
    assert minimal.draft_post == ""
    assert minimal.optimized_post == ""


def test_clean_text_for_json() -> None:
    """Tests removing markdown code fences from LLM responses."""
    raw = "```json\n{\"is_relevant\": true, \"relevance_score\": 0.85}\n```"
    assert _clean_text_for_json(raw) == "{\"is_relevant\": true, \"relevance_score\": 0.85}"


def test_parse_trend_evaluation_from_json() -> None:
    """Tests parsing trend evaluation from various JSON formats."""
    # Standard dict
    raw = json.dumps({
        "is_relevant": True,
        "relevance_score": 0.88,
        "reasoning": "High alignment with Postgres niche.",
        "key_takeaways": ["Vacuum memory cut 2x", "SIMD JSON query speedup"],
        "hot_take": "Stop over-engineering with vector DBs.",
        "draft_post": "Postgres 17 is out. Benchmark before migrating.",
    })
    parsed = _parse_trend_evaluation_from_json(raw)
    assert parsed is not None
    assert parsed.is_relevant is True
    assert parsed.relevance_score == 0.88
    assert len(parsed.key_takeaways) == 2
    assert parsed.draft_post == "Postgres 17 is out. Benchmark before migrating."

    # Nested under "evaluation" key
    nested_raw = json.dumps({
        "evaluation": {
            "is_relevant": False,
            "relevance_score": 0.1,
            "reasoning": "Celebrity gossip has zero relevance.",
        }
    })
    nested_parsed = _parse_trend_evaluation_from_json(nested_raw)
    assert nested_parsed is not None
    assert nested_parsed.is_relevant is False
    assert nested_parsed.relevance_score == 0.1

    # Invalid JSON returns None
    assert _parse_trend_evaluation_from_json("invalid json string") is None
    assert _parse_trend_evaluation_from_json("") is None


@pytest.mark.asyncio
async def test_generate_trend_take_relevant_structured_parse(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests successful structured parse and hook optimization on relevant trend item."""
    expected_response = _TrendAnalysisResponse(
        is_relevant=True,
        relevance_score=0.95,
        reasoning="Postgres 17 core release matches persona focus on database performance.",
        key_takeaways=[
            "Vacuuming memory footprint reduced up to 20x.",
            "SIMD acceleration for JSON operations.",
            "Improved partitioned query planner.",
        ],
        hot_take="Before you migrate to a boutique database, upgrade to Postgres 17.",
        draft_post="Postgres 17 is out.\n\nVacuum memory down up to 20x.\nBefore migrating, upgrade.",
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=expected_response)
    mock_llm_response = MagicMock(choices=[mock_choice])

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = mock_llm_response

    winning_hook = HookCandidate(
        archetype="contrarian",
        hook_text="Postgres 17 just killed your excuse to migrate databases.",
        score=9.5,
        reasoning="Strong contrarian hook",
    )
    mock_hook_result = HookOptimizationResult(
        original_content=expected_response.draft_post,
        optimized_content=f"{winning_hook.hook_text}\n\nVacuum memory down up to 20x.\nBefore migrating, upgrade.",
        winning_hook=winning_hook,
        candidates=[winning_hook],
    )

    with patch("xbot.ai.trend_generator.optimize_post_hook", new_callable=AsyncMock) as mock_optimize:
        mock_optimize.return_value = mock_hook_result

        result = await generate_trend_take(
            persona=sample_persona,
            trend_item=relevant_trend_item,
            client=mock_client,
        )

        assert isinstance(result, TrendEvaluation)
        assert result.is_relevant is True
        assert result.relevance_score == 0.95
        assert len(result.key_takeaways) == 3
        assert result.hot_take == expected_response.hot_take
        assert result.draft_post == expected_response.draft_post
        assert result.optimized_post == mock_hook_result.optimized_content
        assert mock_optimize.called
        assert mock_optimize.call_args.kwargs.get("topic") == relevant_trend_item.title

        # Check prompt contains persona context
        call_args = mock_client.beta.chat.completions.parse.call_args
        messages = call_args.kwargs.get("messages", [])
        prompt_text = " ".join(m["content"] for m in messages)
        assert "Distributed Dev" in prompt_text
        assert "PostgreSQL 17" in prompt_text


@pytest.mark.asyncio
async def test_generate_trend_take_irrelevant_item(
    sample_persona: Persona,
    irrelevant_trend_item: TrendItem,
) -> None:
    """Tests that irrelevant news items return is_relevant=False and do NOT call hook optimizer."""
    expected_response = _TrendAnalysisResponse(
        is_relevant=False,
        relevance_score=0.05,
        reasoning="Celebrity gossip falls under will_not_discuss and has zero technical relevance.",
        key_takeaways=[],
        hot_take="",
        draft_post="",
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=expected_response)
    mock_llm_response = MagicMock(choices=[mock_choice])

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = mock_llm_response

    with patch("xbot.ai.trend_generator.optimize_post_hook", new_callable=AsyncMock) as mock_optimize:
        result = await generate_trend_take(
            persona=sample_persona,
            trend_item=irrelevant_trend_item,
            client=mock_client,
        )

        assert isinstance(result, TrendEvaluation)
        assert result.is_relevant is False
        assert result.relevance_score == 0.05
        assert result.key_takeaways == []
        assert result.draft_post == ""
        assert result.optimized_post == ""
        assert not mock_optimize.called


@pytest.mark.asyncio
async def test_generate_trend_take_json_fallback(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests fallback to chat.completions.create with JSON mode when structured parse fails."""
    json_payload = {
        "is_relevant": True,
        "relevance_score": 0.85,
        "reasoning": "Postgres performance news aligns with core persona interests.",
        "key_takeaways": [
            "Vacuum speedup in Postgres 17",
            "SIMD acceleration for queries",
        ],
        "hot_take": "Stop rewriting queries into microservices.",
        "draft_post": "Postgres 17 released with 2x vacuum efficiency.\n\nBenchmark before rewriting.",
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Structured parse unsupported")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    winning_hook = HookCandidate(
        archetype="contrarian",
        hook_text="Stop rewriting queries into microservices.",
        score=9.0,
        reasoning="Punchy contrarian line",
    )
    mock_hook_result = HookOptimizationResult(
        original_content=json_payload["draft_post"],
        optimized_content=f"{winning_hook.hook_text}\n\nPostgres 17 released with 2x vacuum efficiency.",
        winning_hook=winning_hook,
        candidates=[winning_hook],
    )

    with patch("xbot.ai.trend_generator.optimize_post_hook", new_callable=AsyncMock) as mock_optimize:
        mock_optimize.return_value = mock_hook_result

        result = await generate_trend_take(
            persona=sample_persona,
            trend_item=relevant_trend_item,
            client=mock_client,
        )

        assert isinstance(result, TrendEvaluation)
        assert result.is_relevant is True
        assert result.relevance_score == 0.85
        assert len(result.key_takeaways) == 2
        assert result.optimized_post == mock_hook_result.optimized_content
        assert mock_optimize.called


@pytest.mark.asyncio
async def test_generate_trend_take_raw_json_fallback(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests fallback to standard chat completions when json_object mode fails."""
    json_payload = {
        "is_relevant": True,
        "relevance_score": 0.78,
        "reasoning": "High technical relevance.",
        "key_takeaways": ["Takeaway 1", "Takeaway 2"],
        "hot_take": "Hot take commentary.",
        "draft_post": "Draft post text.",
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse unsupported")

    # First call with json_object mode fails
    # Second call without json_object mode succeeds
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=f"```json\n{json.dumps(json_payload)}\n```")
    
    mock_client.chat.completions.create.side_effect = [
        RuntimeError("json_object mode unsupported"),
        MagicMock(choices=[mock_choice]),
    ]

    with patch("xbot.ai.trend_generator.optimize_post_hook", new_callable=AsyncMock) as mock_optimize:
        mock_optimize.return_value = HookOptimizationResult(
            original_content="Draft post text.",
            optimized_content="Optimized hook draft.",
            winning_hook=HookCandidate(archetype="curiosity_gap", hook_text="Hook", score=8.0),
            candidates=[],
        )

        result = await generate_trend_take(
            persona=sample_persona,
            trend_item=relevant_trend_item,
            client=mock_client,
        )

        assert isinstance(result, TrendEvaluation)
        assert result.is_relevant is True
        assert result.relevance_score == 0.78


@pytest.mark.asyncio
async def test_generate_trend_take_api_exception_fallback(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests that network or API exceptions return a safe non-relevant fallback TrendEvaluation."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = ConnectionError("Network down")
    mock_client.chat.completions.create.side_effect = ConnectionError("Network down")

    result = await generate_trend_take(
        persona=sample_persona,
        trend_item=relevant_trend_item,
        client=mock_client,
    )

    assert isinstance(result, TrendEvaluation)
    assert result.is_relevant is False
    assert result.relevance_score == 0.0
    assert "network down" in result.reasoning.lower() or "error" in result.reasoning.lower()
    assert result.draft_post == ""
    assert result.optimized_post == ""


@pytest.mark.asyncio
async def test_generate_trend_take_invalid_json_fallback(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests that unparseable LLM output returns a safe non-relevant fallback."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content="I cannot process this news item right now.")
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_trend_take(
        persona=sample_persona,
        trend_item=relevant_trend_item,
        client=mock_client,
    )

    assert isinstance(result, TrendEvaluation)
    assert result.is_relevant is False
    assert result.relevance_score == 0.0
    assert result.draft_post == ""


@pytest.mark.asyncio
async def test_generate_trend_take_enforces_score_threshold(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests that relevance score below 0.65 forces is_relevant=False and skips hook optimization."""
    json_payload = {
        "is_relevant": True,  # LLM says true, but score is low
        "relevance_score": 0.55,  # Below 0.65 threshold
        "reasoning": "Marginally related but weak alignment.",
        "key_takeaways": ["Some point"],
        "hot_take": "Some take",
        "draft_post": "Draft post",
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse unsupported")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    with patch("xbot.ai.trend_generator.optimize_post_hook", new_callable=AsyncMock) as mock_optimize:
        result = await generate_trend_take(
            persona=sample_persona,
            trend_item=relevant_trend_item,
            client=mock_client,
        )

        assert isinstance(result, TrendEvaluation)
        assert result.is_relevant is False
        assert result.relevance_score == 0.55
        assert not mock_optimize.called


@pytest.mark.asyncio
async def test_generate_trend_take_auto_assembles_draft_if_empty(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests that if LLM provides takeaways and hot_take but empty draft_post, it gets auto-assembled."""
    expected_response = _TrendAnalysisResponse(
        is_relevant=True,
        relevance_score=0.9,
        reasoning="Strong database alignment.",
        key_takeaways=["Key point 1", "Key point 2"],
        hot_take="Hot take commentary line.",
        draft_post="",  # Empty draft post from LLM
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=expected_response)
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = MagicMock(choices=[mock_choice])

    with patch("xbot.ai.trend_generator.optimize_post_hook", new_callable=AsyncMock) as mock_optimize:
        mock_optimize.return_value = HookOptimizationResult(
            original_content="assembled",
            optimized_content="Optimized assembled take",
            winning_hook=HookCandidate(archetype="curiosity_gap", hook_text="Hook", score=8.5),
            candidates=[],
        )

        result = await generate_trend_take(
            persona=sample_persona,
            trend_item=relevant_trend_item,
            client=mock_client,
        )

        assert result.is_relevant is True
        assert len(result.draft_post) > 0
        assert "Key point 1" in result.draft_post or "Hot take" in result.draft_post
        assert result.optimized_post == "Optimized assembled take"


@pytest.mark.asyncio
async def test_generate_trend_take_default_client_resolution(
    sample_persona: Persona,
    relevant_trend_item: TrendItem,
) -> None:
    """Tests that get_ai_client is called when client=None."""
    expected_response = _TrendAnalysisResponse(
        is_relevant=False,
        relevance_score=0.2,
        reasoning="Not relevant",
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=expected_response)
    mock_response = MagicMock(choices=[mock_choice])

    with patch("xbot.ai.trend_generator.get_ai_client") as mock_get_ai_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_ai_client.return_value = mock_client

        res = await generate_trend_take(
            persona=sample_persona,
            trend_item=relevant_trend_item,
        )

        assert res.is_relevant is False
        mock_get_ai_client.assert_called_once()
