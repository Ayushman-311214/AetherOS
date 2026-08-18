from __future__ import annotations

from pathlib import Path

from ...core.interfaces.screenshot_controller import (
    ScreenshotController,
)
from ...core.logging import get_logger


class ScreenshotService:
    """
    High-level screenshot service.
    """

    def __init__(
        self,
        controller: ScreenshotController,
    ) -> None:

        self._controller = controller

        self._logger = get_logger(
            "screenshot"
        )

    # ==========================================================
    # Capture
    # ==========================================================

    async def capture(self) -> Path:

        self._logger.debug(
            "Capturing full screen."
        )

        return self._controller.capture()

    # ==========================================================
    # Region
    # ==========================================================

    async def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Path:

        self._logger.debug(
            "Capturing screen region "
            "(%s, %s, %s, %s).",
            x,
            y,
            width,
            height,
        )

        return self._controller.capture_region(
            x=x,
            y=y,
            width=width,
            height=height,
        )

    # ==========================================================
    # Size
    # ==========================================================

    async def screen_size(
        self,
    ) -> tuple[int, int]:

        return self._controller.screen_size()