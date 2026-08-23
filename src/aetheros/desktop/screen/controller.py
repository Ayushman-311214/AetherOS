from __future__ import annotations

from pathlib import Path
from typing import Any

from ...core.interfaces.screen_controller import ScreenshotController
from ...core.logging import get_logger


class ScreenService:
    """
    High-level screen service.

    Responsible for screen capture operations.

    The concrete implementation is delegated to the
    configured ScreenController backend.
    """

    def __init__(
        self,
        controller: ScreenshotController,
    ) -> None:

        self._controller = controller
        self._logger = get_logger("screen")

    # ==========================================================
    # Screenshot
    # ==========================================================

    async def capture(
        self,
    ) -> Any:
        """
        Capture the primary screen.

        Returns:
            Backend-specific image object.
        """

        self._logger.debug(
            "Capturing primary screen."
        )

        return self._controller.capture()

    async def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> Any:
        """
        Capture a screen region.
        """

        self._logger.debug(
            "Capturing region (%s,%s,%s,%s)",
            left,
            top,
            width,
            height,
        )

        return self._controller.capture_region(
            left=left,
            top=top,
            width=width,
            height=height,
        )

    # ==========================================================
    # Save
    # ==========================================================

    async def save(
        self,
        image: Any,
        path: str | Path,
    ) -> None:
        """
        Save an image to disk.
        """

        self._controller.save(
            image=image,
            path=path,
        )

    # ==========================================================
    # Information
    # ==========================================================

    async def size(
        self,
    ) -> tuple[int, int]:
        """
        Returns the primary screen size.
        """

        return self._controller.size()

    async def monitors(
        self,
    ) -> list[dict]:
        """
        Returns information about connected monitors.
        """

        return self._controller.monitors()