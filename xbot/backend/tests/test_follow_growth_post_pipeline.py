import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.ai.growth_post_generator import (
    GROWTH_ARCHETYPES,
    generate_fallback_growth_post,
    generate_growth_post_spec,
    generate_growth_post_with_image,
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


def test_generate_fallback_growth_post():
    """Verifies deterministic fallback generation across all archetypes."""
    for arch in GROWTH_ARCHETYPES:
        spec = generate_fallback_growth_post(archetype=arch)
        assert spec.archetype == arch
        assert len(spec.tweet_copy) > 10
        assert len(spec.image_prompt) > 10
        assert spec.aspect_ratio == "4:5"
        assert spec.cta_type in ["drop_handle", "drop_hello", "say_hi", "active_check"]


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

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_mgr.get_context = AsyncMock(return_value=mock_context)

        with patch("xbot.pipelines.follow_growth_post_pipeline.generate_growth_post_with_image") as mock_gen_img, \
             patch("xbot.pipelines.follow_growth_post_pipeline.ComposePost.execute", new_callable=AsyncMock) as mock_compose:

            spec = generate_fallback_growth_post(archetype="GLOBAL_MUTUALS_CONNECT")
            mock_gen_img.return_value = (spec, "/home/ubuntu/projects/xbot/data/media/mock_growth.png")
            mock_compose.return_value = True

            result = await run_follow_growth_post_for_profile(
                db=in_memory_db,
                profile=test_profile,
                guard=mock_guard,
                manager=mock_mgr,
            )

            assert result["status"] == "success"
            assert result["post_published"] is True
            assert result["post_id"] is not None

            # Verify DB content record
            content = await in_memory_db.get(Content, uuid.UUID(result["post_id"]))
            assert content is not None
            assert content.status == ContentStatus.POSTED
            assert content.ai_metadata["media_urls"] == ["/home/ubuntu/projects/xbot/data/media/mock_growth.png"]
