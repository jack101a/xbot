from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.async_api import async_playwright

from xbot.browser.actions.poll_action import CreatePoll


POLL_COMPOSE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Compose Post / X</title></head>
<body>
  <div id="compose-modal">
    <div contenteditable="true" data-testid="tweetTextarea_0" role="textbox" style="min-height: 50px; border: 1px solid #ccc;"></div>
    <button data-testid="pollButton" onclick="openPoll()">Add Poll</button>
    <div id="poll-section" style="display: none; margin-top: 10px;">
      <div data-testid="Choice1">
        <input name="Choice1" type="text" placeholder="Option 1" />
      </div>
      <div data-testid="Choice2">
        <input name="Choice2" type="text" placeholder="Option 2" />
      </div>
      <div id="choice3-wrap" style="display: none;" data-testid="Choice3">
        <input name="Choice3" type="text" placeholder="Option 3" />
      </div>
      <div id="choice4-wrap" style="display: none;" data-testid="Choice4">
        <input name="Choice4" type="text" placeholder="Option 4" />
      </div>
      <button data-testid="addChoice" onclick="addChoice()">Add Choice</button>
    </div>
    <button data-testid="tweetButton" onclick="submitPoll()">Post</button>
  </div>

  <script>
    let pollOpen = false;
    let extraChoices = 0;
    window.__pollSubmitted = false;

    function openPoll() {
      pollOpen = true;
      document.getElementById('poll-section').style.display = 'block';
    }

    function addChoice() {
      if (extraChoices === 0) {
        document.getElementById('choice3-wrap').style.display = 'block';
        extraChoices = 1;
      } else if (extraChoices === 1) {
        document.getElementById('choice4-wrap').style.display = 'block';
        extraChoices = 2;
      }
    }

    function submitPoll() {
      const question = document.querySelector('[data-testid="tweetTextarea_0"]').innerText || document.querySelector('[data-testid="tweetTextarea_0"]').textContent;
      const c1 = document.querySelector('input[name="Choice1"]').value;
      const c2 = document.querySelector('input[name="Choice2"]').value;
      const c3Input = document.querySelector('input[name="Choice3"]');
      const c4Input = document.querySelector('input[name="Choice4"]');
      const c3 = c3Input ? c3Input.value : '';
      const c4 = c4Input ? c4Input.value : '';

      window.__pollSubmitted = {
        question: question.trim(),
        choice1: c1,
        choice2: c2,
        choice3: c3,
        choice4: c4
      };
    }
  </script>
</body>
</html>
"""

HOME_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Home / X</title></head>
<body>
  <div id="sidebar">
    <button data-testid="SideNav_NewTweet_Button" onclick="openComposeModal()">Post</button>
  </div>
  <div id="modal-slot"></div>

  <script>
    function openComposeModal() {
      document.getElementById('modal-slot').innerHTML = `
        <div id="compose-modal">
          <div contenteditable="true" data-testid="tweetTextarea_0" role="textbox" style="min-height: 50px; border: 1px solid #ccc;"></div>
          <button data-testid="pollButton" onclick="openPoll()">Add Poll</button>
          <div id="poll-section" style="display: none;">
            <div data-testid="Choice1"><input name="Choice1" type="text" /></div>
            <div data-testid="Choice2"><input name="Choice2" type="text" /></div>
            <div id="choice3-wrap" style="display: none;" data-testid="Choice3"><input name="Choice3" type="text" /></div>
            <div id="choice4-wrap" style="display: none;" data-testid="Choice4"><input name="Choice4" type="text" /></div>
            <button data-testid="addChoice" onclick="addChoice()">Add Choice</button>
          </div>
          <button data-testid="tweetButton" onclick="submitPoll()">Post</button>
        </div>
      `;
    }

    let extraChoices = 0;
    function openPoll() {
      document.getElementById('poll-section').style.display = 'block';
    }
    function addChoice() {
      if (extraChoices === 0) {
        document.getElementById('choice3-wrap').style.display = 'block';
        extraChoices = 1;
      } else if (extraChoices === 1) {
        document.getElementById('choice4-wrap').style.display = 'block';
        extraChoices = 2;
      }
    }
    function submitPoll() {
      window.__pollSubmitted = true;
    }
  </script>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_create_poll_2_options_success(tmp_path: Path) -> None:
    """Tests creating a standard 2-option poll."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=POLL_COMPOSE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()
        await page.goto("https://x.com/compose/post")

        action = CreatePoll(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            question="What is your favorite language?",
            options=["Python", "Rust"],
            duration_days=1,
            base_url="https://x.com",
        )

        assert result is True

        submitted = await page.evaluate("() => window.__pollSubmitted")
        assert submitted is not None
        assert "What is your favorite language?" in submitted["question"]
        assert submitted["choice1"] == "Python"
        assert submitted["choice2"] == "Rust"

        await browser.close()


