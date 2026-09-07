import pytest
from unittest.mock import AsyncMock
from xbot.ai.thread_generator import generate_thread
from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper


@pytest.mark.asyncio
async def test_thread_generation_failure_returns_none() -> None:
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API connection failure")
    resp = await generate_thread(topic="AI Systems", client=mock_client, deep_research=False)
    assert resp is None


@pytest.mark.asyncio
async def test_generate_thread_structure() -> None:
    topic = "Building Resilient Distributed Systems"
    resp = await generate_thread(topic=topic, num_tweets=4, deep_research=False)
    assert resp.topic is not None
    assert len(resp.tweets) >= 3
    for tweet in resp.tweets:
        assert len(tweet) <= 280
        assert tweet.strip() != ""
