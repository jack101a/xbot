import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel
from httpx import AsyncClient, ASGITransport

from xbot.ai.client import RoutingClient
from xbot.ai.chatgpt_adapter import ChatGPTBridgeAdapter, ChatGPTBridgeCompletions, _extract_json_payload
from xbot.main import app


class SampleResponse(BaseModel):
    headline: str
    takeaways: list[str]


def test_extract_json_payload():
    raw_markdown = """
    Here is your post:
    ```json
    {
      "headline": "AI Revolution 2026",
      "takeaways": ["Speed", "Autonomy"]
    }
    ```
    Hope this helps!
    """
    data = _extract_json_payload(raw_markdown)
    assert data["headline"] == "AI Revolution 2026"
    assert len(data["takeaways"]) == 2


@pytest.mark.asyncio
async def test_chatgpt_bridge_adapter_create():
    adapter = ChatGPTBridgeAdapter()
    with patch.object(
        ChatGPTBridgeCompletions,
        "_post_prompt",
        new_callable=AsyncMock,
        return_value="This is a high-IQ contrarian post about creator economy.",
    ) as mock_post:
        completion = await adapter.chat.completions.create(
            model="auto",
            messages=[
                {"role": "system", "content": "You are a tech founder."},
                {"role": "user", "content": "Write a viral post."},
            ],
        )

        assert completion.choices[0].message.content == "This is a high-IQ contrarian post about creator economy."
        assert mock_post.called


@pytest.mark.asyncio
async def test_chatgpt_bridge_adapter_parse():
    adapter = ChatGPTBridgeAdapter()
    sample_json = '{"headline": "Frontier AI", "takeaways": ["Reasoning", "Scale"]}'
    with patch.object(
        ChatGPTBridgeCompletions,
        "_post_prompt",
        new_callable=AsyncMock,
        return_value=f"```json\n{sample_json}\n```",
    ) as mock_post:
        completion = await adapter.beta.chat.completions.parse(
            model="auto",
            messages=[{"role": "user", "content": "Generate summary"}],
            response_format=SampleResponse,
        )

        parsed = completion.choices[0].message.parsed
        assert isinstance(parsed, SampleResponse)
        assert parsed.headline == "Frontier AI"
        assert parsed.takeaways == ["Reasoning", "Scale"]
        assert mock_post.called


@pytest.mark.asyncio
async def test_routing_client_chatgpt_cascade_fallback():
    client = RoutingClient()

    with patch.object(
        ChatGPTBridgeCompletions,
        "_post_prompt",
        new_callable=AsyncMock,
        side_effect=RuntimeError("ChatGPT bridge connection refused"),
    ), patch("xbot.ai.client.AsyncOpenAI") as mock_openai_cls:

        # Fallback OpenAI client succeeds
        mock_openai_inst = AsyncMock()
        mock_completion = AsyncMock()
        mock_choice = AsyncMock()
        mock_choice.message.content = "Fallback generated from Gemini Flash."
        mock_completion.choices = [mock_choice]
        mock_openai_inst.chat.completions.create.return_value = mock_completion
        mock_openai_cls.return_value = mock_openai_inst

        result = await client.chat.completions.create(
            model="chatgpt/auto,gemini/gemini-flash-latest",
            messages=[{"role": "user", "content": "Test prompt"}],
        )

        assert result.choices[0].message.content == "Fallback generated from Gemini Flash."


@pytest.mark.asyncio
async def test_api_chatgpt_status_and_test_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test status endpoint
        res = await ac.get("/api/system/chatgpt/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "bridge_url" in data
        assert "online" in data

        # 2. Test live test endpoint (with simulated custom URL)
        test_res = await ac.post("/api/system/chatgpt/test", json={"bridge_url": "http://127.0.0.1:8465"})
        assert test_res.status_code == 200
        test_data = test_res.json()
        assert "status" in test_data
        assert "latency_ms" in test_data
        assert "bridge_url" in test_data

        # 3. Test cookie import legacy stub
        import_res = await ac.post("/api/system/chatgpt/cookies", json={"cookies": "dummy"})
        assert import_res.status_code == 200
        assert import_res.json()["status"] == "success"
