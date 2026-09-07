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
    '#prompt-textarea, [data-testid="composer-text-input"], div[contenteditable="true"], textarea[placeholder*="Message"]'
)
SEND_SELECTOR = '[data-testid="send-button"], [data-testid="composer-send-button"], button[aria-label*="Send"]'
TURN_SELECTOR = '[data-testid^="conversation-turn"]'
ASSISTANT_SELECTOR = '[data-message-author-role="assistant"], .markdown'

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

    async def generate_image(self, prompt: str, timeout_s: int = 300) -> dict:
        """Submit a prompt and wait for a generated image."""
        page = await self._page()
        try:
            await self._submit_prompt(page, prompt)
            src = await wait_for_image(page, timeout_s=timeout_s)
            ctx = await self.browser.context()
            path = await save_image(src, _images_dir(), ctx.request)
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

    async def _dismiss_modals_if_present(self, page) -> None:
        """Dismiss common ChatGPT onboarding, promotion, or rate-limit popups."""
        try:
            await page.evaluate("""() => {
                const modals = document.querySelectorAll(
                    '#modal-conversation-history-rate-limit, [id*="rate-limit"], [data-testid*="rate-limit"], [data-state="open"][role="dialog"]'
                );
                modals.forEach(m => {
                    const closeBtn = m.querySelector('button[aria-label*="Close"], button[data-testid*="close"], button');
                    if (closeBtn && (closeBtn.textContent.includes('Dismiss') || closeBtn.textContent.includes('OK') || closeBtn.getAttribute('aria-label')?.includes('Close'))) {
                        closeBtn.click();
                    } else {
                        m.remove();
                    }
                });
                document.querySelectorAll('.fixed.inset-0.z-50').forEach(b => b.remove());
            }""")
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.2)
        except Exception:
            pass

    async def _submit_prompt(self, page, prompt: str) -> None:
        await self._dismiss_modals_if_present(page)

        composer = page.locator(COMPOSER_SELECTOR).first
        await composer.wait_for(state="visible", timeout=30_000)
        try:
            await composer.click(timeout=3000)
        except Exception:
            await self._dismiss_modals_if_present(page)
            await composer.click(force=True)

        # Insert entire multi-line text block atomically without firing Enter on newlines
        inserted = False
        try:
            inserted = await page.evaluate("""(text) => {
                const el = document.querySelector('#prompt-textarea, [data-testid="composer-text-input"], div[contenteditable="true"]');
                if (!el) return false;
                el.focus();
                // Select all existing text
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(el);
                sel.removeAllRanges();
                sel.addRange(range);
                // Atomically insert full text including newlines
                const res = document.execCommand('insertText', false, text);
                return res && el.textContent.trim().length > 0;
            }""", prompt)
        except Exception:
            inserted = False

        if not inserted:
            # Fallback: type line by line using Shift+Enter for newlines so Enter does not submit early
            lines = prompt.split("\n")
            for i, line in enumerate(lines):
                if line:
                    await page.keyboard.type(line, delay=1)
                if i < len(lines) - 1:
                    await page.keyboard.down("Shift")
                    await page.keyboard.press("Enter")
                    await page.keyboard.up("Shift")

        await asyncio.sleep(0.5)
        await self._dismiss_modals_if_present(page)

        # Submit the complete prompt via Send button or Enter
        send_btn = page.locator(SEND_SELECTOR).first
        try:
            if await send_btn.is_visible(timeout=2000):
                await send_btn.click(timeout=3000)
                return
        except Exception:
            pass

        await page.keyboard.press("Enter")

    async def _wait_for_answer(self, page, timeout_s: int = 240) -> str:
        """Poll assistant turns until generation concludes and answer is fully settled."""
        deadline = time.monotonic() + timeout_s
        await asyncio.sleep(2.0)

        # Wait for stop generating button to disappear
        stop_btn = page.locator('[data-testid="stop-button"], button[aria-label*="Stop"]')
        try:
            if await stop_btn.count() > 0:
                await stop_btn.first.wait_for(state="detached", timeout=timeout_s * 1000)
        except Exception:
            pass

        last_text = ""
        stable_polls = 0
        while time.monotonic() < deadline:
            text = await self._read_last_assistant(page)
            if text and text == last_text:
                stable_polls += 1
                if stable_polls >= 3:
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