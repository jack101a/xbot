import datetime
import pytest
from unittest.mock import AsyncMock, patch
from xbot.ai.temporal import (
    TEMPORAL_MARKER,
    get_temporal_anchor,
    inject_temporal_anchor_to_messages,
    inject_temporal_anchor_to_prompt,
)
from xbot.ai.client import RoutingClient


def test_get_temporal_anchor():
    anchor = get_temporal_anchor()
    current_year = str(datetime.datetime.now().year)
    assert TEMPORAL_MARKER in anchor
    assert current_year in anchor
    assert "CRITICAL TEMPORAL RULES" in anchor
    assert "STRICTLY FORBIDDEN to claim or assume the current year is 2023, 2024, or 2025" in anchor


def test_inject_temporal_anchor_with_existing_system_message():
    messages = [
        {"role": "system", "content": "You are an authentic creator."},
        {"role": "user", "content": "What year is it?"},
    ]
    injected = inject_temporal_anchor_to_messages(messages)
    assert len(injected) == 2
    assert injected[0]["role"] == "system"
    assert "You are an authentic creator." in injected[0]["content"]
    assert TEMPORAL_MARKER in injected[0]["content"]
    assert str(datetime.datetime.now().year) in injected[0]["content"]


def test_inject_temporal_anchor_without_system_message():
    messages = [
        {"role": "user", "content": "Give me a tweet about tech trends."},
    ]
    injected = inject_temporal_anchor_to_messages(messages)
    assert len(injected) == 2
    assert injected[0]["role"] == "system"
    assert TEMPORAL_MARKER in injected[0]["content"]
    assert injected[1]["role"] == "user"
    assert injected[1]["content"] == "Give me a tweet about tech trends."


def test_inject_temporal_anchor_idempotent():
    messages = [
        {"role": "system", "content": f"Existing instructions.\n\n{TEMPORAL_MARKER} already here]"},
        {"role": "user", "content": "Hi"},
    ]
    injected = inject_temporal_anchor_to_messages(messages)
    # Count occurrences
    count = injected[0]["content"].count(TEMPORAL_MARKER)
    assert count == 1


def test_inject_temporal_anchor_to_prompt():
    raw_prompt = "Write a post about Harry Potter series."
    anchored = inject_temporal_anchor_to_prompt(raw_prompt)
    assert TEMPORAL_MARKER in anchored
    assert raw_prompt in anchored
    # Repeated call is idempotent
    assert inject_temporal_anchor_to_prompt(anchored) == anchored


@pytest.mark.asyncio
async def test_routing_client_automatically_injects_temporal_anchor():
    client = RoutingClient()
    mock_client = AsyncMock()

    captured_kwargs = {}

    async def side_effect(model, **kwargs):
        captured_kwargs.update(kwargs)
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content="Live take in current year!"))]
        return mock_response

    mock_client.chat.completions.create = side_effect

    with patch.object(RoutingClient.Completions, "_get_provider_client", return_value=mock_client):
        # User makes a call with ONLY a user message
        res = await client.chat.completions.create(
            model="litellm/gemini-3.5-flash",
            messages=[{"role": "user", "content": "What is the newest trailer?"}],
        )
        assert res.choices[0].message.content == "Live take in current year!"

        # Verify that outgoing messages intercepted at _route contain the temporal anchor and current year
        assert "messages" in captured_kwargs
        out_messages = captured_kwargs["messages"]
        assert len(out_messages) >= 2
        system_msg = next((m for m in out_messages if m["role"] == "system"), None)
        assert system_msg is not None
        assert TEMPORAL_MARKER in system_msg["content"]
        assert str(datetime.datetime.now().year) in system_msg["content"]
