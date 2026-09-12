import time
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from celery.signals import worker_process_shutdown
from xbot.celery_app import celery_app, on_worker_process_shutdown
from xbot.infra.llm.chatgpt_bridge.browser import BrowserManager
from xbot.infra.llm.chatgpt_bridge.core import ChatGPT


def test_celery_config_and_beat_schedule():
    """Verify Celery conf limits, updated browser-queue schedule, and removal of watchdog."""
    # 1. Check child worker limits
    assert celery_app.conf.worker_max_tasks_per_child == 10
    assert celery_app.conf.worker_max_memory_per_child == 300000

    # 2. Check beat schedule updates
    schedule = celery_app.conf.beat_schedule
    assert "browser-queue-worker-every-60s" in schedule
    assert schedule["browser-queue-worker-every-60s"]["schedule"] == 60.0
    assert schedule["browser-queue-worker-every-60s"]["options"] == {
        "queue": "browser",
        "expires": 60.0,
    }
    assert "browser-queue-worker-every-10s" not in schedule
    assert "supervisor-watchdog-every-60s" not in schedule


def test_celery_worker_process_shutdown_signal():
    """Verify worker_process_shutdown signal calls reset_chatgpt_instance."""
    with patch("xbot.ai.chatgpt_adapter.reset_chatgpt_instance") as mock_reset:
        on_worker_process_shutdown()
        mock_reset.assert_called_once()


def test_browser_manager_init_and_touch():
    """Verify BrowserManager initialization and touch behavior."""
    mgr = BrowserManager(headless=True)
    assert mgr._last_active_time == 0.0
    assert mgr._idle_timeout_seconds == 300.0
    assert mgr._idle_task is None

    t_before = time.time()
    mgr.touch()
    t_after = time.time()
    assert t_before <= mgr._last_active_time <= t_after


@pytest.mark.asyncio
async def test_browser_manager_launch_args():
    """Verify Chromium launch args in BrowserManager.start()."""
    mgr = BrowserManager(headless=True)

    expected_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--no-zygote",
        "--disable-background-networking",
        "--disable-renderer-backgrounding",
    ]

    mock_playwright = AsyncMock()
    mock_chromium = AsyncMock()
    mock_playwright.chromium = mock_chromium
    mock_context = AsyncMock()
    mock_chromium.launch_persistent_context.return_value = mock_context

    with patch(
        "xbot.infra.llm.chatgpt_bridge.browser.async_playwright"
    ) as mock_ap_cls, patch(
        "xbot.infra.llm.chatgpt_bridge.browser._ensure_virtual_display"
    ):
        mock_ap_inst = AsyncMock()
        mock_ap_inst.start.return_value = mock_playwright
        mock_ap_cls.return_value = mock_ap_inst

        await mgr.start()

        mock_chromium.launch_persistent_context.assert_called_once()
        _, kwargs = mock_chromium.launch_persistent_context.call_args
        assert "args" in kwargs
        for arg in expected_args:
            assert arg in kwargs["args"]
        assert mgr._last_active_time > 0.0


@pytest.mark.asyncio
async def test_browser_manager_close_if_idle():
    """Verify close_if_idle closes context only after idle_timeout_seconds."""
    mgr = BrowserManager(headless=True)
    mgr.stop = AsyncMock()

    # 1. No context active -> returns False
    mgr._context = None
    mgr._last_active_time = time.time() - 500.0
    assert await mgr.close_if_idle() is False
    mgr.stop.assert_not_called()

    # 2. Context active, but active recently -> returns False
    mgr._context = MagicMock()
    mgr._last_active_time = time.time() - 10.0
    assert await mgr.close_if_idle() is False
    mgr.stop.assert_not_called()

    # 3. Context active and idle >= 300s -> calls stop() and returns True
    mgr._last_active_time = time.time() - 301.0
    assert await mgr.close_if_idle() is True
    mgr.stop.assert_called_once()


@pytest.mark.asyncio
async def test_chatgpt_core_touch_and_close():
    """Verify ChatGPT.ask() and generate_image() touch browser, and close() cleans up."""
    chatgpt = ChatGPT(headless=True)
    chatgpt.browser.touch = MagicMock()
    chatgpt._ensure_started = AsyncMock()
    chatgpt._track = AsyncMock()

    # 1. ask() touches browser
    chatgpt.http.ask = AsyncMock(return_value={"text": "hello", "conversation_id": "c1"})
    res = await chatgpt.ask("test prompt")
    assert res["text"] == "hello"
    assert chatgpt.browser.touch.call_count >= 2

    # 2. generate_image() touches browser
    chatgpt.browser.touch.reset_mock()
    chatgpt.ui.generate_image = AsyncMock(
        return_value={"path": "/tmp/img.png", "prompt": "draw cat", "conversation_id": "c2"}
    )
    img_res = await chatgpt.generate_image("draw cat")
    assert img_res["path"] == "/tmp/img.png"
    assert chatgpt.browser.touch.call_count >= 2

    # 3. close() cleans up browser and resets _started
    chatgpt._started = True
    chatgpt.browser.stop = AsyncMock()
    chatgpt.close()
    assert chatgpt._started is False
