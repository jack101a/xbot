import asyncio
import json
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.database import get_db
from xbot.main import app
from xbot.models.analytics import AnalyticsSnapshot
from xbot.models.base import Base
from xbot.models.profile import Profile, ProfileStatus
import xbot.api.profiles as profiles_api
from xbot.browser.auth import format_storage_state

TEST_DATABASE_URL = "sqlite+aiosqlite:///test_auth_api_temp.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


client = TestClient(app)


@pytest.fixture(autouse=True)
def configure_db_override() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None, None, None]:
    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())


async def create_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def temp_profile_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(profiles_api, "BASE_PROFILE_DIR", str(tmp_path))
    return tmp_path


def create_test_profile(slug: str = "test_user", handle: str = "@test_user") -> dict:
    profile_data = {
        "profile_slug": slug,
        "x_handle": handle,
        "display_name": "Test User",
        "status": "active",
        "persona_summary": {"interests": ["AI"]},
        "config": {"schedule": {"sessions_per_day": 3}},
    }
    response = client.post("/api/profiles", json=profile_data)
    assert response.status_code == 201
    return response.json()


# ============================================================================
# 1. GET /{profile_id}/auth-status Tests
# ============================================================================

def test_get_auth_status_not_found() -> None:
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/profiles/{fake_id}/auth-status")
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_get_auth_status_missing_session(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="auth_missing_user", handle="@missing")
    profile_id = profile["id"]

    response = client.get(f"/api/profiles/{profile_id}/auth-status")
    assert response.status_code == 200
    data = response.json()

    assert data["has_session_file"] is False
    assert data["has_auth_token"] is False
    assert data["has_ct0"] is False
    assert data["is_configured"] is False
    assert data["status"] == "missing"
    assert data["cookie_count"] == 0
    assert data["avatar_url"] is None
    assert data["followers_count"] == 0
    assert data["following_count"] == 0


def test_get_auth_status_authenticated(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="auth_valid_user", handle="@valid")
    profile_id = profile["id"]

    # Write a valid storage_state.json in profile directory
    p_dir = temp_profile_dir / "auth_valid_user"
    p_dir.mkdir(parents=True, exist_ok=True)
    state = format_storage_state(auth_token="valid_auth_123", ct0="valid_ct0_456")
    (p_dir / "storage_state.json").write_text(json.dumps(state), encoding="utf-8")

    response = client.get(f"/api/profiles/{profile_id}/auth-status")
    assert response.status_code == 200
    data = response.json()

    assert data["has_session_file"] is True
    assert data["has_auth_token"] is True
    assert data["has_ct0"] is True
    assert data["is_configured"] is True
    assert data["status"] == "authenticated"
    assert data["cookie_count"] >= 2
    assert data["updated_at"] is not None


# ============================================================================
# 2. POST /{profile_id}/import-cookies Tests
# ============================================================================

