import pytest

from xbot.browser.manager import BrowserManager


@pytest.mark.asyncio
async def test_browser_manager_flow() -> None:
    """
    Verifies BrowserManager startup, Redis-based locking, context creation,
    and anti-detection stealth injection.
    """
    manager = BrowserManager()
    await manager.start()

    # 1. Verify Redis locking mechanism
    profile_slug = "stealth_test_profile"
    manager.release_lock(profile_slug)  # Clear any legacy lock

    assert manager.acquire_lock(profile_slug) is True
    assert manager.acquire_lock(profile_slug) is False  # Second acquire fails
    manager.release_lock(profile_slug)
    assert manager.acquire_lock(profile_slug) is True  # Re-acquire succeeds
    manager.release_lock(profile_slug)

    # 2. Launch persistent context
    context = await manager.get_context(profile_slug)
    assert context is not None

    # 3. Create a new page and navigate to trigger init scripts
    page = await context.new_page()
    await page.goto("about:blank")

    # 4. Verify that the stealth script runs and masks navigator.webdriver
    webdriver_val = await page.evaluate("navigator.webdriver")
    assert webdriver_val is None or webdriver_val is False

    # 5. Verify custom init scripts (deviceMemory, hardwareConcurrency)
    device_memory = await page.evaluate("navigator.deviceMemory")
    assert device_memory in [4, 8, 16]

    hardware_concurrency = await page.evaluate("navigator.hardwareConcurrency")
    assert hardware_concurrency in [4, 6, 8, 12]

    # Clean up browser and playwright instances
    await context.close()
    await manager.stop()
