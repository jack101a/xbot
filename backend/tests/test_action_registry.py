import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from xbot.contracts.browser import BrowserActionType
from xbot.browser.actions.registry import ACTION_REGISTRY, dispatch_browser_action

def test_registry_is_exhaustive():
    """Invariance test: every BrowserActionType member MUST be registered in ACTION_REGISTRY."""
    missing = set(BrowserActionType) - set(ACTION_REGISTRY.keys())
    assert not missing, f"The following BrowserActionTypes lack registered handlers: {missing}"
    assert len(ACTION_REGISTRY) == len(BrowserActionType), "Mismatch in registered action count"

def test_all_handlers_are_callable_coroutines():
    """Verifies that every registered handler is an async coroutine function."""
    for action_type, handler in ACTION_REGISTRY.items():
        assert callable(handler), f"Handler for {action_type} is not callable"
        assert asyncio.iscoroutinefunction(handler), f"Handler for {action_type} is not a coroutine"

@pytest.mark.asyncio
async def test_dispatch_unknown_action_raises_value_error():
    """Verifies that unknown action types raise ValueError."""
    mock_page = AsyncMock()
    with pytest.raises(ValueError, match="Unknown browser action type"):
        await dispatch_browser_action(mock_page, "completely_invalid_action_xyz")

@pytest.mark.asyncio
async def test_dispatch_routes_to_registered_handler():
    """Verifies that dispatch_browser_action correctly invokes the mapped handler."""
    mock_page = AsyncMock()
    # Test a simple action with mocked handler
    with patch.dict(ACTION_REGISTRY, {BrowserActionType.POST: AsyncMock(return_value={"status": "success"})}):
        res = await dispatch_browser_action(mock_page, BrowserActionType.POST, {"text": "test"})
        assert res["status"] == "success"

@pytest.mark.asyncio
async def test_dispatch_routes_legacy_aliases():
    """Verifies that legacy aliases route to the correct handlers."""
    mock_page = AsyncMock()
    with patch.dict(ACTION_REGISTRY, {BrowserActionType.CHECK_USER_LATEST: AsyncMock(return_value={"status": "success"})}):
        res = await dispatch_browser_action(mock_page, "check_user_tweets", {"username": "jack"})
        assert res["status"] == "success"
