import json
import time
from pathlib import Path
import pytest

from xbot.browser.auth import (
    format_storage_state,
    inspect_profile_auth_status,
    parse_cookie_string,
)


def test_format_storage_state_basic() -> None:
    """Test format_storage_state generates standard Playwright storage state structure."""
    auth_token = "test_auth_token_12345"
    ct0 = "test_ct0_67890"

    state = format_storage_state(auth_token=auth_token, ct0=ct0)

    assert "cookies" in state
    assert "origins" in state
    assert isinstance(state["cookies"], list)
    assert len(state["cookies"]) == 4  # 2 for .x.com, 2 for .twitter.com

    # Check auth_token cookies
    auth_cookies = [c for c in state["cookies"] if c["name"] == "auth_token"]
    assert len(auth_cookies) == 2
    domains = {c["domain"] for c in auth_cookies}
    assert domains == {".x.com", ".twitter.com"}
    for c in auth_cookies:
        assert c["value"] == auth_token
        assert c["httpOnly"] is True
        assert c["secure"] is True
        assert c["path"] == "/"
        assert c["sameSite"] in ("None", "Lax")

    # Check ct0 cookies
    ct0_cookies = [c for c in state["cookies"] if c["name"] == "ct0"]
    assert len(ct0_cookies) == 2
    domains = {c["domain"] for c in ct0_cookies}
    assert domains == {".x.com", ".twitter.com"}
    for c in ct0_cookies:
        assert c["value"] == ct0
        assert c["httpOnly"] is False
        assert c["secure"] is True
        assert c["path"] == "/"
        assert c["sameSite"] == "Lax"


def test_format_storage_state_with_twid() -> None:
    """Test format_storage_state includes twid when provided."""
    state = format_storage_state(
        auth_token="auth_123",
        ct0="ct0_456",
        twid="u%3D1234567890",
    )

    twid_cookies = [c for c in state["cookies"] if c["name"] == "twid"]
    assert len(twid_cookies) == 2
    domains = {c["domain"] for c in twid_cookies}
    assert domains == {".x.com", ".twitter.com"}
    for c in twid_cookies:
        assert c["value"] == "u%3D1234567890"
        assert c["secure"] is True


def test_parse_cookie_string_semicolon_header() -> None:
    """Test parsing standard HTTP Cookie header string."""
    raw = "auth_token=abc123; ct0=def456; twid=u%3D12345; guest_id=v1%3A123"
    result = parse_cookie_string(raw)
    assert result == {
        "auth_token": "abc123",
        "ct0": "def456",
        "twid": "u%3D12345",
        "guest_id": "v1%3A123",
    }


def test_parse_cookie_string_with_prefix_and_quotes() -> None:
    """Test parsing Cookie: header with quotes and spaces."""
    raw = 'Cookie: auth_token="abc123"; ct0="def456"'
    result = parse_cookie_string(raw)
    assert result["auth_token"] == "abc123"
    assert result["ct0"] == "def456"


def test_parse_cookie_string_json_array() -> None:
    """Test parsing JSON array format from browser extensions like Cookie-Editor."""
    raw_json = json.dumps([
        {"name": "auth_token", "value": "abc123token", "domain": ".x.com"},
        {"name": "ct0", "value": "def456ct0", "domain": ".x.com"},
        {"name": "twid", "value": "u=999", "domain": ".twitter.com"},
    ])
    result = parse_cookie_string(raw_json)
    assert result == {
        "auth_token": "abc123token",
        "ct0": "def456ct0",
        "twid": "u=999",
    }


def test_parse_cookie_string_json_object() -> None:
    """Test parsing raw JSON object format."""
    raw_json = json.dumps({
        "auth_token": "token_val",
        "ct0": "ct0_val",
    })
    result = parse_cookie_string(raw_json)
    assert result == {
        "auth_token": "token_val",
        "ct0": "ct0_val",
    }


def test_parse_cookie_string_playwright_storage_state() -> None:
    """Test parsing full Playwright storage_state JSON string."""
    raw_state = json.dumps({
        "cookies": [
            {"name": "auth_token", "value": "tok_111", "domain": ".x.com"},
            {"name": "ct0", "value": "ct0_222", "domain": ".x.com"},
        ],
        "origins": [],
    })
    result = parse_cookie_string(raw_state)
    assert result == {
        "auth_token": "tok_111",
        "ct0": "ct0_222",
    }


