import pytest
from xbot.ai.thread_generator import generate_thread, _build_fallback_thread
from xbot.ai.anti_ai_gatekeeper import AntiAIGatekeeper


@pytest.mark.asyncio
async def test_fallback_thread_validity() -> None:
    topic = "Autonomous AI Agent State Architecture"
    resp = _build_fallback_thread(topic)
    assert resp.topic == topic
    assert resp.hook_score >= 90
    assert len(resp.tweets) == 4
    assert len(resp.items) == 4
    assert resp.items[0].item_type == "hook"
    assert resp.items[-1].item_type == "closer"

    gatekeeper = AntiAIGatekeeper()
    for tweet in resp.tweets:
        assert len(tweet) <= 280
        val = gatekeeper.validate(tweet)
        assert val.is_valid is True, f"Tweet failed gatekeeper: {val.errors}"


@pytest.mark.asyncio
async def test_generate_thread_structure() -> None:
    topic = "Building Resilient Distributed Systems"
    resp = await generate_thread(topic=topic, num_tweets=4, deep_research=False)
    assert resp.topic is not None
    assert len(resp.tweets) >= 3
    for tweet in resp.tweets:
        assert len(tweet) <= 280
        assert tweet.strip() != ""
