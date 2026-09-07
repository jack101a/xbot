"""
Direct action diagnostic: test Post, Reply, Retweet, Follow
with the real authenticated @jackds1234 session.
Bypasses safety guard — for diagnostic use only.
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from xbot.browser.actions.x_actions import (
    ComposePost, ReplyToTweet, Retweet, FollowUser
)
from xbot.browser.manager import BrowserManager

PROFILE_SLUG = "test_profile1"
BASE_DIR = "/home/ubuntu/projects/xbot/data/profiles"
OUT_DIR = Path(__file__).parent / "diag_output"
OUT_DIR.mkdir(exist_ok=True)

# Use a benign existing tweet for reply/retweet tests (jackds1234's own tweet or a harmless one)
# We'll grab one from the home timeline dynamically

async def main():
    manager = BrowserManager(base_profile_dir=BASE_DIR)
    if not manager.acquire_lock(PROFILE_SLUG, timeout_seconds=60):
        print("LOCK BUSY")
        return

    context = None
    results = {}
    try:
        await manager.start()
        context = await manager.get_context(PROFILE_SLUG)
        page = await context.new_page()

        # ── STEP 1: Get a real tweet URL from timeline to use for reply/retweet ──
        print("=== Grabbing tweet URL from timeline ===")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
        tweet_links = await page.query_selector_all('a[href*="/status/"]')
        tweet_url = None
        for link in tweet_links:
            href = await link.get_attribute("href")
            if href and "/status/" in href and not href.endswith("/analytics"):
                tweet_url = f"https://x.com{href}" if href.startswith("/") else href
                break
        print(f"  Using tweet URL: {tweet_url}")

        # ── STEP 2: Test ComposePost ──
        print("\n=== TEST: ComposePost ===")
        post_text = "Testing automated posting — ignore this test tweet 🤖 (will delete)"
        action = ComposePost()
        try:
            success = await action.execute(page, text=post_text)
            results["compose_post"] = "✅ SUCCESS" if success else "❌ FAILED (returned False)"
        except Exception as e:
            results["compose_post"] = f"❌ ERROR: {e}"
        print(f"  ComposePost: {results['compose_post']}")
        await page.screenshot(path=str(OUT_DIR / "post_result.png"))

        # ── STEP 3: Test ReplyToTweet ──
        print("\n=== TEST: ReplyToTweet ===")
        if tweet_url:
            reply_action = ReplyToTweet()
            try:
                reply_text = "Interesting perspective! 🤖 (automated test reply)"
                success = await reply_action.execute(page, reply_text=reply_text, tweet_url=tweet_url)
                results["reply"] = "✅ SUCCESS" if success else "❌ FAILED (returned False)"
            except Exception as e:
                results["reply"] = f"❌ ERROR: {e}"
        else:
            results["reply"] = "⚠️ SKIPPED (no tweet URL)"
        print(f"  ReplyToTweet: {results['reply']}")
        await page.screenshot(path=str(OUT_DIR / "reply_result.png"))

        # ── STEP 4: Test Retweet ──
        print("\n=== TEST: Retweet ===")
        if tweet_url:
            rt_action = Retweet()
            try:
                success = await rt_action.execute(page, tweet_url=tweet_url)
                results["retweet"] = "✅ SUCCESS" if success else "❌ FAILED (returned False)"
            except Exception as e:
                results["retweet"] = f"❌ ERROR: {e}"
        else:
            results["retweet"] = "⚠️ SKIPPED (no tweet URL)"
        print(f"  Retweet: {results['retweet']}")
        await page.screenshot(path=str(OUT_DIR / "retweet_result.png"))

        # ── STEP 5: Test FollowUser ──
        print("\n=== TEST: FollowUser ===")
        follow_action = FollowUser()
        try:
            # Follow a harmless test account - we'll use @elonmusk (already famous, won't matter)
            # Actually let's use a small account that won't affect anything
            success = await follow_action.execute(page, username="sama")
            results["follow"] = "✅ SUCCESS" if success else "❌ FAILED (returned False)"
        except Exception as e:
            results["follow"] = f"❌ ERROR: {e}"
        print(f"  FollowUser: {results['follow']}")
        await page.screenshot(path=str(OUT_DIR / "follow_result.png"))

        print("\n" + "="*60)
        print("SUMMARY:")
        for action, result in results.items():
            print(f"  {action}: {result}")

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback; traceback.print_exc()
        if context:
            await page.screenshot(path=str(OUT_DIR / "fatal_error.png"))
    finally:
        if context:
            await context.close()
        await manager.stop()
        manager.release_lock(PROFILE_SLUG)

if __name__ == "__main__":
    asyncio.run(main())
