from __future__ import annotations

import logging
import random
from pathlib import Path

import redis
from playwright.async_api import (
    BrowserContext,
    Playwright,
    ProxySettings,
    async_playwright,
)

from xbot.browser.stealth import apply_stealth_to_context
from xbot.config import settings

logger = logging.getLogger(__name__)


# Structured browser profiles: every field is internally consistent.
# sec-ch-ua MUST match the Chrome version in the User-Agent string exactly —
# mismatches are a primary X anti-bot signal.
_BROWSER_PROFILES = [
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec_ch_ua_platform": '"Windows"',
        "platform": "Win32",
        "viewport": (1366, 768),
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="123", "Google Chrome";v="123", "Not-A.Brand";v="24"',
        "sec_ch_ua_platform": '"Windows"',
        "platform": "Win32",
        "viewport": (1280, 800),
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec_ch_ua_platform": '"macOS"',
        "platform": "MacIntel",
        "viewport": (1440, 900),
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="122", "Google Chrome";v="122", "Not-A.Brand";v="24"',
        "sec_ch_ua_platform": '"Windows"',
        "platform": "Win32",
        "viewport": (1920, 1080),
    },
    {
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec_ch_ua_platform": '"macOS"',
        "platform": "MacIntel",
        "viewport": (1512, 982),
    },
    {
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Chromium";v="125", "Google Chrome";v="125", "Not-A.Brand";v="24"',
        "sec_ch_ua_platform": '"Windows"',
        "platform": "Win32",
        "viewport": (1600, 900),
    },
]


