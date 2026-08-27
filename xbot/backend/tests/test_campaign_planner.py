"""Unit Tests for CampaignPlanner (AI Director Intent Decomposer)."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from xbot.ai.campaign_planner import (
    DeliverableType,
    DeliverableSpec,
    CampaignPlan,
    plan_campaign_from_prompt,
)
from xbot.persona.loader import (
    Persona,
    Identity,
    Personality,
    WritingStyle,
    Interests,
    Goals,
    Rules,
)


@pytest.fixture
def sample_persona() -> Persona:
    return Persona(
        id="test_persona",
        display_name="Alex Tech",
        x_handle="alex_tech",
        identity=Identity(background="AI engineer and tech commentator"),
        personality=Personality(traits=["witty", "analytical"], communication_style="casual"),
        writing_style=WritingStyle(tone="authentic", typical_length="concise", formatting=[]),
        interests=Interests(primary=["AI", "Tech"], secondary=["Culture"]),
        goals=Goals(primary="Audience growth", secondary="Tech discourse"),
        rules=Rules(hard_rules=["No generic summaries"], soft_rules=[]),
    )


@pytest.mark.asyncio
async def test_plan_campaign_multi_intent_decomposition(sample_persona: Persona):
    """Verifies that a multi-part prompt is decomposed into discrete deliverables."""
    prompt = "build a thread on giva jewellery kriti senon rakshabandhan controversy with multiple media, a thread and some polls on apple upcoming launch event, multiple posts on toxic film"

    mock_client = AsyncMock()
    mock_plan_data = {
        "campaign_title": "Multi-Topic Trend Pack",
        "theme": "Cultural controversies, Apple event hype, and cinema commentary",
        "overall_strategy": "High engagement mix of deep dive threads, interactive polls, and punchy takes.",
        "deliverables": [
            {
                "id": "deliv_1",
                "type": "thread",
                "topic": "GIVA Jewellery Kriti Sanon Rakshabandhan Controversy",
                "search_query": "giva jewellery kriti sanon controversy rakshabandhan",
                "target_media_count": 3,
                "instructions": "Break down the ad backlash, social reaction, and marketing misstep with attached screenshots.",
            },
            {
                "id": "deliv_2",
                "type": "thread",
                "topic": "Apple Upcoming Launch Event Announcements",
                "search_query": "apple event iphone 16 leak announcement",
                "target_media_count": 2,
                "instructions": "Deep dive into expected hardware updates, AI integration, and pricing.",
            },
            {
                "id": "deliv_3",
                "type": "poll",
                "topic": "Apple Event: Day 1 Upgrade vs Waiting",
                "search_query": "apple event upgrade iphone",
                "target_media_count": 0,
                "instructions": "Polarizing dilemma on whether to upgrade immediately or skip.",
            },
            {
                "id": "deliv_4",
                "type": "post",
                "topic": "Toxic Film Teaser & Audience Expectations",
                "search_query": "toxic movie yash teaser reaction",
                "target_media_count": 1,
                "instructions": "Punchy hot take on the cinematic tone and hype.",
            },
        ],
    }

    mock_resp = MagicMock()
    mock_resp.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps(mock_plan_data)
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    plan = await plan_campaign_from_prompt(prompt=prompt, persona=sample_persona, client=mock_client)

    assert isinstance(plan, CampaignPlan)
    assert len(plan.deliverables) == 4
    assert plan.deliverables[0].type == DeliverableType.THREAD
    assert plan.deliverables[0].target_media_count == 3
    assert plan.deliverables[2].type == DeliverableType.POLL
    assert plan.deliverables[3].type == DeliverableType.POST


@pytest.mark.asyncio
async def test_plan_campaign_fallback_on_parse_error(sample_persona: Persona):
    """Verifies that invalid LLM output falls back to a safe single deliverable."""
    prompt = "build a post on quantum computing breakthroughs"

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Invalid non-json string"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    plan = await plan_campaign_from_prompt(prompt=prompt, persona=sample_persona, client=mock_client)

    assert isinstance(plan, CampaignPlan)
    assert len(plan.deliverables) >= 1
    assert "quantum computing" in plan.deliverables[0].topic.lower()
