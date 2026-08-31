import pytest
from unittest.mock import AsyncMock, patch
from xbot.ai.client import RoutingClient

@pytest.mark.asyncio
async def test_routing_client_retries_and_fallback():
    client = RoutingClient()
    
    # Mock client where model1 fails 3 times, model2 succeeds
    mock_client = AsyncMock()
    
    call_counts = {"gemini-3.5-flash": 0, "deepseek-v4-pro": 0}
    
    async def side_effect(model, **kwargs):
        call_counts[model] = call_counts.get(model, 0) + 1
        if model == "gemini-3.5-flash":
            raise Exception("503 Service Unavailable / Heavy Traffic")
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content="Success from DeepSeek!"))]
        return mock_response
        
    mock_client.chat.completions.create = side_effect
    
    with patch.object(RoutingClient.Completions, "_get_provider_client", return_value=mock_client):
        # Request with cascade: gemini-3.5-flash -> deepseek-v4-pro
        res = await client.chat.completions.create(
            model="litellm/gemini-3.5-flash,litellm/deepseek-v4-pro",
            messages=[{"role": "user", "content": "Hi"}]
        )
        assert res.choices[0].message.content == "Success from DeepSeek!"
        # Verify gemini was retried 3 times before failing over
        assert call_counts["gemini-3.5-flash"] == 3
        # Verify deepseek was called and succeeded on 1st try
        assert call_counts["deepseek-v4-pro"] == 1


@pytest.mark.asyncio
async def test_routing_client_three_tier_cascade():
    client = RoutingClient()
    mock_client = AsyncMock()

    call_counts = {"gpt-4o": 0, "gemini-2.5-flash": 0, "deepseek-chat": 0}

    async def side_effect(model, **kwargs):
        call_counts[model] = call_counts.get(model, 0) + 1
        if model == "gpt-4o":
            raise Exception("429 Rate limit exceeded")
        elif model == "gemini-2.5-flash":
            raise Exception("500 Internal Server Error")
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content="Success from 3rd Tier DeepSeek!"))]
        return mock_response

    mock_client.chat.completions.create = side_effect

    with patch.object(RoutingClient.Completions, "_get_provider_client", return_value=mock_client):
        # 3-Tier Cascade: Tier 1 (gpt-4o) -> Tier 2 (gemini-2.5-flash) -> Tier 3 (deepseek-chat)
        res = await client.chat.completions.create(
            model="chatgpt/gpt-4o,gemini/gemini-2.5-flash,deepseek/deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}]
        )
        assert res.choices[0].message.content == "Success from 3rd Tier DeepSeek!"
        assert call_counts["gpt-4o"] == 3
        assert call_counts["gemini-2.5-flash"] == 3
        assert call_counts["deepseek-chat"] == 1

