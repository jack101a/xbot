from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)

# Memory & DOM limits for tab auto-recycling
MAX_TAB_MEMORY_BYTES = 150 * 1024 * 1024  # 150 MB
MAX_TAB_DOM_NODES = 2500                   # 2,500 DOM elements
MAX_WORKER_TABS = 2                        # Up to 2 burst worker tabs (Tabs 3 & 4)


def _is_tab_closed(page: Page | None) -> bool:
    if page is None:
        return True
    try:
        res = page.is_closed()
        if asyncio.iscoroutine(res):
            # If mock returned a coroutine, close it to avoid warning
            res.close()
            return False
        return bool(res)
    except Exception:
        return True


class TabPool:
    """
    Dedicated 4-Tab Pool for a profile's persistent browser context:
    - Tab 1: Main Home Feed Anchor (https://x.com/home) - Never navigates away.
    - Tab 2: Research & Trend Harvester (https://x.com/explore & Search).
    - Tabs 3 & 4: Ephemeral Worker Tabs for quick tasks, auto-closed after execution.
    """

    def __init__(self, profile_slug: str, context: BrowserContext) -> None:
        self.profile_slug = profile_slug
        self.context = context
        self._home_page: Page | None = None
        self._research_page: Page | None = None
        self._worker_semaphore = asyncio.Semaphore(MAX_WORKER_TABS)
        self._active_workers: set[Page] = set()
        self._lock = asyncio.Lock()

    async def get_home_page(self) -> Page:
        """
        Retrieves the persistent Tab 1 anchored on https://x.com/home.
        Creates and navigates to Home if not already open.
        """
        async with self._lock:
            if self._home_page and not _is_tab_closed(self._home_page):
                if hasattr(self._home_page, "url") and "x.com/home" not in str(self._home_page.url):
                    try:
                        await self._home_page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
                    except Exception as e:
                        logger.warning("TabPool [%s]: Home page navigation warning: %s", self.profile_slug, e)
                return self._home_page

            # Create new Home page
            if self.context.pages:
                self._home_page = self.context.pages[0]
            else:
                self._home_page = await self.context.new_page()

            if hasattr(self._home_page, "set_default_timeout"):
                try:
                    res = self._home_page.set_default_timeout(25000)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass
            try:
                await self._home_page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
            except Exception as e:
                logger.warning("TabPool [%s]: Initial home navigation error: %s", self.profile_slug, e)

            logger.info("TabPool [%s]: Tab 1 (Home Feed Anchor) initialized.", self.profile_slug)
            return self._home_page

    async def get_research_page(self) -> Page:
        """
        Retrieves or initializes Tab 2 dedicated to live trend & media harvesting.
        """
        async with self._lock:
            if self._research_page and not _is_tab_closed(self._research_page):
                return self._research_page

            self._research_page = await self.context.new_page()
            if hasattr(self._research_page, "set_default_timeout"):
                try:
                    res = self._research_page.set_default_timeout(25000)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass
            try:
                await self._research_page.goto("https://x.com/explore", wait_until="domcontentloaded", timeout=25000)
            except Exception as e:
                logger.warning("TabPool [%s]: Initial explore navigation error: %s", self.profile_slug, e)

            logger.info("TabPool [%s]: Tab 2 (Research & Trend Harvester) initialized.", self.profile_slug)
            return self._research_page

    @asynccontextmanager
    async def acquire_worker(self, name: str = "worker") -> AsyncIterator[Page]:
        """
        Async context manager to acquire an ephemeral worker tab (Tab 3 or 4).
        Automatically ensures the tab is closed on exit to prevent RAM bloat.
        """
        async with self._worker_semaphore:
            worker_page: Page | None = None
            try:
                worker_page = await self.context.new_page()
                if hasattr(worker_page, "set_default_timeout"):
                    try:
                        res = worker_page.set_default_timeout(30000)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception:
                        pass
                self._active_workers.add(worker_page)
                logger.info("TabPool [%s]: Worker tab '%s' opened (Active workers: %d).", self.profile_slug, name, len(self._active_workers))
                yield worker_page
            finally:
                if worker_page is not None:
                    self._active_workers.discard(worker_page)
                    if not _is_tab_closed(worker_page):
                        try:
                            await worker_page.close()
                            logger.info("TabPool [%s]: Worker tab '%s' closed cleanly (Active workers: %d).", self.profile_slug, name, len(self._active_workers))
                        except Exception as e:
                            logger.warning("TabPool [%s]: Error closing worker tab '%s': %s", self.profile_slug, name, e)

    async def check_and_recycle_bloated_tabs(self) -> dict[str, Any]:
        """
        RAM Watchdog: Inspects memory and DOM node counts on persistent tabs (Tabs 1 & 2).
        If bloated, safely recycles the tab without losing authentication or cookies.
        """
        recycled = []
        async with self._lock:
            # 1. Check Tab 1 (Home Anchor)
            if self._home_page and not _is_tab_closed(self._home_page):
                stats = await self._get_tab_stats(self._home_page)
                if stats["dom_nodes"] > MAX_TAB_DOM_NODES or stats["js_heap_bytes"] > MAX_TAB_MEMORY_BYTES:
                    logger.info("TabPool [%s]: Tab 1 bloated (DOM: %d, RAM: %.1f MB). Recycling...",
                                self.profile_slug, stats["dom_nodes"], stats["js_heap_bytes"] / (1024 * 1024))
                    try:
                        await self._home_page.close()
                    except Exception:
                        pass
                    self._home_page = await self.context.new_page()
                    await self._home_page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
                    recycled.append("home_tab")

            # 2. Check Tab 2 (Research Harvester)
            if self._research_page and not _is_tab_closed(self._research_page):
                stats = await self._get_tab_stats(self._research_page)
                if stats["dom_nodes"] > MAX_TAB_DOM_NODES or stats["js_heap_bytes"] > MAX_TAB_MEMORY_BYTES:
                    logger.info("TabPool [%s]: Tab 2 bloated (DOM: %d, RAM: %.1f MB). Recycling...",
                                self.profile_slug, stats["dom_nodes"], stats["js_heap_bytes"] / (1024 * 1024))
                    try:
                        await self._research_page.close()
                    except Exception:
                        pass
                    self._research_page = await self.context.new_page()
                    await self._research_page.goto("https://x.com/explore", wait_until="domcontentloaded", timeout=25000)
                    recycled.append("research_tab")

        return {"recycled": recycled, "active_workers": len(self._active_workers)}

    async def _get_tab_stats(self, page: Page) -> dict[str, int]:
        """Calculates DOM element count and approximate JS heap size."""
        try:
            dom_nodes = await page.evaluate("() => document.getElementsByTagName('*').length")
            heap_size = await page.evaluate("() => window.performance && window.performance.memory ? window.performance.memory.usedJSHeapSize : 0")
            return {"dom_nodes": int(dom_nodes or 0), "js_heap_bytes": int(heap_size or 0)}
        except Exception:
            return {"dom_nodes": 0, "js_heap_bytes": 0}

    async def close_all(self) -> None:
        """Closes all open tabs in the pool."""
        async with self._lock:
            for w in list(self._active_workers):
                if not w.is_closed():
                    try:
                        await w.close()
                    except Exception:
                        pass
            self._active_workers.clear()

            if self._home_page and not self._home_page.is_closed():
                try:
                    await self._home_page.close()
                except Exception:
                    pass
                self._home_page = None

            if self._research_page and not self._research_page.is_closed():
                try:
                    await self._research_page.close()
                except Exception:
                    pass
                self._research_page = None


class TabPoolManager:
    """Global manager for profile TabPool instances."""

    def __init__(self) -> None:
        self._pools: dict[str, TabPool] = {}
        self._lock = asyncio.Lock()

    async def get_pool(self, profile_slug: str, context: BrowserContext) -> TabPool:
        """Gets or creates the dedicated TabPool for a profile context."""
        async with self._lock:
            if profile_slug not in self._pools or self._pools[profile_slug].context != context:
                self._pools[profile_slug] = TabPool(profile_slug, context)
            return self._pools[profile_slug]

    async def release_pool(self, profile_slug: str) -> None:
        """Closes and unregisters a profile's TabPool."""
        async with self._lock:
            pool = self._pools.pop(profile_slug, None)
            if pool:
                await pool.close_all()


# Global singleton manager instance
tab_pool_manager = TabPoolManager()
