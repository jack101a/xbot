"""
xbot.contracts.ports: Abstract Base Classes defining boundary Ports.
Enforces that pipelines and tasks depend only on interfaces, never concrete drivers.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional
from xbot.contracts.browser import BrowserRequest, BrowserResponse


class BrowserPort(ABC):
    """The ONLY interface through which application code executes browser actions."""

    @abstractmethod
    async def execute(self, request: BrowserRequest) -> BrowserResponse:
        """Execute a browser action envelope and return normalized response."""
        raise NotImplementedError


class LLMPort(ABC):
    """The ONLY interface through which application code performs LLM operations."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.7,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        """Generate text completion from the underlying LLM provider."""
        raise NotImplementedError

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs: Any) -> bytes:
        """Generate image bytes from the underlying visual provider."""
        raise NotImplementedError


class GuardPort(ABC):
    """The ONLY interface through which application code checks safety and limits."""

    @abstractmethod
    async def can_act(self, profile_slug: str, action: str, target_id: str | None = None) -> bool:
        """Check if action is allowed by rate limits, circadian rhythms, and safety policies."""
        raise NotImplementedError

    @abstractmethod
    async def record_action(self, profile_slug: str, action: str, target_id: str | None = None) -> None:
        """Record successful action execution for accounting and limit tracking."""
        raise NotImplementedError

    @abstractmethod
    async def record_failure(self, profile_slug: str, error: str) -> None:
        """Record execution failure for circuit breaker and health telemetry."""
        raise NotImplementedError
