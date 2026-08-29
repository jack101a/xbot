import pytest
import asyncio
from xbot.ai.fact_grounder import (
    extract_search_query_from_text,
    search_web_grounding,
    ground_context_with_live_facts,
)

def test_extract_search_query():
    text = "🔥 [TRENDING DEBATE/TOPIC]: Anthropic launches Claude 3.7 Sonnet with hybrid reasoning capabilities and benchmark records."
    query = extract_search_query_from_text(text)
    assert "Claude" in query or "Anthropic" in query
    assert "🔥" not in query

@pytest.mark.asyncio
async def test_search_web_grounding_live():
    facts = await search_web_grounding("One Piece manga Oda Jump Festa", max_results=2)
    assert isinstance(facts, list)
    if facts:
        assert "title" in facts[0]
        assert "snippet" in facts[0]

@pytest.mark.asyncio
async def test_ground_context_prompt_block():
    block = await ground_context_with_live_facts("MKBHD reviews Apple M4 Max MacBook Pro battery life", max_results=2)
    assert isinstance(block, str)
    if block:
        assert "Verified Real-Time Web Facts" in block
        assert "Fact-Check & Accuracy Guardrails" in block
