from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from xbot.browser.tab_pool import (
    TabPool,
    TabPoolManager,
    MAX_TAB_DOM_NODES,
    MAX_TAB_MEMORY_BYTES,
)


@pytest.mark.asyncio
async def test_tab_pool_home_page_persistence():
    mock_context = MagicMock()
    mock_page = MagicMock()
    mock_page.is_closed = MagicMock(return_value=False)
    mock_page.url = "https://x.com/home"
    mock_page.goto = AsyncMock()
    mock_page.set_default_timeout = MagicMock()
    mock_context.pages = [mock_page]
    mock_context.new_page = AsyncMock(return_value=mock_page)

    pool = TabPool("test_profile", mock_context)
    page1 = await pool.get_home_page()
    page2 = await pool.get_home_page()

    assert page1 == page2
    assert page1 == mock_page


@pytest.mark.asyncio
async def test_tab_pool_worker_acquisition_and_auto_close():
    mock_context = MagicMock()
    mock_worker_page = MagicMock()
    mock_worker_page.is_closed = MagicMock(return_value=False)
    mock_worker_page.close = AsyncMock()
    mock_worker_page.set_default_timeout = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_worker_page)

    pool = TabPool("test_profile", mock_context)

    async with pool.acquire_worker(name="test_sniper") as worker:
        assert worker == mock_worker_page
        assert len(pool._active_workers) == 1

    # Worker must be closed cleanly after exiting context manager
    mock_worker_page.close.assert_awaited_once()
    assert len(pool._active_workers) == 0


@pytest.mark.asyncio
async def test_ram_watchdog_auto_recycle():
    mock_context = MagicMock()
    bloated_page = MagicMock()
    bloated_page.is_closed = MagicMock(return_value=False)
    bloated_page.url = "https://x.com/home"
    bloated_page.close = AsyncMock()
    bloated_page.goto = AsyncMock()
    bloated_page.set_default_timeout = MagicMock()

    # Simulate bloated DOM and JS Heap
    async def mock_eval(expr):
        if "getElementsByTagName" in expr:
            return 3500  # Above 2500 limit
        if "usedJSHeapSize" in expr:
            return 180 * 1024 * 1024  # Above 150MB limit
        return 0

    bloated_page.evaluate = AsyncMock(side_effect=mock_eval)

    fresh_page = MagicMock()
    fresh_page.is_closed = MagicMock(return_value=False)
    fresh_page.url = "https://x.com/home"
    fresh_page.close = AsyncMock()
    fresh_page.goto = AsyncMock()
    fresh_page.set_default_timeout = MagicMock()
    fresh_page.evaluate = AsyncMock(return_value=100)

    mock_context.pages = [bloated_page]
    mock_context.new_page = AsyncMock(return_value=fresh_page)

    pool = TabPool("test_profile", mock_context)
    await pool.get_home_page()

    # Trigger watchdog check
    result = await pool.check_and_recycle_bloated_tabs()

    assert "home_tab" in result["recycled"]
    bloated_page.close.assert_awaited_once()
    assert pool._home_page == fresh_page


@pytest.mark.asyncio
async def test_tab_pool_manager_singleton():
    manager = TabPoolManager()
    mock_context = MagicMock()
    mock_context.pages = []

    pool1 = await manager.get_pool("test_profile", mock_context)
    pool2 = await manager.get_pool("test_profile", mock_context)

    assert pool1 == pool2

    await manager.release_pool("test_profile")
    assert "test_profile" not in manager._pools
