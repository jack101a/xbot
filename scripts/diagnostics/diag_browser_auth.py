"""
Phase 1 Diagnostic: What is X.com actually returning for the authenticated @jackds1234 session?
Takes a screenshot and dumps the DOM to identify exactly where the browser fails.
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
    manager.acquire_lock(PROFILE_SLUG, timeout_seconds=30)
    context = None
    try:
        await manager.start()
        context = await manager.get_context(PROFILE_SLUG)
        page = await context.new_page()

        print("=== STEP 1: Navigate to x.com/home (timeline) ===")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        url_after = page.url
        print(f"  URL after goto home: {url_after}")
        await page.screenshot(path=str(OUT_DIR / "01_home.png"), full_page=False)
        print(f"  Screenshot saved: 01_home.png")

        # Check if we landed on login page or actual home
        login_form = await page.query_selector('[data-testid="LoginForm_Login_Button"], input[name="text"]')
        home_timeline = await page.query_selector('[data-testid="primaryColumn"]')
        print(f"  Login form present: {login_form is not None}")
        print(f"  Home timeline present: {home_timeline is not None}")

        print("\n=== STEP 2: Navigate to @elonmusk profile ===")
        await page.goto("https://x.com/elonmusk", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        print(f"  URL: {page.url}")
        await page.screenshot(path=str(OUT_DIR / "02_elonmusk.png"), full_page=False)
        print(f"  Screenshot saved: 02_elonmusk.png")

        # Look for tweet selector alternatives
        selectors_to_test = [
            '[data-testid="tweet"]',
            'article[data-testid="tweet"]',
            'article[role="article"]',
            '[data-testid="cellInnerDiv"]',
            '[data-testid="tweetText"]',
            '[aria-label*="Timeline"]',
        ]
        print("  Testing tweet selectors:")
        for sel in selectors_to_test:
            els = await page.query_selector_all(sel)
            print(f"    {sel!r}: {len(els)} elements found")

        # Check for wall / login wall / challenge
        walls = {
            "login_wall": '[data-testid="LoginForm_Login_Button"]',
            "flow_wall": '[data-testid="StartLoginFlow"]',
            "challenge": '[data-testid="challenge"]',
            "suspendedNotice": '[data-testid="suspendedNotice"]',
            "primaryColumn": '[data-testid="primaryColumn"]',
            "UserName": '[data-testid="UserName"]',
        }
        print("  Checking for walls/auth indicators:")
        for name, sel in walls.items():
            el = await page.query_selector(sel)
            print(f"    {name}: {'FOUND' if el else 'not found'}")

        print("\n=== STEP 3: Navigate to own profile @jackds1234 ===")
        await page.goto("https://x.com/jackds1234", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        print(f"  URL: {page.url}")
        await page.screenshot(path=str(OUT_DIR / "03_jackds1234.png"), full_page=False)
        print(f"  Screenshot saved: 03_jackds1234.png")
        for name, sel in walls.items():
            el = await page.query_selector(sel)
            print(f"    {name}: {'FOUND' if el else 'not found'}")

        print("\n=== STEP 4: Try like action on a tweet ===")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(3)
        like_btns = await page.query_selector_all('[data-testid="like"]')
        print(f"  Like buttons on timeline: {len(like_btns)}")
        if like_btns:
            await like_btns[0].click()
            await asyncio.sleep(2)
            await page.screenshot(path=str(OUT_DIR / "04_after_like.png"), full_page=False)
            print("  Like clicked — screenshot saved")

        print("\n=== STEP 5: Dump page title and cookies ===")
        title = await page.title()
        print(f"  Page title: {title}")
        cookies = await context.cookies()
        print(f"  Active cookies: {len(cookies)}")
        for c in cookies:
            if c['name'] in ('auth_token', 'ct0', 'twid'):
                print(f"    {c['name']} = {c['value'][:25]}... [{c['domain']}]")

        print(f"\nAll screenshots in: {OUT_DIR}")

    finally:
        if context:
            await context.close()
        await manager.stop()
        manager.release_lock(PROFILE_SLUG)

if __name__ == "__main__":
    asyncio.run(main())
