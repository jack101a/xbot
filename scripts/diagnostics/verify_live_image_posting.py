import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from xbot.browser.manager import BrowserManager
from xbot.browser.actions.x_actions import ComposePost
from xbot.ai.meme_renderer import render_side_by_side

async def test_live_image_posting():
    print("1. Generating fresh 4:5 visual meme...")
    img_path = render_side_by_side(
        title="Why Fast Iteration Beats Theoretical Architecture",
        left_header="Over-Engineered Spec",
        left_content="• 14 Microservices\n• Unused Kafka cluster\n• Zero real users",
        right_header="Pragmatic Production",
        right_content="• Fast SQLite / Redis\n• Verified live feedback\n• Scaled with demand",
    )
    abs_img_path = os.path.abspath(img_path)
    print(f"Generated image at: {abs_img_path} (exists: {os.path.exists(abs_img_path)}, size: {os.path.getsize(abs_img_path)} bytes)")

    mgr = BrowserManager(base_profile_dir=Path("/home/ubuntu/projects/xbot/data/profiles"))
    try:
        await mgr.start()
        ctx = await mgr.get_context("test_profile1")
        page = await ctx.new_page()

        print("2. Navigating to X home...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)

        os.makedirs("test-script/live_image_debug", exist_ok=True)
        await page.screenshot(path="test-script/live_image_debug/01_home_loaded.png")
        print("Screenshot 1 saved.")

        # Check inline textarea
        textarea_sel = 'div[data-testid="tweetTextarea_0"], div[role="textbox"][data-testid*="tweetTextarea"]'
        textarea = await page.wait_for_selector(textarea_sel, timeout=10000)
        print(f"Textarea found: {bool(textarea)}")

        # Check file inputs in DOM
        file_inputs = await page.query_selector_all('input[type="file"]')
        print(f"Found {len(file_inputs)} file inputs on page.")
        for idx, fi in enumerate(file_inputs):
            testid = await fi.get_attribute("data-testid")
            accept = await fi.get_attribute("accept")
            print(f"  Input {idx}: data-testid='{testid}', accept='{accept}'")

        action = ComposePost()
        post_text = "Pragmatic engineering: shipping real features > debating hypothetical scale. 🍿"
        
        print("3. Executing ComposePost with image...")
        success = await action.execute(page, text=post_text, media_paths=[abs_img_path])
        print(f"ComposePost execution success: {success}")

        await page.screenshot(path="test-script/live_image_debug/02_post_executed.png")
        print("Screenshot 2 saved.")

        await asyncio.sleep(4)
        await page.goto("https://x.com", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(3)
        await page.screenshot(path="test-script/live_image_debug/03_profile_feed.png")
        print("Screenshot 3 saved.")

        await ctx.close()
    finally:
        await mgr.stop()

if __name__ == "__main__":
    asyncio.run(test_live_image_posting())