def test_import_cookies_not_found() -> None:
    fake_id = str(uuid.uuid4())
    payload = {"auth_token": "abc", "ct0": "def"}
    response = client.post(f"/api/profiles/{fake_id}/import-cookies", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_import_cookies_missing_required_fields(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="cookie_fail_user", handle="@cookiefail")
    profile_id = profile["id"]

    # Missing ct0
    response = client.post(
        f"/api/profiles/{profile_id}/import-cookies",
        json={"auth_token": "only_auth_token"},
    )
    assert response.status_code == 400
    assert "Both auth_token and ct0" in response.json()["detail"]

    # Empty payload
    response = client.post(
        f"/api/profiles/{profile_id}/import-cookies",
        json={},
    )
    assert response.status_code == 400


def test_import_cookies_direct_fields_success(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="cookie_direct_user", handle="@direct")
    profile_id = profile["id"]

    payload = {
        "auth_token": "direct_token_12345",
        "ct0": "direct_ct0_67890",
        "twid": "u%3D123456",
    }
    response = client.post(f"/api/profiles/{profile_id}/import-cookies", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "imported successfully" in data["message"].lower()
    assert data["auth_status"]["has_session_file"] is True
    assert data["auth_status"]["has_auth_token"] is True
    assert data["auth_status"]["has_ct0"] is True
    assert data["auth_status"]["status"] == "authenticated"

    # Verify file was written to disk
    state_file = temp_profile_dir / "cookie_direct_user" / "storage_state.json"
    assert state_file.exists()
    disk_content = json.loads(state_file.read_text(encoding="utf-8"))
    assert "cookies" in disk_content
    cookie_names = [c["name"] for c in disk_content["cookies"]]
    assert "auth_token" in cookie_names
    assert "ct0" in cookie_names
    assert "twid" in cookie_names


def test_import_cookies_raw_header_string_success(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="cookie_raw_user", handle="@raw")
    profile_id = profile["id"]

    raw_header = "Cookie: auth_token=raw_tok_999; ct0=raw_ct0_888; twid=u%3D99999"
    payload = {"raw_cookies": raw_header}

    response = client.post(f"/api/profiles/{profile_id}/import-cookies", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["auth_status"]["status"] == "authenticated"

    # Verify storage_state.json on disk
    state_file = temp_profile_dir / "cookie_raw_user" / "storage_state.json"
    assert state_file.exists()
    disk_content = json.loads(state_file.read_text(encoding="utf-8"))
    tokens = {c["name"]: c["value"] for c in disk_content["cookies"]}
    assert tokens["auth_token"] == "raw_tok_999"
    assert tokens["ct0"] == "raw_ct0_888"


# ============================================================================
# 3. POST /{profile_id}/sync-from-x Tests
# ============================================================================

def test_sync_from_x_not_found() -> None:
    fake_id = str(uuid.uuid4())
    response = client.post(f"/api/profiles/{fake_id}/sync-from-x")
    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


def test_sync_from_x_lock_busy(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="sync_busy_user", handle="@busy")
    profile_id = profile["id"]

    with patch("xbot.api.profiles.BrowserManager") as mock_bm_cls:
        mock_bm = MagicMock()
        mock_bm.acquire_lock.return_value = False
        mock_bm_cls.return_value = mock_bm

        response = client.post(f"/api/profiles/{profile_id}/sync-from-x")
        assert response.status_code == 409
        assert "locked or in use" in response.json()["detail"]


def test_sync_from_x_success(temp_profile_dir: Path) -> None:
    profile = create_test_profile(slug="sync_success_user", handle="@syncuser")
    profile_id = profile["id"]

    mock_sync_result = {
        "status": "authenticated",
        "is_authenticated": True,
        "handle": "syncuser",
        "display_name": "Sync User Official",
        "avatar_url": "https://pbs.twimg.com/profile_images/999/avatar_400x400.jpg",
        "followers_count": 12500,
        "following_count": 340,
        "bio": "Official sync user account",
        "is_verified": True,
    }

    with patch("xbot.api.profiles.BrowserManager") as mock_bm_cls, \
         patch("xbot.api.profiles.SyncProfileFromX") as mock_sync_cls:

        mock_bm = MagicMock()
        mock_bm.acquire_lock.return_value = True
        mock_bm.start = AsyncMock()
        mock_bm.stop = AsyncMock()
        mock_bm.release_lock = MagicMock()

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()
        mock_bm.get_context = AsyncMock(return_value=mock_context)
        mock_bm_cls.return_value = mock_bm

        mock_sync_instance = MagicMock()
        mock_sync_instance.execute = AsyncMock(return_value=mock_sync_result)
        mock_sync_cls.return_value = mock_sync_instance

        response = client.post(f"/api/profiles/{profile_id}/sync-from-x")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["sync_data"]["handle"] == "syncuser"
        assert data["sync_data"]["followers_count"] == 12500
        assert data["profile"]["display_name"] == "Sync User Official"
        assert data["profile"]["avatar_url"] == "https://pbs.twimg.com/profile_images/999/avatar_400x400.jpg"
        assert data["profile"]["followers_count"] == 12500
        assert data["profile"]["following_count"] == 340

        # Verify BrowserManager lock was acquired and released
        mock_bm.acquire_lock.assert_called_once_with("sync_success_user", timeout_seconds=120)
        mock_bm.release_lock.assert_called_once_with("sync_success_user")
        mock_bm.stop.assert_called_once()
        mock_context.close.assert_called_once()

        # Verify GET /api/profiles/{id} reflects updated metrics and avatar
        get_res = client.get(f"/api/profiles/{profile_id}")
        assert get_res.status_code == 200
        p_data = get_res.json()
        assert p_data["display_name"] == "Sync User Official"
        assert p_data["avatar_url"] == "https://pbs.twimg.com/profile_images/999/avatar_400x400.jpg"
        assert p_data["followers_count"] == 12500
        assert p_data["following_count"] == 340
