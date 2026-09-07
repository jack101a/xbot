from __future__ import annotations

import logging
import uuid
from pathlib import Path

from playwright.async_api import Page

logger = logging.getLogger(__name__)


class BaseAction:
    """
    Base action class providing failure recovery, logging, and screenshot tools.
    """

    def __init__(
        self,
        screenshot_dir: str | Path | None = None,
    ) -> None:
        from xbot.config import settings
        if screenshot_dir is None:
            self.screenshot_dir = Path(settings.BASE_PROFILE_DIR).parent / "screenshots"
        else:
            self.screenshot_dir = Path(screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def capture_failure(self, page: Page, action_name: str) -> str:
        """
        Takes a screenshot of the page upon action failure and returns the filepath.
        """
        filename = f"fail_{action_name}_{uuid.uuid4().hex}.png"
        filepath = self.screenshot_dir / filename
        try:
            await page.screenshot(path=str(filepath))
            logger.info("Saved failure screenshot to: %s", filepath)
            return str(filepath)
        except Exception as e:
            logger.error("Failed to capture screenshot: %s", e)
            return ""
