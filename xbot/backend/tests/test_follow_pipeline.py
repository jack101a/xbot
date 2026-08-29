import datetime
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from xbot.models.profile import Profile, ProfileStatus
from xbot.pipelines.follow_pipeline import run_follow_pipeline_for_profile


@pytest.mark.asyncio
async def test_run_follow_pipeline_for_profile_skipped_by_guard():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=False)
    mock_manager = MagicMock()

    res = await run_follow_pipeline_for_profile(mock_db, profile, mock_guard, mock_manager)
    assert res["status"] == "skipped"
    assert res["actions_executed"] == 0


@pytest.mark.asyncio
async def test_run_follow_pipeline_lock_busy():
    mock_db = AsyncMock()
    profile = Profile(
        id=uuid.uuid4(),
        profile_slug="test_slug",
        x_handle="@test_creator",
        status=ProfileStatus.ACTIVE,
    )

    mock_guard = MagicMock()
    mock_guard.can_act = AsyncMock(return_value=True)

    mock_manager = MagicMock()
    mock_manager.acquire_lock.return_value = False

    res = await run_follow_pipeline_for_profile(mock_db, profile, mock_guard, mock_manager)
    assert res["status"] == "skipped"
    assert res["reason"] == "browser_lock_busy"
