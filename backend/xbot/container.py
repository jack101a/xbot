"""
xbot.container: Dependency Injection Container for Ports and Adapters.
Wires abstract ports to concrete infrastructure adapters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from sqlalchemy.ext.asyncio import AsyncSession

from xbot.contracts.ports import BrowserPort, LLMPort, GuardPort
from xbot.database import AsyncSessionLocal
@dataclass
class Container:
    """Central composition root for application services and pipelines."""
    browser: BrowserPort
    llm: LLMPort
    guard: GuardPort
    db_session_factory: Callable[[], AsyncSession] = AsyncSessionLocal


_global_container: Container | None = None


def get_container(
    browser: BrowserPort | None = None,
    llm: LLMPort | None = None,
    guard: GuardPort | None = None,
) -> Container:
    """Retrieve or build the global DI container."""
    global _global_container
    if _global_container is None:
        if browser is None:
            from xbot.infra.browser.queued_adapter import QueuedBrowserAdapter
            browser = QueuedBrowserAdapter()
        if llm is None:
            from xbot.infra.llm.adapter import UnifiedLLMAdapter
            llm = UnifiedLLMAdapter()
        if guard is None:
            from xbot.infra.guard.adapter import CentralGuardAdapter
            guard = CentralGuardAdapter()

        _global_container = Container(
            browser=browser,
            llm=llm,
            guard=guard,
            db_session_factory=AsyncSessionLocal,
        )
    return _global_container


def reset_container() -> None:
    """Reset the DI container (used in unit testing for mock injection)."""
    global _global_container
    _global_container = None
