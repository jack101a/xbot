from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.async_api import async_playwright

from xbot.browser.actions.sync_profile_action import SyncProfileFromX, _parse_count, _upgrade_avatar_url


AUTHENTICATED_PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Alex Developer (@alexdev) / X</title></head>
<body>
  <div id="react-root">
    <!-- Side navigation indicating logged-in session -->
    <nav>
      <div data-testid="SideNav_AccountSwitcher_Button">
        <span>Alex Developer</span>
      </div>
      <a data-testid="AppTabBar_Profile_Link" href="/alexdev">Profile</a>
    </nav>

    <!-- Main profile column -->
    <main data-testid="primaryColumn">
      <div data-testid="UserName">
        <div>
          <span>Alex Developer</span>
          <svg data-testid="icon-verified" aria-label="Verified account"></svg>
        </div>
        <div><span>@alexdev</span></div>
      </div>

      <div data-testid="UserAvatar-Container-profileUser">
        <img src="https://pbs.twimg.com/profile_images/123456789/avatar_normal.jpg" alt="Alex Developer" />
      </div>

      <div data-testid="UserDescription">
        <span>Building autonomous AI agents & modern web apps.</span>
      </div>

      <div>
        <a href="/alexdev/following">
          <span>420</span> <span>Following</span>
        </a>
        <a href="/alexdev/verified_followers">
          <span>15.4K</span> <span>Followers</span>
        </a>
      </div>
    </main>
  </div>
</body>
</html>
"""

LOGGED_OUT_PROFILE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Tech News (@technews) / X</title></head>
<body>
  <div id="react-root">
    <!-- Logged-out header with login button -->
    <header>
      <a data-testid="loginButton" href="/login">Log in</a>
    </header>

    <main data-testid="primaryColumn">
      <div data-testid="UserName">
        <div><span>Tech News</span></div>
        <div><span>@technews</span></div>
      </div>

      <div data-testid="UserAvatar-Container-profileUser">
        <img src="https://pbs.twimg.com/profile_images/987654321/tech_200x200.png" alt="Tech News" />
      </div>

      <div data-testid="UserDescription">
        <span>Latest breaking news in technology and science.</span>
      </div>

      <div>
        <a href="/technews/following">
          <span>125</span> <span>Following</span>
        </a>
        <a href="/technews/followers">
          <span>1.2M</span> <span>Followers</span>
        </a>
      </div>
    </main>
  </div>
</body>
</html>
"""

CHALLENGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Access Challenge / X</title></head>
<body>
  <div id="challenge-container" data-testid="challenge">
    <h1>Confirm your identity</h1>
    <p>Please enter the verification code sent to your email.</p>
    <input data-testid="confirmation_code" type="text" />
  </div>
</body>
</html>
"""


def test_parse_count_helper() -> None:
    """Tests count parsing helper function across various formats."""
    assert _parse_count("0") == 0
    assert _parse_count("42") == 42
    assert _parse_count("1,234") == 1234
    assert _parse_count("15.4K") == 15400
    assert _parse_count("15K") == 15000
    assert _parse_count("1.2M") == 1200000
    assert _parse_count("2M") == 2000000
    assert _parse_count("10.5B") == 10500000000
    assert _parse_count("  3,450 Followers  ") == 3450
    assert _parse_count("") == 0
    assert _parse_count("invalid") == 0


def test_upgrade_avatar_url_helper() -> None:
    """Tests avatar URL upgrade helper function to 400x400."""
    url1 = "https://pbs.twimg.com/profile_images/12345/photo_normal.jpg"
    assert _upgrade_avatar_url(url1) == "https://pbs.twimg.com/profile_images/12345/photo_400x400.jpg"

    url2 = "https://pbs.twimg.com/profile_images/12345/photo_200x200.png"
    assert _upgrade_avatar_url(url2) == "https://pbs.twimg.com/profile_images/12345/photo_400x400.png"

    url3 = "https://pbs.twimg.com/profile_images/12345/photo_bigger.jpeg"
    assert _upgrade_avatar_url(url3) == "https://pbs.twimg.com/profile_images/12345/photo_400x400.jpeg"

    url4 = "https://pbs.twimg.com/profile_images/12345/photo_mini.jpg"
    assert _upgrade_avatar_url(url4) == "https://pbs.twimg.com/profile_images/12345/photo_400x400.jpg"

    url_already_400 = "https://pbs.twimg.com/profile_images/12345/photo_400x400.jpg"
    assert _upgrade_avatar_url(url_already_400) == url_already_400

    assert _upgrade_avatar_url("") == ""


@pytest.mark.asyncio
async def test_sync_profile_authenticated_success(tmp_path: Path) -> None:
    """Tests extracting profile metrics from an authenticated session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=AUTHENTICATED_PROFILE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = SyncProfileFromX(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            username="@alexdev",
            base_url="https://x.com",
        )

        assert result["status"] == "authenticated"
        assert result["is_authenticated"] is True
        assert result["handle"] == "alexdev"
        assert result["display_name"] == "Alex Developer"
        assert result["avatar_url"] == "https://pbs.twimg.com/profile_images/123456789/avatar_400x400.jpg"
        assert result["followers_count"] == 15400
        assert result["following_count"] == 420
        assert "autonomous AI agents" in result["bio"]
        assert result["is_verified"] is True

        await browser.close()


@pytest.mark.asyncio
async def test_sync_profile_logged_out_success(tmp_path: Path) -> None:
    """Tests extracting profile metrics from a logged-out guest session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=LOGGED_OUT_PROFILE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = SyncProfileFromX(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            username="technews",
            base_url="https://x.com",
        )

        assert result["status"] == "logged_out"
        assert result["is_authenticated"] is False
        assert result["handle"] == "technews"
        assert result["display_name"] == "Tech News"
        assert result["avatar_url"] == "https://pbs.twimg.com/profile_images/987654321/tech_400x400.png"
        assert result["followers_count"] == 1200000
        assert result["following_count"] == 125
        assert "breaking news" in result["bio"]
        assert result["is_verified"] is False

        await browser.close()


@pytest.mark.asyncio
async def test_sync_profile_challenge_detection(tmp_path: Path) -> None:
    """Tests detecting access/login challenge screen."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=CHALLENGE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = SyncProfileFromX(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            username="locked_user",
            base_url="https://x.com",
        )

        assert result["status"] == "challenged"
        assert result["is_authenticated"] is False
        assert result["handle"] == "locked_user"

        await browser.close()


@pytest.mark.asyncio
async def test_sync_profile_navigation_failure_returns_fallback(tmp_path: Path) -> None:
    """Tests that HTTP 404 or network errors return status='failed' and capture screenshot."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=404, content_type="text/html", body="<html><body>Not Found</body></html>")

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()

        action = SyncProfileFromX(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            username="nonexistent_user",
            base_url="https://x.com",
        )

        assert result["status"] == "failed"
        assert result["is_authenticated"] is False
        assert result["handle"] == "nonexistent_user"
        assert result["avatar_url"] == ""
        assert result["followers_count"] == 0

        # Check screenshot was taken
        screenshots = list(tmp_path.glob("*.png"))
        assert len(screenshots) >= 1

        await browser.close()


@pytest.mark.asyncio
async def test_sync_profile_empty_username_returns_failed() -> None:
    """Tests that an empty or whitespace username returns status='failed' immediately."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        action = SyncProfileFromX()
        result = await action.execute(
            page=page,
            username="   @   ",
            base_url="https://x.com",
        )

        assert result["status"] == "failed"
        assert result["is_authenticated"] is False
        assert result["handle"] == ""

        await browser.close()
