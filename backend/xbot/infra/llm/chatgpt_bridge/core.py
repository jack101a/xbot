"""Public core API for chatgpt-bridge."""

from __future__ import annotations

import asyncio

from .browser import BrowserManager
from .chat_pool import DEFAULT_MAX_CHATS, ChatPoolManager
from .errors import AuthError, ShapeChangedError
from .http_client import BackendClient
from .session import SessionManager
from .ui_driver import UIDriver


class ChatGPT:
    """Prompt ChatGPT (web session) for text and images.

    Uses the fast backend-api HTTP path first, falling back to the UI driver
    when the HTTP shape drifts.
    """

    def __init__(
        self,
        headless: bool = True,
        auto_relogin: bool = False,
        max_chats: int | None = None,
    ) -> None:
        self.headless = headless
        self.auto_relogin = auto_relogin
        self.browser = BrowserManager(headless=headless)
        self.session = SessionManager(self.browser)
        self.http = BackendClient(self.session)
        self.ui = UIDriver(self.browser, self.session)
        self.pool = ChatPoolManager(
            self.session,
            max_chats=max_chats if max_chats is not None else DEFAULT_MAX_CHATS,
        )
        self._started = False
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    async def _ensure_started(self) -> None:
        if self._started:
            return
        await self.browser.start()
        await self.session.apply_pending_import()
        if not await self.session.is_alive():
            # Try cookie-file import before giving up or going interactive.
            await self.session.try_cookie_login()
        if not await self.session.is_alive():
            if self.auto_relogin:
                await self.session.login_flow()
            else:
                raise AuthError(
                    "No valid ChatGPT session. Re-login or refresh cookies, "
                    "or construct with auto_relogin=True."
                )
        self._started = True

    async def ask(
        self,
        prompt: str,
        model: str | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        """Return ``{"text", "conversation_id"}``.

        Tries the backend HTTP path first; on :class:`ShapeChangedError`
        falls back to the UI driver.
        """
        self.browser.touch()
        await self._ensure_started()
        try:
            result = await self.http.ask(prompt, conversation_id=conversation_id)
        except ShapeChangedError:
            result = await self.ui.ask(prompt, conversation_id=conversation_id)
        self.browser.touch()
        await self._track(result.get("conversation_id"))
        return result

    async def generate_image(self, prompt: str, timeout_s: int = 180) -> dict:
        """Generate an image via the UI and return ``{"path", "prompt"}``."""
        self.browser.touch()
        await self._ensure_started()
        result = await self.ui.generate_image(prompt, timeout_s=timeout_s)
        self.browser.touch()
        await self._track(result.get("conversation_id"))
        return result

    async def _track(self, conversation_id: str | None) -> None:
        """Record a bridge-created conversation and prune the oldest past the limit."""
        if not conversation_id:
            return
        try:
            self.pool.record(conversation_id)
            await self.pool.prune()
        except Exception:
            pass

    async def close_if_idle(self) -> bool:
        """Close browser if idle and reset started state."""
        closed = await self.browser.close_if_idle()
        if closed:
            self._started = False
        return closed

    async def aclose(self) -> None:
        """Asynchronously stop the browser and ensure clean teardown."""
        try:
            await self.browser.stop()
        except Exception:
            pass
        finally:
            self._started = False

    def close(self) -> None:
        """Synchronously stop the browser and ensure clean teardown."""
        try:
            if self._started or (hasattr(self, "browser") and self.browser._context is not None):
                try:
                    running_loop = asyncio.get_running_loop()
                except RuntimeError:
                    running_loop = None

                if running_loop and running_loop.is_running():
                    running_loop.create_task(self.browser.stop())
                else:
                    loop = self._get_loop()
                    if not loop.is_closed():
                        loop.run_until_complete(self.browser.stop())
        except Exception:
            pass
        finally:
            self._started = False
            if self._loop is not None and not self._loop.is_closed():
                try:
                    self._loop.close()
                except Exception:
                    pass
                self._loop = None

    # Sync sugar — all reuse one event loop (Playwright objects are loop-bound).
    def ask_sync(self, prompt: str, model: str | None = None, conversation_id: str | None = None) -> dict:
        return self._get_loop().run_until_complete(
            self.ask(prompt, model=model, conversation_id=conversation_id)
        )

    def generate_image_sync(self, prompt: str, timeout_s: int = 180) -> dict:
        return self._get_loop().run_until_complete(
            self.generate_image(prompt, timeout_s=timeout_s)
        )