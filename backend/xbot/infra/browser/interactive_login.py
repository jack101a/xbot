"""
xbot.infra.browser.interactive_login: Interactive Headed Browser Login Helper.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright
from xbot.config import settings


async def run_interactive_login_session(profile_slug: str, base_profile_dir: str | None = None) -> dict[str, Any]:
    """
    Launches a headed Playwright browser on the host display pointing to X.com login.
    Captures cookies/storage state upon browser window close and saves it for persistent session.
    """
    profile_dir = Path(base_profile_dir or settings.BASE_PROFILE_DIR) / profile_slug
    profile_dir.mkdir(parents=True, exist_ok=True)
    state_path = profile_dir / "storage_state.json"

    if not os.environ.get("DISPLAY"):
        os.environ["DISPLAY"] = ":0"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"],
        )
        context = await browser.new_context(
            viewport=None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        if state_path.exists():
            try:
                import json
                with open(state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    await context.add_cookies(state.get("cookies", []))
            except Exception:
                pass

        await page.goto("https://x.com/login", wait_until="domcontentloaded")
        try:
            await page.wait_for_event("close", timeout=300000)
        except Exception:
            pass

        await context.storage_state(path=str(state_path))
        await context.close()
        await browser.close()

    return {
        "status": "success",
        "message": "Interactive login session completed and cookies saved.",
        "storage_state_path": str(state_path),
    }
