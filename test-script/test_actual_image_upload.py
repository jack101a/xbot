import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from xbot.browser.manager import BrowserManager
from xbot.browser.actions.x_actions import ComposePost, _attach_media_files
from xbot.ai.meme_renderer import render_side_by_side

async def test():
    print("1. Generating 4:5 visual image...")
    img_path = render_side_by_side(
        title="Why Fast Iteration Beats Theoretical Architecture",
        left_header="Over-Engineered Spec",
        left_content="• 14 Microservices\n• Unused Kafka cluster\n• Zero real users",
        right_header="Pragmatic Production",
        right_content="• Fast SQLite / Redis\n• Verified live feedback\n• Scaled with demand",
    )
    abs_img_path = os.path.abspath(img_path)
    print(f"Image path: {abs_img_path}")

    mgr = BrowserManager(base_profile_dir=Path("/home/ubuntu/projects/xbot/data/profiles"))
    try:
        await mgr.start()
        ctx = await mgr.get_context("test_profile1")
        page = await ctx.new_page()

        print("2. Navigating to https://x.com...")
        await page.goto("https://x.com", wait_until="load", timeout=30000)
        
        # Wait for home page to hydrate
        await page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=20000)
        print("Home page hydrated and textarea visible!")

        # Focus textarea and type text
        textarea = await page.query_selector('div[data-testid="tweetTextarea_0"]')
        await textarea.click()
        await asyncio.sleep(1)
        await page.keyboard.type("Pragmatic engineering: shipping real features beats debating hypothetical scale. 🍿", delay=30)
        await asyncio.sleep(1)

        os.makedirs("test-script/live_image_debug", exist_ok=True)
        await page.screenshot(path="test-script/live_image_debug/stage1_text_typed.png")
        print("Screenshot stage 1 saved.")

        # Attach image
        print("3. Attaching media file...")
        file_input = await page.wait_for_selector('input[data-testid="fileInput"]', state="attached", timeout=10000)
        await file_input.set_input_files([abs_img_path])
        print("set_input_files called!")

        # Wait 4 seconds for image upload preview to render
        await asyncio.sleep(4)
        await page.screenshot(path="test-script/live_image_debug/stage2_image_attached.png")
        print("Screenshot stage 2 saved.")

        # Check for attachment preview or tweet photo element
        attachment_el = await page.query_selector('[data-testid="attachments"], [data-testid="tweetPhoto"], div[role="group"][aria-label*="Media"], img[alt*="Image"]')
        print(f"Attachment preview element detected in DOM: {bool(attachment_el)}")

        # Click Post button
        submit_btn = await page.query_selector('button[data-testid="tweetButtonInline"]')
        print(f"Post button found: {bool(submit_btn)}")
        if submit_btn:
            await submit_btn.click()
            print("Post button clicked!")
            await asyncio.sleep(6)

        await page.screenshot(path="test-script/live_image_debug/stage3_posted.png")
        print("Screenshot stage 3 saved.")

        # Navigate to user's profile to verify live published post with image
        print("4. Checking profile for published tweet...")
        await page.goto("https://x.com/jackds1234", wait_until="load", timeout=25000)
        await asyncio.sleep(4)
        await page.screenshot(path="test-script/live_image_debug/stage4_profile_verified.png")
        print("Screenshot stage 4 saved.")

        # Check for tweet photo on profile
        tweet_photos = await page.query_selector_all('[data-testid="tweetPhoto"], [data-testid="tweet"] img[src*="pbs.twimg.com/media"]')
        print(f"Live tweet photos found on profile: {len(tweet_photos)}")

        await ctx.close()
    finally:
        await mgr.stop()

if __name__ == "__main__":
    asyncio.run(test())
