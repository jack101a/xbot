"""
xbot.contracts: Pydantic Data Transfer Objects and Abstract Ports.
Defines the architectural boundary between application logic and infrastructure adapters.
"""
from xbot.contracts.browser import (
    BrowserActionType,
    BrowserRequest,
    BrowserResponse,
    ActionResult,
    TweetData,
    NotificationData,
    FollowListResult,
    ScrapeResult,
)
from xbot.contracts.ports import (
    BrowserPort,
    LLMPort,
    GuardPort,
)
from xbot.contracts.pipeline import (
    PipelineResult,
)

__all__ = [
    "BrowserActionType",
    "BrowserRequest",
    "BrowserResponse",
    "ActionResult",
    "TweetData",
    "NotificationData",
    "FollowListResult",
    "ScrapeResult",
    "BrowserPort",
    "LLMPort",
    "GuardPort",
    "PipelineResult",
]
