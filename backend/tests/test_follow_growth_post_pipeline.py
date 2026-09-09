import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.growth_post_generator import (
    GROWTH_ARCHETYPES,
    compute_next_milestone,
    enforce_hashtag_count,
    generate_growth_post_spec,
    generate_growth_post_with_image,
    sanitize_growth_image_prompt,
)
from xbot.models.base import Base
import xbot.models  # Register all models on Base.metadata
from xbot.models.content import Content, ContentStatus
from xbot.models.follow_growth import FollowCandidate, FollowRelationship
from xbot.models.profile import Profile, ProfileStatus
from xbot.persona.loader import Persona
from xbot.pipelines.central_guard import CentralGuard
from xbot.pipelines.follow_growth_post_pipeline import run_follow_growth_post_for_profile

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_generate_growth_post_failure_returns_none():
    """Verifies that growth post generation returns None on API error instead of boilerplate."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API connection dropped")
    spec = await generate_growth_post_spec(client=mock_client)
    assert spec is None


@pytest.mark.asyncio
async def test_generate_growth_post_spec_llm():
    """Verifies LLM-powered growth post generation and parsing."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
      "tweet_copy": "We are global creators building in public. Drop your handle below to connect! 🤝🔥",
      "image_prompt": "3D golden checkmark on dark slate background",
      "aspect_ratio": "4:5",
      "archetype": "GLOBAL_MUTUALS_CONNECT",
      "cta_type": "drop_handle"
    }
    """
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    spec = await generate_growth_post_spec(client=mock_client)
    assert spec.archetype == "GLOBAL_MUTUALS_CONNECT"
    assert "Drop your handle" in spec.tweet_copy
    assert spec.aspect_ratio == "4:5"


@pytest.mark.asyncio
async def test_run_follow_growth_post_for_profile_flow():
    """Verifies the complete execution of the hourly follow growth post pipeline."""
    await _reset_db()
    async with TestingSessionLocal() as in_memory_db:
        # 1. Setup profile
        test_profile = Profile(
            id=uuid.uuid4(),
            profile_slug="test_creator",
            x_handle="@test_creator",
            display_name="Test Creator",
            status=ProfileStatus.ACTIVE,
        )
        in_memory_db.add(test_profile)
        await in_memory_db.commit()

        # 2. Mocks
        mock_guard = MagicMock(spec=CentralGuard)
        mock_guard.can_act = AsyncMock(return_value=True)

        mock_mgr = MagicMock()
        mock_mgr.acquire_lock = MagicMock(return_value=True)
        mock_mgr.release_lock = MagicMock()

        mock_page = MagicMock()
        mock_page.set_default_timeout = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.query_selector_all = AsyncMock(return_value=[])

        from xbot.container import Container
        from xbot.contracts.browser import ActionResult, BrowserActionType, BrowserResponse

        mock_browser = AsyncMock()
        mock_browser.execute.return_value = BrowserResponse(
            status="success",
            action=BrowserActionType.POST,
            action_result=ActionResult(status="success", url="https://x.com/status/123"),
        )
        container = Container(browser=mock_browser, llm=AsyncMock(), guard=mock_guard)

        with patch("xbot.pipelines.follow_growth_post_pipeline.generate_growth_post_with_image") as mock_gen_img:
            from xbot.ai.growth_post_generator import GrowthPostResult
            spec = GrowthPostResult(
                tweet_copy="We are global creators building in public. Drop your handle below to connect! 🤝🔥",
                image_prompt="3D golden checkmark on dark slate background",
                aspect_ratio="4:5",
                archetype="GLOBAL_MUTUALS_CONNECT",
                cta_type="drop_handle",
            )
            mock_gen_img.return_value = (spec, "/home/ubuntu/projects/xbot/data/media/mock_growth.png")

            result = await run_follow_growth_post_for_profile(
                db=in_memory_db,
                profile=test_profile,
                guard=mock_guard,
                container=container,
            )

            assert result["status"] == "success"
            assert result["post_published"] is True
            assert result["post_id"] is not None

            # Verify DB content record
            content = await in_memory_db.get(Content, uuid.UUID(result["post_id"]))
            assert content is not None
            assert content.status == ContentStatus.POSTED
            assert content.ai_metadata["media_urls"] == ["/home/ubuntu/projects/xbot/data/media/mock_growth.png"]


def test_compute_next_milestone():
    assert compute_next_milestone(0) == 500
    assert compute_next_milestone(250) == 500
    assert compute_next_milestone(500) == 1000
    assert compute_next_milestone(750) == 1000
    assert compute_next_milestone(1200) == 2500
    assert compute_next_milestone(3000) == 5000
    assert compute_next_milestone(6500) == 10000
    assert compute_next_milestone(12000) == 15000


def test_enforce_hashtag_count_zero():
    raw_text = "Building the future in public! #BuildInPublic #Tech #F4F"
    result = enforce_hashtag_count(raw_text, target_count=0)
    assert "#" not in result
    assert "Building the future in public!" in result


def test_enforce_hashtag_count_one_or_two():
    raw_text = "Connecting with fellow creators today. Drop your current stack."
    res_one = enforce_hashtag_count(raw_text, target_count=1)
    assert res_one.count("#") == 1
    assert any(tag.lower() in res_one.lower() for tag in ["#f4f", "#500followers", "follow", "#mutuals"])

    res_two = enforce_hashtag_count(raw_text, target_count=2)
    assert res_two.count("#") == 2


def test_enforce_growth_hashtags_prioritized():
    raw_text = "Let's grow together! #f4f #followforfollow #500followers"
    res = enforce_hashtag_count(raw_text, target_count=1)
    assert "#f4f" in res.lower()
    assert res.count("#") == 1

    res_two = enforce_hashtag_count(raw_text, target_count=2)
    assert res_two.count("#") == 2


def test_sanitize_growth_image_prompt_strips_humans_and_cinematic():
    bad_prompt = "A photorealistic young woman smiling at camera in a cinematic film still with moody film grain"
    sanitized = sanitize_growth_image_prompt(bad_prompt, include_milestone=False)

    assert "young woman" not in sanitized.lower()
    assert "photorealistic" not in sanitized.lower()
    assert "cinematic film still" not in sanitized.lower()
    assert "moody film grain" not in sanitized.lower()
    assert "zero people, zero human faces" in sanitized.lower()
    assert "no realistic humans" in sanitized.lower()


def test_sanitize_growth_image_prompt_milestone_badge():
    bad_prompt = "A man standing"
    sanitized = sanitize_growth_image_prompt(bad_prompt, include_milestone=True, milestone_num=750)
    assert "750" in sanitized
    assert "milestone badge" in sanitized
    assert "zero people, zero human faces" in sanitized.lower()
