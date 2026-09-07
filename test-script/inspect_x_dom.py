import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from xbot.browser.manager import BrowserManager

async def inspect():
    mgr = BrowserManager(base_profile_dir=Path("/home/ubuntu/projects/xbot/data/profiles"))
    try:
        await mgr.start()
        ctx = await mgr.get_context("test_profile1")
        page = await ctx.new_page()

        print("Navigating to https://x.com...")
        await page.goto("https://x.com", wait_until="load", timeout=30000)
        
        # Wait up to 15 seconds for React hydration / navigation
        for i in range(15):
            await asyncio.sleep(1)
            url = page.url
            title = await page.title()
            body_text = await page.evaluate("() => document.body.innerText")
            print(f"[{i}s] URL: {url} | Title: {title} | Body len: {len(body_text)}")
            if "home" in url or len(body_text) > 100:
                print("Page hydrated!")
                break

        await page.screenshot(path="test-script/live_image_debug/dom_inspected.png")
        print("Screenshot saved.")

        # Check for tweetTextarea or fileInput
        inputs = await page.query_selector_all("input")
        print(f"Total inputs found: {len(inputs)}")
        for inp in inputs:
            itype = await inp.get_attribute("type")
            itestid = await inp.get_attribute("data-testid")
            iaccept = await inp.get_attribute("accept")
            print(f"  Input: type='{itype}', testid='{itestid}', accept='{iaccept}'")

        textareas = await page.query_selector_all("[data-testid*='tweetTextarea'], [contenteditable='true']")
        print(f"Total textareas / contenteditables: {len(textareas)}")
        for ta in textareas:
            t_testid = await ta.get_attribute("data-testid")
            t_role = await ta.get_attribute("role")
            print(f"  Textarea: testid='{t_testid}', role='{t_role}'")

        await ctx.close()
    finally:
        await mgr.stop()

if __name__ == "__main__":
    asyncio.run(inspect())
