"""
End-to-end verification of all 5 browser actions on live X:
1. FollowUser (@sama)
2. LikeTweet (on a tweet from timeline)
3. Retweet (on a tweet from timeline)
4. ComposePost (publish a test tweet and verify it appears on profile)
5. ReplyToTweet (reply to a tweet and verify it was sent)
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from xbot.browser.actions.x_actions import (
    ComposePost, ReplyToTweet, Retweet, FollowUser, LikeTweet
)
from xbot.browser.manager import BrowserManager

PROFILE_SLUG = "test_profile1"
BASE_DIR = "/home/ubuntu/projects/xbot/data/profiles"
OUT_DIR = Path(__file__).parent / "diag_output"
OUT_DIR.mkdir(exist_ok=True)

async def test_all():
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

        # ── 1. TEST FOLLOW ──
        print("\n--- 1. Testing FollowUser (@sama) ---")
        follow_action = FollowUser()
        res_follow = await follow_action.execute(page, username="sama")
        results["follow"] = res_follow
        print(f"Follow result: {res_follow}")
        await page.screenshot(path=str(OUT_DIR / "01_follow_sama.png"))

        # ── 2. GET TWEET FROM TIMELINE FOR LIKE / RETWEET / REPLY ──
        print("\n--- Navigating to Home Timeline ---")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector('[data-testid="tweet"]', timeout=15000)
        await asyncio.sleep(2)

        tweets = await page.query_selector_all('[data-testid="tweet"]')
        print(f"Timeline tweets found: {len(tweets)}")

        tweet_url = None
        for t in tweets:
            link = await t.query_selector('a[href*="/status/"]')
            if link:
                href = await link.get_attribute("href")
                if href and "/status/" in href and not href.endswith("/analytics"):
                    tweet_url = f"https://x.com{href}" if href.startswith("/") else href
                    break
        print(f"Selected tweet URL for testing: {tweet_url}")

        # ── 3. TEST LIKE ──
        print("\n--- 2. Testing LikeTweet ---")
        like_action = LikeTweet()
        res_like = await like_action.execute(page, tweet_url=tweet_url)
        results["like"] = res_like
        print(f"Like result: {res_like}")
        await page.screenshot(path=str(OUT_DIR / "02_like.png"))

        # ── 4. TEST RETWEET ──
        print("\n--- 3. Testing Retweet ---")
        rt_action = Retweet()
        res_rt = await rt_action.execute(page, tweet_url=tweet_url)
        results["retweet"] = res_rt
        print(f"Retweet result: {res_rt}")
        await page.screenshot(path=str(OUT_DIR / "03_retweet.png"))

        # ── 5. TEST COMPOSE POST ──
        print("\n--- 4. Testing ComposePost ---")
        post_action = ComposePost()
        test_text = "Building autonomous agent architectures with strict state machines and verified execution 🚀 #buildinpublic"
        res_post = await post_action.execute(page, text=test_text)
        results["compose_post"] = res_post
        print(f"ComposePost result: {res_post}")
        await page.screenshot(path=str(OUT_DIR / "04_compose_post.png"))

        # Verify on own profile
        await page.goto("https://x.com/jackds1234", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_selector('[data-testid="UserName"]', timeout=12000)
        await asyncio.sleep(2)
        await page.screenshot(path=str(OUT_DIR / "05_own_profile_after_post.png"))

        # ── 6. TEST REPLY TO TWEET ──
        print("\n--- 5. Testing ReplyToTweet ---")
        if tweet_url:
            reply_action = ReplyToTweet()
            res_reply = await reply_action.execute(
                page,
                reply_text="High signal take. State management and verifiable logs are what actually separate production agents from toys.",
                tweet_url=tweet_url,
            )
            results["reply"] = res_reply
            print(f"Reply result: {res_reply}")
            await page.screenshot(path=str(OUT_DIR / "06_reply.png"))
        else:
            results["reply"] = False

        print("\n" + "="*50)
        print("FINAL RESULTS OF LIVE ACTIONS TEST:")
        for k, v in results.items():
            print(f"  {k}: {'✅ SUCCESS' if v else '❌ FAILED'}")
        print("="*50)

    except Exception as e:
        print(f"FATAL EXCEPTION: {e}")
        import traceback; traceback.print_exc()
    finally:
        if context:
            await context.close()
        await manager.stop()
        manager.release_lock(PROFILE_SLUG)

if __name__ == "__main__":
    asyncio.run(test_all())