@pytest.mark.asyncio
async def test_create_poll_4_options_success(tmp_path: Path) -> None:
    """Tests creating a 4-option poll with multiple extra choices added."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=POLL_COMPOSE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()
        await page.goto("https://x.com/compose/post")

        action = CreatePoll(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            question="Which database is best for scale?",
            options=["PostgreSQL", "MySQL", "Cassandra", "DynamoDB"],
            duration_days=2,
            base_url="https://x.com",
        )

        assert result is True

        submitted = await page.evaluate("() => window.__pollSubmitted")
        assert submitted is not None
        assert "Which database is best for scale?" in submitted["question"]
        assert submitted["choice1"] == "PostgreSQL"
        assert submitted["choice2"] == "MySQL"
        assert submitted["choice3"] == "Cassandra"
        assert submitted["choice4"] == "DynamoDB"

        await browser.close()


@pytest.mark.asyncio
async def test_create_poll_3_options_success(tmp_path: Path) -> None:
    """Tests creating a 3-option poll with 1 extra choice."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body=POLL_COMPOSE_HTML)

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()
        await page.goto("https://x.com/compose/post")

        action = CreatePoll(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            question="Best cloud provider?",
            options=["AWS", "GCP", "Azure"],
            duration_days=1,
            base_url="https://x.com",
        )

        assert result is True

        submitted = await page.evaluate("() => window.__pollSubmitted")
        assert submitted is not None
        assert "Best cloud provider?" in submitted["question"]
        assert submitted["choice1"] == "AWS"
        assert submitted["choice2"] == "GCP"
        assert submitted["choice3"] == "Azure"
        assert submitted["choice4"] == ""

        await browser.close()


@pytest.mark.asyncio
async def test_create_poll_navigates_to_compose_if_needed(tmp_path: Path) -> None:
    """Tests navigating to compose post URL if textarea is not already on page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def handle_route(route: Any) -> None:
            url = route.request.url
            if "/compose/post" in url:
                await route.fulfill(status=200, content_type="text/html", body=POLL_COMPOSE_HTML)
            else:
                # Blank / home page
                await route.fulfill(status=200, content_type="text/html", body="<html><body><h1>Home</h1></body></html>")

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()
        await page.goto("https://x.com/home")

        action = CreatePoll(screenshot_dir=str(tmp_path))
        result = await action.execute(
            page=page,
            question="Navigated Poll Question?",
            options=["Option A", "Option B"],
            duration_days=1,
            base_url="https://x.com",
        )

        assert result is True
        assert "/compose/post" in page.url

        await browser.close()


@pytest.mark.asyncio
async def test_create_poll_failure_returns_false_and_saves_screenshot(tmp_path: Path) -> None:
    """Tests that execution errors gracefully return False and capture failure screenshot."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Route returns HTML with missing submit button and broken elements
        async def handle_route(route: Any) -> None:
            await route.fulfill(status=200, content_type="text/html", body="<html><body><div>Broken Compose</div></body></html>")

        await context.route("https://x.com/**", handle_route)
        page = await context.new_page()
        await page.goto("https://x.com/compose/post")

        action = CreatePoll(screenshot_dir=str(tmp_path))
        # Provide invalid / short timeout by pointing at page without textarea
        result = await action.execute(
            page=page,
            question="Broken question?",
            options=["A", "B"],
            duration_days=1,
            base_url="https://x.com",
        )

        assert result is False
        # Screenshot directory should have failure screenshot
        screenshots = list(tmp_path.glob("*.png"))
        assert len(screenshots) >= 1

        await browser.close()
