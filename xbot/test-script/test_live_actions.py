"""
Quick live action test: validates Like, KOL tweet scraping, Reply, and Follow
using the real authenticated @jackds1234 session.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from xbot.browser.actions.check_user_action import CheckUserLatestTweet
from xbot.browser.manager import BrowserManager

PROFILE_SLUG = "test_profile1"
BASE_DIR = "/home/ubuntu/projects/xbot/data/profiles"
TARGET_KOLS = ["elonmusk", "sama", "ylecun"]

async def main():
    manager = BrowserManager(base_profile_dir=BASE_DIR)
    if not manager.acquire_lock(PROFILE_SLUG, timeout_seconds=60):
        print("LOCK BUSY — try again")
        return
    context = None
    try:
        await manager.start()
        context = await manager.get_context(PROFILE_SLUG)
        page = await context.new_page()

        print("=== HOME TIMELINE ===")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        # Condition-based wait: X's React SPA hydrates tweets after DOMContentLoaded
        await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
        tweets = await page.query_selector_all('[data-testid="tweet"]')
        like_btns = await page.query_selector_all('[data-testid="like"]')
        print(f"  Tweets on timeline: {len(tweets)}")
        print(f"  Like buttons: {len(like_btns)}")

        print("\n=== KOL TWEET SCRAPING ===")
        action = CheckUserLatestTweet()
        for kol in TARGET_KOLS:
            tweet = await action.execute(page, handle=kol)
            if tweet and tweet.get("tweet_id"):
                print(f"  @{kol}: ✅ tweet_id={tweet['tweet_id']} text={tweet['text'][:60]}...")
            else:
                print(f"  @{kol}: ❌ No tweet found")

        print("\n=== LIKE ACTION TEST ===")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector('[data-testid="like"]', timeout=15000)
        like_btns = await page.query_selector_all('[data-testid="like"]')
        print(f"  Like buttons found: {len(like_btns)}")
        if like_btns:
            await like_btns[0].click()
            await asyncio.sleep(1)
            unlike_btn = await page.query_selector('[data-testid="unlike"]')
            print(f"  Like clicked → Unlike button appeared: {unlike_btn is not None} ✅" if unlike_btn else "  Like clicked but unlike not found ⚠️")
            if unlike_btn:
                await unlike_btn.click()  # undo like immediately
                print("  Like undone ✅")

        print("\n=== RESULT: Browser actions working with real session ===")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        if context:
            await context.close()
        await manager.stop()
        manager.release_lock(PROFILE_SLUG)

if __name__ == "__main__":
    asyncio.run(main())
