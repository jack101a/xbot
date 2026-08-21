import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xbot.database import get_db
from xbot.main import app
from xbot.models.base import Base
from xbot.models.profile import ProfileStatus

import xbot.models  # Ensure all models are registered on Base.metadata

# Define test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///test_temp.db"

# Create test engine and session
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency to use test database."""
    async with TestingSessionLocal() as session:
        yield session


# Create synchronous client for FastAPI
client = TestClient(app)


@pytest.fixture(autouse=True)
def configure_db_override() -> Generator[None, None, None]:
    """Configure dependency override for the duration of the test module."""
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None, None, None]:
    """Create all tables before starting test session and drop them after."""
    # Run async schema creation in a synchronous environment
    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())


async def create_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def test_profile_crud_flow() -> None:
    """Test full Profile CRUD API flow."""
    # 1. List profiles (initially empty)
    response = client.get("/api/profiles")
    assert response.status_code == 200
    assert response.json() == []

    # 2. Create profile
    profile_data = {
        "profile_slug": "techie_sarah",
        "x_handle": "@sarahcodes",
        "display_name": "Sarah Chen",
        "status": "active",
        "persona_summary": {"interests": ["Rust", "Distributed Systems"]},
        "config": {"schedule": {"sessions_per_day": 4}},
        "proxy_url_encrypted": "encrypted_proxy_string",
    }
    response = client.post("/api/profiles", json=profile_data)
    assert response.status_code == 201
    created_profile = response.json()
    assert created_profile["profile_slug"] == "techie_sarah"
    assert created_profile["display_name"] == "Sarah Chen"
    profile_id = created_profile["id"]

    # 3. Create profile with duplicate slug (should fail)
    response = client.post("/api/profiles", json=profile_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

    # 4. List profiles again (should have 1)
    response = client.get("/api/profiles")
    assert response.status_code == 200
    profiles = response.json()
    assert len(profiles) == 1
    assert profiles[0]["id"] == profile_id

    # 5. Get profile by ID
    response = client.get(f"/api/profiles/{profile_id}")
    assert response.status_code == 200
    profile = response.json()
    assert profile["profile_slug"] == "techie_sarah"

    # 6. Get non-existent profile (should 404)
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/profiles/{fake_uuid}")
    assert response.status_code == 404

    # 7. Update profile
    update_data = {
        "display_name": "Sarah Chen updated",
        "config": {"schedule": {"sessions_per_day": 5}},
    }
    response = client.put(f"/api/profiles/{profile_id}", json=update_data)
    assert response.status_code == 200
    updated_profile = response.json()
    assert updated_profile["display_name"] == "Sarah Chen updated"
    assert updated_profile["config"] == {"schedule": {"sessions_per_day": 5}}

    # 8. Pause profile
    response = client.post(f"/api/profiles/{profile_id}/pause")
    assert response.status_code == 200
    paused_profile = response.json()
    assert paused_profile["status"] == ProfileStatus.PAUSED

    # 9. Resume profile
    response = client.post(f"/api/profiles/{profile_id}/resume")
    assert response.status_code == 200
    resumed_profile = response.json()
    assert resumed_profile["status"] == ProfileStatus.ACTIVE

    # 10. Delete profile
    response = client.delete(f"/api/profiles/{profile_id}")
    assert response.status_code == 204

    # 11. Verify deletion
    response = client.get(f"/api/profiles/{profile_id}")
    assert response.status_code == 404
