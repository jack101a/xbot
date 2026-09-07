"""
xbot.infra.browser: Browser infrastructure adapters and execution managers.
"""
from xbot.infra.browser.adapter import PlaywrightBrowserAdapter
from xbot.infra.browser.queued_adapter import QueuedBrowserAdapter

__all__ = [
    "PlaywrightBrowserAdapter",
    "QueuedBrowserAdapter",
]
