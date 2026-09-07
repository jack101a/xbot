"""Playwright persistent-context browser manager.

Owns a single persistent Chromium profile under ``~/.chatgpt-bridge/profile``
so a logged-in session survives across runs.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from .errors import AuthError

# State directory lives in the user's home.
STATE_DIR = Path(os.environ.get("CHATGPT_BRIDGE_STATE", "~/.chatgpt-bridge")).expanduser()
PROFILE_DIR = STATE_DIR / "profile"


def _ensure_virtual_display() -> None:
    """Ensures an X11 virtual display is running so Chromium can run headed without a physical monitor."""
    if not os.environ.get("DISPLAY"):
        try:
            import subprocess
            res = subprocess.run(["pgrep", "-a", "Xvfb"], capture_output=True, text=True)
            if ":99" not in res.stdout:
                subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1920x1080x24"])
            os.environ["DISPLAY"] = ":99"
        except Exception:
            pass


class BrowserManager:
    """Launch and manage a persistent Playwright Chromium context."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Any = None
        self._context: Any = None

    async def start(self) -> None:
        """Launch the persistent context at ``PROFILE_DIR``."""
        if self._context is not None:
            return
        _ensure_virtual_display()
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        # Clean up any stale singleton locks from killed processes
        for lock_file in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            lf = PROFILE_DIR / lock_file
            if lf.exists() or lf.is_symlink():
                try:
                    lf.unlink(missing_ok=True)
                except Exception:
                    pass
        self._playwright = await async_playwright().start()
        # If virtual display is available, run headed to bypass Cloudflare Turnstile headless detection
        effective_headless = False if os.environ.get("DISPLAY") else self.headless
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=effective_headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

    async def context(self):
        """Return the Playwright ``BrowserContext``, starting or recreating it if needed."""
        is_active = False
        if self._context is not None:
            try:
                # Check if context is still open
                if hasattr(self._context, "is_closed"):
                    is_active = not self._context.is_closed()
                else:
                    is_active = True
            except Exception:
                is_active = False

        if not is_active:
            self._context = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            await self.start()
        return self._context

    async def ensure_logged_in(self) -> None:
        """Ensure the persistent context has a live ChatGPT session.

        Raises :class:`AuthError` if the session endpoint is unreachable or
        reports an unauthenticated user.
        """
        ctx = await self.context()
        page = await ctx.new_page()
        try:
            resp = await page.request.get(
                "https://chatgpt.com/api/auth/session",
                timeout=15_000,
            )
            if resp.status != 200:
                raise AuthError(
                    "ChatGPT session check failed "
                    f"(status {resp.status}); re-login or refresh cookies."
                )
            data = await resp.json()
            if not data or not data.get("user"):
                raise AuthError(
                    "ChatGPT session is not authenticated; "
                    "re-login or refresh cookies."
                )
        finally:
            await page.close()

    async def stop(self) -> None:
        """Close the context and stop Playwright."""
        if self._context is not None:
            await self._context.close()
            self._context = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None