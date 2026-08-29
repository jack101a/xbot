"""UI fallback driver: drive chatgpt.com DOM via Playwright."""

from __future__ import annotations

import asyncio
import time

from .browser import BrowserManager
from .errors import BridgeTimeoutError, ShapeChangedError
from .images import save_image, wait_for_image
from .session import SessionManager

# Robust selectors, data-testid first.
COMPOSER_SELECTOR = (
    '[data-testid="composer-text-input"], div[contenteditable="true"]'
)
SEND_SELECTOR = '[data-testid="composer-send-button"]'
TURN_SELECTOR = '[data-testid^="conversation-turn"]'
ASSISTANT_SELECTOR = '[data-message-author-role="assistant"]'

HOME_URL = "https://chatgpt.com/"


class UIDriver:
    """Drive the ChatGPT web UI as a fallback and for image generation."""

    def __init__(self, browser: BrowserManager, session: SessionManager) -> None:
        self.browser = browser
        self.session = session

    async def _page(self):
        ctx = await self.browser.context()
        page = await ctx.new_page()
        await page.goto(HOME_URL, wait_until="domcontentloaded")
        return page

    async def ask(
        self, prompt: str, conversation_id: str | None = None
    ) -> dict:
        """Submit a prompt via the composer and return ``{"text", ...}``."""
        page = await self._page()
        try:
            await self._submit_prompt(page, prompt)
            text = await self._wait_for_answer(page)
            cid = conversation_id or await self._current_conversation_id(page)
            return {"text": text, "conversation_id": cid}
        finally:
            await page.close()

    async def generate_image(self, prompt: str, timeout_s: int = 180, output_dir: Path | str | None = None) -> dict:
        """Submit a prompt and wait for a generated image."""
        page = await self._page()
        try:
            await self._submit_prompt(page, prompt)
            src = await wait_for_image(page, timeout_s=timeout_s)
            ctx = await self.browser.context()
            target_out = Path(output_dir).expanduser() if output_dir else _images_dir()
            path = await save_image(src, target_out, ctx.request)
            conversation_id = await self._current_conversation_id(page)
            return {
                "path": str(path),
                "prompt": prompt,
                "conversation_id": conversation_id,
            }
        finally:
            await page.close()

    async def _current_conversation_id(self, page) -> str:
        """Extract the conversation id from the URL (``/c/<id>``), else empty."""
        try:
            url = page.url
            if "/c/" in url:
                return url.split("/c/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        except Exception:
            pass
        return ""

    async def _submit_prompt(self, page, prompt: str) -> None:
        composer = page.locator(COMPOSER_SELECTOR).first
        await composer.wait_for(state="visible", timeout=30_000)
        await composer.click()
        # Type characters: fill() doesn't fire the input events the
        # contenteditable ProseMirror composer needs.
        await page.keyboard.type(prompt, delay=10)
        await page.keyboard.press("Enter")

    async def _wait_for_answer(self, page, timeout_s: int = 120) -> str:
        """Poll assistant turns until the answer is stable across 2 polls."""
        deadline = time.monotonic() + timeout_s
        last_text = ""
        stable_polls = 0
        while time.monotonic() < deadline:
            text = await self._read_last_assistant(page)
            if text and text == last_text:
                stable_polls += 1
                if stable_polls >= 2:
                    return text
            elif text:
                last_text = text
                stable_polls = 0
            await asyncio.sleep(1.0)
        if last_text:
            return last_text
        raise ShapeChangedError("no assistant answer detected in UI")

    async def _read_last_assistant(self, page) -> str:
        try:
            turns = page.locator(TURN_SELECTOR)
            count = await turns.count()
            for i in range(count - 1, -1, -1):
                turn = turns.nth(i)
                if await turn.locator(ASSISTANT_SELECTOR).count() > 0:
                    return (await turn.inner_text()).strip()
        except Exception:
            pass
        return ""


def _images_dir():
    from pathlib import Path

    return Path("~/.chatgpt-bridge/images").expanduser()