def test_parse_cookie_string_multiline() -> None:
    """Test parsing multiline newline-separated cookie string."""
    raw = "auth_token=tok123\nct0=ct0123\ntwid=twid123\n"
    result = parse_cookie_string(raw)
    assert result == {
        "auth_token": "tok123",
        "ct0": "ct0123",
        "twid": "twid123",
    }


def test_parse_cookie_string_empty_and_invalid() -> None:
    """Test empty, whitespace, and malformed inputs."""
    assert parse_cookie_string("") == {}
    assert parse_cookie_string("   \n\t ") == {}
    assert parse_cookie_string("this has no key value pairs") == {}


def test_inspect_profile_auth_status_missing(tmp_path: Path) -> None:
    """Test inspect_profile_auth_status when storage_state.json does not exist."""
    profile_dir = tmp_path / "nonexistent_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    status = inspect_profile_auth_status(profile_dir)
    assert status == {
        "has_session_file": False,
        "has_auth_token": False,
        "has_ct0": False,
        "is_configured": False,
        "status": "missing",
        "cookie_count": 0,
        "updated_at": None,
    }


def test_inspect_profile_auth_status_authenticated(tmp_path: Path) -> None:
    """Test inspect_profile_auth_status with valid active storage_state.json."""
    profile_dir = tmp_path / "active_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    state = format_storage_state(auth_token="valid_auth", ct0="valid_ct0")
    state_file = profile_dir / "storage_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)

    status = inspect_profile_auth_status(profile_dir)
    assert status["has_session_file"] is True
    assert status["has_auth_token"] is True
    assert status["has_ct0"] is True
    assert status["is_configured"] is True
    assert status["status"] == "authenticated"
    assert status["cookie_count"] == 4
    assert status["updated_at"] is not None
    assert "T" in status["updated_at"]


def test_inspect_profile_auth_status_partial(tmp_path: Path) -> None:
    """Test inspect_profile_auth_status with only auth_token present."""
    profile_dir = tmp_path / "partial_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "cookies": [
            {"name": "auth_token", "value": "valid_auth", "domain": ".x.com"}
        ],
        "origins": [],
    }
    state_file = profile_dir / "storage_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)

    status = inspect_profile_auth_status(profile_dir)
    assert status["has_session_file"] is True
    assert status["has_auth_token"] is True
    assert status["has_ct0"] is False
    assert status["is_configured"] is False
    assert status["status"] == "partial"
    assert status["cookie_count"] == 1


def test_inspect_profile_auth_status_expired(tmp_path: Path) -> None:
    """Test inspect_profile_auth_status with expired cookies."""
    profile_dir = tmp_path / "expired_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    past_timestamp = time.time() - 3600  # 1 hour ago
    state = {
        "cookies": [
            {
                "name": "auth_token",
                "value": "expired_auth",
                "domain": ".x.com",
                "expires": past_timestamp,
            },
            {
                "name": "ct0",
                "value": "expired_ct0",
                "domain": ".x.com",
                "expires": past_timestamp,
            },
        ],
        "origins": [],
    }
    state_file = profile_dir / "storage_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)

    status = inspect_profile_auth_status(profile_dir)
    assert status["has_session_file"] is True
    assert status["has_auth_token"] is True
    assert status["has_ct0"] is True
    assert status["is_configured"] is False
    assert status["status"] == "expired"
    assert status["cookie_count"] == 2


def test_inspect_profile_auth_status_corrupt_file(tmp_path: Path) -> None:
    """Test inspect_profile_auth_status when storage_state.json is malformed."""
    profile_dir = tmp_path / "corrupt_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    state_file = profile_dir / "storage_state.json"
    state_file.write_text("{ corrupt json ...", encoding="utf-8")

    status = inspect_profile_auth_status(profile_dir)
    assert status["has_session_file"] is True
    assert status["has_auth_token"] is False
    assert status["has_ct0"] is False
    assert status["is_configured"] is False
    assert status["status"] == "missing"
    assert status["cookie_count"] == 0
    assert status["updated_at"] is not None