class BrowserManager:
    """
    Manages Playwright browser automation contexts and anti-detection settings.
    Enforces profile locks to prevent parallel sessions for the same persona.
    """

    def __init__(
        self, base_profile_dir: str = "/home/ubuntu/projects/xbot/data/profiles"
    ) -> None:
        self.base_profile_dir = Path(base_profile_dir)
        self.playwright: Playwright | None = None
        self._redis_client = redis.from_url(settings.REDIS_URL)

    async def start(self) -> None:
        """Starts the Playwright driver."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            logger.info("Playwright engine started.")

    async def stop(self) -> None:
        """Stops the Playwright driver."""
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Playwright engine stopped.")

    def acquire_lock(self, profile_slug: str, timeout_seconds: int = 180) -> bool:
        """
        Acquires a lock in Redis to prevent multiple workers
        from running the same profile simultaneously.
        """
        lock_key = f"lock:browser:{profile_slug}"
        for _ in range(3):
            if self._redis_client.set(lock_key, "1", ex=timeout_seconds, nx=True):
                return True
            import time
            time.sleep(1.0)
        return False

    def release_lock(self, profile_slug: str) -> None:
        """
        Releases the execution lock for a profile.
        """
        lock_key = f"lock:browser:{profile_slug}"
        self._redis_client.delete(lock_key)

    async def get_context(
        self,
        profile_slug: str,
        browser_profile: dict | None = None,
        locale: str = "en-US",
        timezone: str = "America/New_York",
        proxy_url: str | None = None,
    ) -> BrowserContext:
        """
        Creates or retrieves a persistent browser context for the profile.

        Picks a random browser fingerprint profile where ALL signals are
        internally consistent: UA, sec-ch-ua client hints, platform,
        and viewport all agree with each other.

        This prevents the #1 X detection signal: mismatched client hints.
        """
        if not self.playwright:
            await self.start()

        assert self.playwright is not None

        # Pick a fully consistent browser profile (UA + client hints + viewport)
        if browser_profile is None:
            browser_profile = random.choice(_BROWSER_PROFILES)

        ua = browser_profile["ua"]
        sec_ch_ua = browser_profile["sec_ch_ua"]
        sec_ch_ua_platform = browser_profile["sec_ch_ua_platform"]
        platform = browser_profile["platform"]
        vp_w, vp_h = browser_profile["viewport"]

        user_data_dir = self.base_profile_dir / profile_slug / "browser_data"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        # Clean up stale Chromium Singleton locks if present
        for stale_name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
            stale_p = user_data_dir / stale_name
            if stale_p.exists() or stale_p.is_symlink():
                try:
                    stale_p.unlink()
                except Exception:
                    pass

        proxy_config: ProxySettings | None = None
        if proxy_url:
            proxy_config = {"server": proxy_url}

        context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=True,
            bypass_csp=True,
            user_agent=ua,
            viewport={"width": vp_w, "height": vp_h},
            locale=locale,
            timezone_id=timezone,
            proxy=proxy_config,
            # sec-ch-ua client hints — MUST match UA exactly or X flags as bot
            extra_http_headers={
                "sec-ch-ua": sec_ch_ua,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": sec_ch_ua_platform,
                "Accept-Language": "en-US,en;q=0.9",
            },
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-web-security",
                "--enable-webgl",
                "--ignore-certificate-errors",
                # Declare window size so headless size matches the viewport
                f"--window-size={vp_w},{vp_h + 88}",  # +88 accounts for browser chrome
            ],
        )

        logger.info(
            "Browser context for profile %s: %s | %dx%d | platform=%s",
            profile_slug, ua[:70], vp_w, vp_h, platform
        )

        # Apply stealth (playwright-stealth + randomized fingerprint overrides)
        # Pass platform so navigator.platform matches our UA
        await apply_stealth_to_context(context, platform=platform)


        # Automatically load cookies from storage_state.json if it exists
        state_path = self.base_profile_dir / profile_slug / "storage_state.json"
        if state_path.exists():
            import json
            try:
                with open(state_path, "r") as f:
                    state_data = json.load(f)
                
                raw_cookies = []
                if isinstance(state_data, list):
                    raw_cookies = state_data
                elif isinstance(state_data, dict):
                    raw_cookies = state_data.get("cookies", [])
                
                if raw_cookies:
                    sanitized_cookies = []
                    for c in raw_cookies:
                        if not isinstance(c, dict):
                            continue
                        
                        expires = c.get("expirationDate") or c.get("expires")
                        cookie = {
                            "name": c.get("name"),
                            "value": c.get("value"),
                            "domain": c.get("domain"),
                            "path": c.get("path") or "/",
                            "secure": c.get("secure", True),
                            "httpOnly": c.get("httpOnly", False),
                        }
                        if expires is not None:
                            cookie["expires"] = float(expires)
                        
                        same_site = c.get("sameSite")
                        if same_site:
                            ss_lower = same_site.lower()
                            if "lax" in ss_lower:
                                cookie["sameSite"] = "Lax"
                            elif "strict" in ss_lower:
                                cookie["sameSite"] = "Strict"
                            elif "none" in ss_lower or "no_restriction" in ss_lower:
                                cookie["sameSite"] = "None"
                        sanitized_cookies.append(cookie)
                    
                    await context.add_cookies(sanitized_cookies)
                    logger.info("Successfully imported and sanitized %d cookies from storage_state.json for profile %s", len(sanitized_cookies), profile_slug)
            except Exception as e:
                logger.error("Failed to load/sanitize cookies from storage_state.json for profile %s: %s", profile_slug, e)

        logger.info("Created browser context for profile slug: %s", profile_slug)
        return context

    async def get_tab_pool(self, profile_slug: str, context: BrowserContext | None = None):
        """Retrieves the dedicated TabPool for a profile."""
        from xbot.browser.tab_pool import tab_pool_manager
        if context is None:
            context = await self.get_context(profile_slug)
        return await tab_pool_manager.get_pool(profile_slug, context)

    async def get_home_page(self, profile_slug: str):
        """Retrieves Tab 1 (Main Home Feed Anchor) permanently on x.com/home."""
        pool = await self.get_tab_pool(profile_slug)
        return await pool.get_home_page()

    async def get_research_page(self, profile_slug: str):
        """Retrieves Tab 2 (Dedicated Trend & Media Harvester)."""
        pool = await self.get_tab_pool(profile_slug)
        return await pool.get_research_page()

    def acquire_worker(self, profile_slug: str, name: str = "worker"):
        """Async context manager to acquire an ephemeral worker tab (Tab 3 or 4)."""
        from xbot.browser.tab_pool import tab_pool_manager
        class _WorkerContextManager:
            def __init__(self, manager: BrowserManager, slug: str, w_name: str):
                self.mgr = manager
                self.slug = slug
                self.w_name = w_name
                self._cm = None

            async def __aenter__(self):
                pool = await self.mgr.get_tab_pool(self.slug)
                self._cm = pool.acquire_worker(name=self.w_name)
                return await self._cm.__aenter__()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self._cm:
                    return await self._cm.__aexit__(exc_type, exc_val, exc_tb)

        return _WorkerContextManager(self, profile_slug, name)
