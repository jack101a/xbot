import pytest
from httpx import AsyncClient, ASGITransport
from xbot.main import app
from xbot.ai.prompt_logger import log_ai_interaction_async, get_ai_prompt_logs, clear_ai_prompt_logs

@pytest.mark.asyncio
async def test_ai_prompt_logger_lifecycle():
    # 1. Clear logs
    clear_ai_prompt_logs()
    
    # 2. Record mock interactions
    await log_ai_interaction_async(
        messages=[
            {"role": "system", "content": "You are a tech analyst."},
            {"role": "user", "content": "Write a take on AI agents."}
        ],
        response_text="AI agents represent the next computing paradigm.",
        model="auto",
        provider="chatgpt",
        latency_ms=350,
        status="success",
        action_type="post_creation",
        profile_slug="test_profile1",
    )
    
    # 3. Query logs via Python API
    logs = get_ai_prompt_logs(limit=10)
    assert len(logs) >= 1
    top = logs[0]
    assert top["provider"] == "chatgpt"
    assert top["action_type"] == "post_creation"
    assert "You are a tech analyst." in top["system_prompt"]
    assert "Write a take on AI agents." in top["user_prompt"]
    assert "AI agents represent" in top["response"]
    assert top["latency_ms"] == 350

    # 4. Query logs via FastAPI endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/system/ai-logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["count"] >= 1
        assert data["logs"][0]["provider"] == "chatgpt"

        # Search filter
        search_resp = await ac.get("/api/system/ai-logs?q=paradigm")
        assert search_resp.status_code == 200
        assert search_resp.json()["count"] >= 1

        # Delete logs
        del_resp = await ac.delete("/api/system/ai-logs")
        assert del_resp.status_code == 200
        
        # Verify empty
        after_resp = await ac.get("/api/system/ai-logs")
        assert after_resp.json()["count"] == 0
