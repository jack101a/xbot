"""Session management: token/cookie harvest, validation, cookie import."""

from __future__ import annotations

from pathlib import Path

from .browser import BrowserManager
from .cookies import load_cookie_file
from .errors import AuthError

# Default cookie file locations checked during login flow.
COOKIE_TXT = Path("~/.chatgpt-bridge/cookies.txt").expanduser()
COOKIE_JSON = Path("~/.chatgpt-bridge/cookies.json").expanduser()


class SessionManager:
    """Validate and harvest the ChatGPT web session from a browser context."""

    def __init__(self, browser: BrowserManager) -> None:
        self.browser = browser
        self._pending_import: list[dict] | None = None
        self._cached_access_token: str | None = None

    async def is_alive(self) -> bool:
        """Return True iff the session endpoint reports an authenticated user."""
        ctx = await self.browser.context()
        page = await ctx.new_page()
        try:
            resp = await page.request.get(
                "https://chatgpt.com/api/auth/session",
                timeout=15_000,
            )
            if resp.status != 200:
                return False
            data = await resp.json()
            return bool(data and data.get("user"))
        except Exception:
            return False
        finally:
            await page.close()

    async def get_user_info(self) -> dict[str, Any] | None:
        """Return user dict from session endpoint if authenticated, else None."""
        ctx = await self.browser.context()
        page = await ctx.new_page()
        try:
            resp = await page.request.get(
                "https://chatgpt.com/api/auth/session",
                timeout=15_000,
            )
            if resp.status != 200:
                return None
            data = await resp.json()
            user = (data or {}).get("user")
            if user:
                return {
                    "email": user.get("email"),
                    "name": user.get("name"),
                    "image": user.get("image"),
                    "expires": (data or {}).get("expires"),
                }
            return None
        except Exception:
            return None
        finally:
            await page.close()

    async def get_access_token(self) -> str:
        """Parse the access token from the session endpoint JSON with token caching."""
        if self._cached_access_token:
            return self._cached_access_token
        ctx = await self.browser.context()
        page = await ctx.new_page()
        try:
            resp = await page.request.get(
                "https://chatgpt.com/api/auth/session",
                timeout=15_000,
            )
            if resp.status != 200:
                raise AuthError(
                    f"session endpoint returned status {resp.status}; "
                    "re-login or refresh cookies."
                )
            data = await resp.json()
            token = (data or {}).get("accessToken")
            if not token:
                raise AuthError(
                    "session JSON missing accessToken; re-login or refresh cookies."
                )
            self._cached_access_token = token
            return token
        finally:
            await page.close()

    async def get_cookies(self) -> list[dict]:
        """Return the current context cookies as Playwright-style dicts."""
        ctx = await self.browser.context()
        return await ctx.cookies()

    def import_cookie_file(self, path: str | Path) -> None:
        """Load a cookie file and mark it for injection on next context start.

        The cookies are applied via ``context.add_cookies`` the next time the
        browser context is started (see :meth:`apply_pending_import`).
        """
        cookies = load_cookie_file(path)
        self._pending_import = cookies

    async def apply_pending_import(self) -> None:
        """Inject any pending imported cookies into the live context."""
        if not self._pending_import:
            return
        ctx = await self.browser.context()
        for cookie in self._pending_import:
            try:
                await ctx.add_cookies([cookie])
            except Exception:
                pass
        self._pending_import = None

    async def try_cookie_login(self) -> bool:
        """Try cookie-file import; return True iff session became alive."""
        cookie_path = None
        if COOKIE_JSON.exists():
            cookie_path = COOKIE_JSON
        elif COOKIE_TXT.exists():
            cookie_path = COOKIE_TXT
        if cookie_path is None:
            return False
        self.import_cookie_file(cookie_path)
        await self.apply_pending_import()
        return await self.is_alive()

    async def login_flow(self, interactive: bool = True) -> None:
        """Establish a session using the documented priority.

        Priority: existing live profile -> cookie import -> interactive
        headful relaunch (only when ``interactive`` is True; caller raises
        on its own when the session is still missing afterwards).
        """
        # 1. Existing profile already alive?
        if await self.is_alive():
            return

        # 2. Cookie import if a cookie file is present.
        if await self.try_cookie_login():
            return

        # 3. Interactive headful relaunch.
        if interactive:
            await self._interactive_login()

    async def _interactive_login(self) -> None:
        """Open a headful browser for the user to log in manually."""
        ctx = await self.browser.context()
        page = await ctx.new_page()
        try:
            await page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
            print(
                "Please log in to ChatGPT in the opened browser window, "
                "then press Enter here to continue..."
            )
            await self._wait_for_enter()
            if not await self.is_alive():
                raise AuthError(
                    "Interactive login did not produce a valid session; "
                    "please try again or refresh cookies."
                )
        finally:
            await page.close()

    async def delete_conversation(self, conversation_id: str) -> None:
        """Soft-delete (hide) a conversation via the browser request context.

        Uses ``PATCH /backend-api/conversation/{id}`` with ``is_visible: false``,
        matching the web UI's "Delete chat" action. The browser context carries
        the full cookie jar + Cloudflare clearance, so this succeeds where a
        bare ``httpx`` call returns 403.
        """
        import json as _json

        access_token = await self.get_access_token()
        ctx = await self.browser.context()
        page = await ctx.new_page()
        try:
            resp = await page.request.patch(
                f"https://chatgpt.com/backend-api/conversation/{conversation_id}",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                },
                data=_json.dumps({"is_visible": False}),
                timeout=30_000,
            )
            if resp.status not in (200, 204):
                raise AuthError(
                    f"delete conversation returned status {resp.status}"
                )
        finally:
            await page.close()

    async def list_conversations(self, limit: int = 20) -> list[dict]:
        """List recent conversations (most-recently-updated first)."""
        ctx = await self.browser.context()
        page = await ctx.new_page()
        try:
            resp = await page.request.get(
                "https://chatgpt.com/backend-api/conversations",
                params={"offset": 0, "limit": limit, "order": "updated"},
                timeout=30_000,
            )
            if resp.status != 200:
                raise AuthError(
                    f"list conversations returned status {resp.status}"
                )
            data = await resp.json()
            return data.get("items") or data.get("conversations") or []
        finally:
            await page.close()

    @staticmethod
    async def _wait_for_enter() -> None:
        """Block until the user presses Enter on stdin (run in executor)."""
        import asyncio

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, input)