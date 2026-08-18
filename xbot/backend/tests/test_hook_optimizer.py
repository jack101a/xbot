from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from xbot.ai.hook_optimizer import (
    HookCandidate,
    HookOptimizationResult,
    optimize_post_hook,
    format_optimized_post,
    clean_hook_text,
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
        id="tech_lead",
        display_name="Distributed Dev",
        x_handle="@distdev",
        identity=Identity(
            background="Principal engineer specialized in distributed databases and cloud infrastructure.",
            occupation="Principal Engineer",
        ),
        personality=Personality(
            traits=["pragmatic", "skeptical", "sharp"],
            values=["efficiency", "reliability"],
            communication_style="Direct, actionable, no-nonsense",
        ),
        interests=Interests(
            primary=["Distributed Systems", "PostgreSQL", "Rust"],
            secondary=["Cloud Architecture"],
            will_not_discuss=["partisan politics", "crypto schemes"],
        ),
        writing_style=WritingStyle(
            tone="sharp, technical, insightful",
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
            always=["provide actionable technical insights", "keep hooks under 140 chars"],
            never=["use generic AI buzzwords", "say 'Let's dive in'", "use hashtags"],
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


def test_hook_candidate_model_validation() -> None:
    """Tests Pydantic validation on HookCandidate."""
    candidate = HookCandidate(
        archetype="contrarian",
        hook_text="Microservices didn't solve your scaling problem; they multiplied your network latency.",
        score=9.2,
        reasoning="Strong contrarian take against industry consensus.",
    )
    assert candidate.archetype == "contrarian"
    assert candidate.score == 9.2
    assert "scaling problem" in candidate.hook_text

    # Invalid archetype should raise ValidationError
    with pytest.raises(ValidationError):
        HookCandidate(
            archetype="invalid_archetype",  # type: ignore[arg-type]
            hook_text="Some hook",
            score=7.0,
        )

    # Score out of bounds (< 1.0 or > 10.0) should raise ValidationError
    with pytest.raises(ValidationError):
        HookCandidate(
            archetype="curiosity_gap",
            hook_text="Some hook",
            score=11.0,
        )

    with pytest.raises(ValidationError):
        HookCandidate(
            archetype="curiosity_gap",
            hook_text="Some hook",
            score=0.5,
        )


def test_clean_hook_text() -> None:
    """Tests cleaning archetype prefixes and long strings."""
    assert clean_hook_text('Contrarian: "Postgres is great."') == "Postgres is great."
    assert clean_hook_text('curiosity_gap: The secret is simple.') == "The secret is simple."
    assert clean_hook_text('Story-Relatable: We crashed prod.') == "We crashed prod."
    long_text = "A" * 200
    cleaned = clean_hook_text(long_text)
    assert len(cleaned) <= 140


def test_format_optimized_post_body_preservation() -> None:
    """Tests body preservation and micro-spacing in format_optimized_post."""
    draft = (
        "Most developers don't understand caching.\n\n"
        "Here are the 3 biggest mistakes:\n"
        "1. Setting TTL too long\n"
        "2. No cache invalidation strategy\n"
        "3. Not monitoring hit ratios"
    )
    new_hook = "Your Redis cluster is a band-aid covering terrible SQL queries."
    
    formatted = format_optimized_post(draft, new_hook)
    assert formatted.startswith(new_hook)
    assert "Here are the 3 biggest mistakes:" in formatted
    assert "1. Setting TTL too long" in formatted
    assert "3. Not monitoring hit ratios" in formatted
    assert "Most developers don't understand caching." not in formatted


def test_format_optimized_post_single_line() -> None:
    """Tests format_optimized_post with a single line draft."""
    draft = "Why is Kafka so fast?"
    new_hook = "Kafka's sequential disk I/O beats random memory access every time."
    formatted = format_optimized_post(draft, new_hook)
    assert formatted == new_hook


@pytest.mark.asyncio
async def test_optimize_post_hook_structured_parse(sample_persona: Persona) -> None:
    """Tests successful structured parse with 4 archetypes and winning hook selection."""
    draft_content = (
        "Postgres is slow for large scale apps.\n\n"
        "Here is what you should check:\n"
        "- Connection pooling limits\n"
        "- Index bloat\n"
        "- WAL buffer configuration"
    )

    candidates = [
        HookCandidate(
            archetype="curiosity_gap",
            hook_text="The hidden Postgres config setting that quietly triples query throughput.",
            score=8.4,
            reasoning="Creates curiosity around a specific config parameter.",
        ),
        HookCandidate(
            archetype="contrarian",
            hook_text="Postgres isn't failing at scale. Your default connection pool is killing it.",
            score=9.5,
            reasoning="Sharp contrarian stance with high viral potential.",
        ),
        HookCandidate(
            archetype="framework_breakdown",
            hook_text="The 3-point Postgres scaling checklist before you spend $50k on new nodes.",
            score=8.8,
            reasoning="Clear value proposition with financial framing.",
        ),
        HookCandidate(
            archetype="story_relatable",
            hook_text="We almost migrated to Cassandra until one query rewrite saved our database.",
            score=7.9,
            reasoning="Authentic engineering war story.",
        ),
    ]

    mock_parsed = MagicMock()
    mock_parsed.candidates = candidates
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=mock_parsed)
    mock_response = MagicMock(choices=[mock_choice])

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response

    result = await optimize_post_hook(
        persona=sample_persona,
        draft_content=draft_content,
        topic="PostgreSQL Performance",
        client=mock_client,
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.original_content == draft_content
    assert len(result.candidates) == 4
    # Highest score candidate should be winning_hook
    assert result.winning_hook.archetype == "contrarian"
    assert result.winning_hook.score == 9.5
    assert result.winning_hook.hook_text == "Postgres isn't failing at scale. Your default connection pool is killing it."
    # Optimized content should combine winning hook with body
    assert result.optimized_content.startswith(result.winning_hook.hook_text)
    assert "- Connection pooling limits" in result.optimized_content
    assert mock_client.beta.chat.completions.parse.called

    # Check prompt contents
    call_args = mock_client.beta.chat.completions.parse.call_args
    messages = call_args.kwargs.get("messages", [])
    prompt_text = " ".join(m["content"] for m in messages)
    assert "curiosity_gap" in prompt_text
    assert "contrarian" in prompt_text
    assert "framework_breakdown" in prompt_text
    assert "story_relatable" in prompt_text
    assert "Let's dive in" in prompt_text  # in forbidden list


@pytest.mark.asyncio
async def test_optimize_post_hook_json_fallback(sample_persona: Persona) -> None:
    """Tests fallback to chat.completions.create with JSON mode when parse fails."""
    draft_content = "Why distributed systems fail.\n\nNetwork partitions happen constantly."

    json_payload = {
        "candidates": [
            {
                "archetype": "curiosity_gap",
                "hook_text": "The one distributed systems law everyone forgets during an outage.",
                "score": 8.0,
                "reasoning": "Open loop on outage cause.",
            },
            {
                "archetype": "contrarian",
                "hook_text": "Your microservices don't have high availability; they have distributed fate-sharing.",
                "score": 9.1,
                "reasoning": "Punchy contrarian truth.",
            },
            {
                "archetype": "framework_breakdown",
                "hook_text": "The 2-step resilience framework for surviving network partitions.",
                "score": 7.5,
                "reasoning": "Concise framework.",
            },
            {
                "archetype": "story_relatable",
                "hook_text": "At 3 AM on Black Friday, a single timeout cascaded into a complete outage.",
                "score": 8.6,
                "reasoning": "High-stakes relatable incident.",
            },
        ]
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse unsupported")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await optimize_post_hook(
        persona=sample_persona,
        draft_content=draft_content,
        client=mock_client,
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.winning_hook.archetype == "contrarian"
    assert result.winning_hook.score == 9.1
    assert "distributed fate-sharing" in result.optimized_content
    assert "Network partitions happen constantly." in result.optimized_content


@pytest.mark.asyncio
async def test_optimize_post_hook_dict_of_archetypes_fallback(sample_persona: Persona) -> None:
    """Tests JSON parsing when returned as a dict keyed by archetype name."""
    draft_content = "Building an index in SQLite.\n\nAlways use WAL mode."

    json_payload = {
        "curiosity_gap": {
            "hook_text": "SQLite handles 100k writes/sec, but only if you flip this one pragma.",
            "score": 8.7,
            "reasoning": "Surprising capability curiosity.",
        },
        "contrarian": {
            "hook_text": "You don't need a dedicated DB server for 95% of internal tools.",
            "score": 8.2,
            "reasoning": "Challenges over-engineering.",
        },
        "framework_breakdown": {
            "hook_text": "The SQLite production hardening guide in 3 pragma commands.",
            "score": 8.9,
            "reasoning": "Ultra-actionable technical guide.",
        },
        "story_relatable": {
            "hook_text": "We replaced a $2,000/mo RDS cluster with SQLite on NVMe and never looked back.",
            "score": 9.4,
            "reasoning": "Real dollar savings story.",
        },
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse unsupported")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await optimize_post_hook(
        persona=sample_persona,
        draft_content=draft_content,
        client=mock_client,
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.winning_hook.archetype == "story_relatable"
    assert result.winning_hook.score == 9.4
    assert "$2,000/mo RDS" in result.optimized_content
    assert "Always use WAL mode." in result.optimized_content


@pytest.mark.asyncio
async def test_optimize_post_hook_api_exception_safe_fallback(sample_persona: Persona) -> None:
    """Tests that LLM network or API exceptions return original content safely."""
    draft_content = "Postgres is great.\n\nUse it for everything."

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = ConnectionError("Connection refused")
    mock_client.chat.completions.create.side_effect = ConnectionError("Connection refused")

    result = await optimize_post_hook(
        persona=sample_persona,
        draft_content=draft_content,
        client=mock_client,
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.original_content == draft_content
    assert result.optimized_content == draft_content
    assert result.winning_hook.score == 5.0
    assert "fallback" in result.winning_hook.reasoning.lower() or "connection refused" in result.winning_hook.reasoning.lower()


@pytest.mark.asyncio
async def test_optimize_post_hook_invalid_json_safe_fallback(sample_persona: Persona) -> None:
    """Tests that invalid JSON response triggers safe fallback returning original content."""
    draft_content = "Kafka vs RabbitMQ.\n\nEvent streaming vs message queueing."

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content="This is completely invalid and not JSON at all.")
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await optimize_post_hook(
        persona=sample_persona,
        draft_content=draft_content,
        client=mock_client,
    )

    assert isinstance(result, HookOptimizationResult)
    assert result.original_content == draft_content
    assert result.optimized_content == draft_content
    assert result.winning_hook.score == 5.0


@pytest.mark.asyncio
async def test_optimize_post_hook_default_client_resolution(sample_persona: Persona) -> None:
    """Tests that when client=None, get_ai_client() is invoked."""
    draft = "Redis caching patterns.\n\nUse cache-aside."
    mock_candidate = HookCandidate(
        archetype="framework_breakdown",
        hook_text="The 3 Redis caching architectures you must know.",
        score=8.5,
        reasoning="Clean framework.",
    )

    mock_parsed = MagicMock(candidates=[mock_candidate])
    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=mock_parsed)
    mock_response = MagicMock(choices=[mock_choice])

    with patch("xbot.ai.hook_optimizer.get_ai_client") as mock_get_ai_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_ai_client.return_value = mock_client

        res = await optimize_post_hook(
            persona=sample_persona,
            draft_content=draft,
        )

        assert res.winning_hook.archetype == "framework_breakdown"
        mock_get_ai_client.assert_called_once()
