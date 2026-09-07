"""
xbot.pipelines.browser_queue.worker: Re-export shim for backward compatibility.
Implementation has moved to xbot.infra.browser.queue.worker.
"""
from xbot.infra.browser.queue.worker import (
    execute_browser_action,
    process_browser_queue,
    process_single_job,
    _process_browser_queue_async,
)

__all__ = [
    "execute_browser_action",
    "process_browser_queue",
    "process_single_job",
    "_process_browser_queue_async",
]
