from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from pydantic import ValidationError

from xbot.ai.poll_generator import (
    GeneratedPoll,
    generate_poll,
    _clean_text_for_json,
    _parse_poll_from_json,
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
            always=["provide actionable technical insights", "keep polls engaging"],
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


def test_generated_poll_model_validation() -> None:
    """Tests Pydantic validation and option constraints on GeneratedPoll."""
    poll = GeneratedPoll(
        question="Which database bottleneck causes the most production outages?",
        options=["Index bloat", "Replication lag", "Connection spikes", "Lock contention"],
        duration_days=2,
        context_hook="Scaling PostgreSQL under heavy write loads is brutal.",
        reasoning="Sparks debate among backend engineers.",
    )
    assert poll.question == "Which database bottleneck causes the most production outages?"
    assert len(poll.options) == 4
    assert poll.duration_days == 2
    assert poll.context_hook == "Scaling PostgreSQL under heavy write loads is brutal."

    # Test option length truncation (<= 25 chars)
    poll_long_options = GeneratedPoll(
        question="What is the biggest architecture mistake?",
        options=[
            "Premature microservices migration",  # 34 chars -> should be truncated to 25
            "Not using database indexing",        # 27 chars -> should be truncated to 25
        ],
    )
    for opt in poll_long_options.options:
        assert len(opt) <= 25
    assert poll_long_options.options[0] == "Premature microservices m"
    assert poll_long_options.options[1] == "Not using database indexi"

    # Test fewer than 2 options raises ValidationError
    with pytest.raises(ValidationError):
        GeneratedPoll(
            question="Is Rust better than Go?",
            options=["Yes, absolutely"],
        )

    # Test more than 4 options raises ValidationError
    with pytest.raises(ValidationError):
        GeneratedPoll(
            question="Pick one favorite language:",
            options=["Rust", "Go", "Python", "TypeScript", "C++"],
        )

    # Test duration_days bounds (1 to 7)
    with pytest.raises(ValidationError):
        GeneratedPoll(
            question="Quick poll:",
            options=["Option A", "Option B"],
            duration_days=0,
        )

    with pytest.raises(ValidationError):
        GeneratedPoll(
            question="Quick poll:",
            options=["Option A", "Option B"],
            duration_days=8,
        )

    # Test question length (> 200 chars raises ValidationError)
    with pytest.raises(ValidationError):
        GeneratedPoll(
            question="Q" * 201,
            options=["Option A", "Option B"],
        )


def test_clean_text_for_json() -> None:
    """Tests removing markdown code fences."""
    raw = "```json\n{\"question\": \"Test?\", \"options\": [\"A\", \"B\"]}\n```"
    cleaned = _clean_text_for_json(raw)
    assert cleaned == "{\"question\": \"Test?\", \"options\": [\"A\", \"B\"]}"


def test_parse_poll_from_json() -> None:
    """Tests parsing poll from various JSON structures."""
    # Standard dict
    raw = json.dumps({
        "question": "Postgres vs SQLite for edge apps?",
        "options": ["Postgres", "SQLite", "Neither"],
        "duration_days": 3,
        "context_hook": "Edge computing debate:",
        "reasoning": "Drives engagement on edge DB trade-offs.",
    })
    poll = _parse_poll_from_json(raw)
    assert poll is not None
    assert poll.question == "Postgres vs SQLite for edge apps?"
    assert len(poll.options) == 3
    assert poll.duration_days == 3

    # Nested under "poll" key
    nested_raw = json.dumps({
        "poll": {
            "question": "Best caching strategy?",
            "options": ["Cache-aside", "Write-through", "Refresh-ahead", "No cache"],
            "duration_days": 1,
        }
    })
    nested_poll = _parse_poll_from_json(nested_raw)
    assert nested_poll is not None
    assert nested_poll.question == "Best caching strategy?"
    assert len(nested_poll.options) == 4

    # Invalid JSON returns None
    assert _parse_poll_from_json("not valid json at all") is None
    assert _parse_poll_from_json("") is None


@pytest.mark.asyncio
async def test_generate_poll_structured_parse(sample_persona: Persona) -> None:
    """Tests successful structured parse via OpenAI beta endpoint."""
    expected_poll = GeneratedPoll(
        question="Which layer of the stack is most likely to fail under 10x traffic?",
        options=["Database / Storage", "API Gateway", "Third-party APIs", "Message Broker"],
        duration_days=2,
        context_hook="Every architecture breaks under 10x load.",
        reasoning="Triggers architectural debates among senior engineers.",
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=expected_poll)
    mock_response = MagicMock(choices=[mock_choice])

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.return_value = mock_response

    result = await generate_poll(
        persona=sample_persona,
        topic="System Scaling",
        client=mock_client,
    )

    assert isinstance(result, GeneratedPoll)
    assert result.question == expected_poll.question
    assert len(result.options) == 4
    assert result.duration_days == 2
    assert result.context_hook == "Every architecture breaks under 10x load."
    assert mock_client.beta.chat.completions.parse.called

    # Check prompt contains persona context and strict poll constraints
    call_args = mock_client.beta.chat.completions.parse.call_args
    messages = call_args.kwargs.get("messages", [])
    prompt_text = " ".join(m["content"] for m in messages)
    assert "Distributed Dev" in prompt_text
    assert "System Scaling" in prompt_text
    assert "25 characters" in prompt_text or "max 25 chars" in prompt_text
    assert "2 to 4 options" in prompt_text or "2-4 options" in prompt_text


@pytest.mark.asyncio
async def test_generate_poll_json_fallback(sample_persona: Persona) -> None:
    """Tests fallback to chat.completions.create with JSON mode when parse fails."""
    json_payload = {
        "question": "What is the single biggest cause of slow database queries?",
        "options": [
            "Missing indexes",
            "N+1 ORM queries",
            "Huge table bloat",
            "Poor join conditions",
        ],
        "duration_days": 1,
        "context_hook": "Your database is trying to tell you something.",
        "reasoning": "Engages backend developers on common performance pitfalls.",
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Beta parse unsupported")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_poll(
        persona=sample_persona,
        topic="Database Performance",
        client=mock_client,
    )

    assert isinstance(result, GeneratedPoll)
    assert result.question == "What is the single biggest cause of slow database queries?"
    assert len(result.options) == 4
    assert result.options[0] == "Missing indexes"
    assert result.duration_days == 1
    assert result.context_hook == "Your database is trying to tell you something."


@pytest.mark.asyncio
async def test_generate_poll_options_truncation_on_json_fallback(sample_persona: Persona) -> None:
    """Tests that options exceeding 25 characters are safely truncated to 25 chars."""
    json_payload = {
        "question": "Which architecture pattern causes the most tech debt?",
        "options": [
            "Over-engineered Microservices Architecture",  # 42 chars
            "Monolithic Codebase without boundaries",      # 38 chars
            "Serverless Lambda Functions Everywhere",      # 39 chars
        ],
        "duration_days": 1,
        "context_hook": "Tech debt architecture audit:",
        "reasoning": "Heated debate on architectural anti-patterns.",
    }

    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse unsupported")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content=json.dumps(json_payload))
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_poll(
        persona=sample_persona,
        client=mock_client,
    )

    assert isinstance(result, GeneratedPoll)
    assert len(result.options) == 3
    for opt in result.options:
        assert len(opt) <= 25
    assert result.options[0] == "Over-engineered Microserv"
    assert result.options[1] == "Monolithic Codebase witho"
    assert result.options[2] == "Serverless Lambda Functio"


@pytest.mark.asyncio
async def test_generate_poll_api_exception_returns_none(sample_persona: Persona) -> None:
    """Tests that network or API exceptions return None to avoid posting boilerplate fallback."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = ConnectionError("Network down")
    mock_client.chat.completions.create.side_effect = ConnectionError("Network down")

    result = await generate_poll(
        persona=sample_persona,
        topic="Distributed Databases",
        client=mock_client,
    )

    assert result is None


@pytest.mark.asyncio
async def test_generate_poll_invalid_json_returns_none(sample_persona: Persona) -> None:
    """Tests that unparseable JSON response returns None to discard cleanly."""
    mock_client = AsyncMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError("Parse failed")

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(content="Sorry, I cannot generate a poll right now.")
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    result = await generate_poll(
        persona=sample_persona,
        client=mock_client,
    )

    assert result is None


@pytest.mark.asyncio
async def test_generate_poll_default_client_resolution(sample_persona: Persona) -> None:
    """Tests that when client=None, get_ai_client() is called."""
    expected_poll = GeneratedPoll(
        question="Rust or Go for backend microservices in 2026?",
        options=["Rust", "Go", "Both / Depends", "Neither"],
        duration_days=1,
    )

    mock_choice = MagicMock()
    mock_choice.message = MagicMock(parsed=expected_poll)
    mock_response = MagicMock(choices=[mock_choice])

    with patch("xbot.ai.poll_generator.get_ai_client") as mock_get_ai_client:
        mock_client = AsyncMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_ai_client.return_value = mock_client

        res = await generate_poll(
            persona=sample_persona,
        )

        assert res.question == "Rust or Go for backend microservices in 2026?"
        mock_get_ai_client.assert_called_once()
