import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel

from xbot.ai.client import RoutingClient
from xbot.ai.chatgpt_adapter import ChatGPTBridgeAdapter, _extract_json_payload


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
    with patch("xbot.ai.chatgpt_adapter.get_chatgpt_instance") as mock_get_inst:
        mock_inst = AsyncMock()
        mock_inst.ask.return_value = {"text": "This is a high-IQ contrarian post about creator economy.", "conversation_id": "c123"}
        mock_get_inst.return_value = mock_inst

        completion = await adapter.chat.completions.create(
            model="auto",
            messages=[
                {"role": "system", "content": "You are a tech founder."},
                {"role": "user", "content": "Write a viral post."},
            ],
        )

        assert completion.choices[0].message.content == "This is a high-IQ contrarian post about creator economy."
        assert mock_inst.ask.called


@pytest.mark.asyncio
async def test_chatgpt_bridge_adapter_parse():
    adapter = ChatGPTBridgeAdapter()
    sample_json = '{"headline": "Frontier AI", "takeaways": ["Reasoning", "Scale"]}'
    with patch("xbot.ai.chatgpt_adapter.get_chatgpt_instance") as mock_get_inst:
        mock_inst = AsyncMock()
        mock_inst.ask.return_value = {"text": f"```json\n{sample_json}\n```", "conversation_id": "c456"}
        mock_get_inst.return_value = mock_inst

        completion = await adapter.beta.chat.completions.parse(
            model="auto",
            messages=[{"role": "user", "content": "Generate summary"}],
            response_format=SampleResponse,
        )

        parsed = completion.choices[0].message.parsed
        assert isinstance(parsed, SampleResponse)
        assert parsed.headline == "Frontier AI"
        assert parsed.takeaways == ["Reasoning", "Scale"]


@pytest.mark.asyncio
async def test_routing_client_chatgpt_cascade_fallback():
    client = RoutingClient()

    with patch("xbot.ai.chatgpt_adapter.get_chatgpt_instance") as mock_get_inst, \
         patch("xbot.ai.client.AsyncOpenAI") as mock_openai_cls:

        # 1. ChatGPT Bridge fails
        mock_chatgpt_inst = AsyncMock()
        mock_chatgpt_inst.ask.side_effect = RuntimeError("Cloudflare session blocked")
        mock_get_inst.return_value = mock_chatgpt_inst

        # 2. Fallback OpenAI client succeeds
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


from httpx import AsyncClient, ASGITransport
from xbot.main import app


@pytest.mark.asyncio
async def test_api_chatgpt_status_and_cookie_import(tmp_path):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test status endpoint
        res = await ac.get("/api/system/chatgpt/status")
        assert res.status_code == 200
        data = res.json()
        assert "status" in data
        assert "has_cookie_file" in data

        # Test cookie import endpoint
        sample_cookies = '[{"name": "__Secure-next-auth.session-token", "value": "mock_token_val", "domain": ".chatgpt.com"}]'
        import_res = await ac.post("/api/system/chatgpt/cookies", json={"cookies": sample_cookies})
        assert import_res.status_code == 200
        import_data = import_res.json()
        assert import_data["status"] == "success"
        assert import_data["cookie_count"] == 1
        assert import_data["has_valid_session_token"] is True
