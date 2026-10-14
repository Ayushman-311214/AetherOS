from __future__ import annotations

from pathlib import Path

import numpy as np

from ...core.interfaces.screen_controller import ScreenController
from ...core.logging import get_logger


class ScreenService:
    """
    High-level screen service.

    Responsible for screen capture operations.

    The concrete implementation is delegated to the
    configured ScreenController backend.

    Every frame returned here is a **BGR** ``uint8`` array — see
    :class:`~aetheros.core.interfaces.screen_controller.ScreenController`. The
    vision engine wraps it with ``Image.from_numpy(frame)``, whose default
    colour space matches.
    """

    def __init__(
        self,
        controller: ScreenController,
    ) -> None:

        self._controller = controller
        self._logger = get_logger("screen")

    # ==========================================================
    # Screenshot
    # ==========================================================

    async def capture(self) -> np.ndarray:
        """
        Capture the primary screen.

        Returns:
            BGR image array of shape (height, width, 3).
        """

        self._logger.debug("Capturing primary screen.")

        return self._controller.capture()

    async def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        """
        Capture a screen region.
        """

        # bind(), not %-style args: loguru formats with str.format, so
        # positional args would be dropped silently.
        self._logger.bind(
            left=left,
            top=top,
            width=width,
            height=height,
        ).debug("Capturing screen region.")

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
        image: np.ndarray,
        path: str | Path,
    ) -> None:
        """
        Save a captured frame to disk.
        """

        self._controller.save(
            image=image,
            path=path,
        )

    # ==========================================================
    # Information
    # ==========================================================

    async def size(self) -> tuple[int, int]:
        """
        Returns the primary screen size as (width, height).
        """

        return self._controller.size()

    async def monitors(self) -> list[dict]:
        """
        Returns information about connected monitors.
        """

        return self._controller.monitors()

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def shutdown(self) -> None:
        """
        Release the backend's screen handle.
        """

        self._logger.debug("Releasing screen capture backend.")

        self._controller.close()
