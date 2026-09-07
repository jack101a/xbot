"""
Diagnose what selectors are actually present on @sama's profile page.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from xbot.browser.manager import BrowserManager

PROFILE_SLUG = "test_profile1"
BASE_DIR = "/home/ubuntu/projects/xbot/data/profiles"
OUT_DIR = Path(__file__).parent / "diag_output"
OUT_DIR.mkdir(exist_ok=True)

async def main():
    manager = BrowserManager(base_profile_dir=BASE_DIR)
    if not manager.acquire_lock(PROFILE_SLUG, timeout_seconds=60):
        print("LOCK BUSY"); return

    context = None
    try:
        await manager.start()
        context = await manager.get_context(PROFILE_SLUG)
        page = await context.new_page()

        await page.goto("https://x.com/sama", wait_until="domcontentloaded", timeout=20000)
        # Wait for something we know exists
        await page.wait_for_selector('[data-testid="primaryColumn"]', timeout=15000)
        await asyncio.sleep(2)

        await page.screenshot(path=str(OUT_DIR / "sama_profile.png"))
        print("Screenshot saved")

        # Test candidate selectors for the follow button and profile loaded indicator
        candidates = [
            '[data-testid="UserAvatar-Container-profileUser"]',
            '[data-testid="UserAvatar-Container-sama"]',
            '[data-testid="UserName"]',
            '[data-testid="UserProfileHeader_Items"]',
            '[data-testid="placementTracking"]',
            'div[data-testid*="UserAvatar"]',
            'button[data-testid="placementTracking"]',
            '[aria-label="Follow @sama"]',
            'button[aria-label*="Follow"]',
            '[data-testid="followButton"]',  # older name
            'button[data-testid*="follow"]',
            'div[data-testid="primaryColumn"] button',
        ]

        print("\nSelector results on @sama profile:")
        for sel in candidates:
            els = await page.query_selector_all(sel)
            if els:
                text = await els[0].inner_text() if els else ""
                print(f"  ✅ {sel!r}: {len(els)} elements — text={text[:50]!r}")
            else:
                print(f"  ❌ {sel!r}: 0 elements")

        # Dump ALL button data-testid values on the profile
        buttons = await page.query_selector_all("button")
        print(f"\n  All buttons ({len(buttons)} total):")
        for btn in buttons[:20]:
            tid = await btn.get_attribute("data-testid")
            label = await btn.get_attribute("aria-label")
            text = (await btn.inner_text())[:30]
            if tid or label:
                print(f"    data-testid={tid!r} aria-label={label!r} text={text!r}")

    finally:
        if context:
            await context.close()
        await manager.stop()
        manager.release_lock(PROFILE_SLUG)

if __name__ == "__main__":
    asyncio.run(main())
