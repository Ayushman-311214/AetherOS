from __future__ import annotations

from pathlib import Path
from typing import Any

import mss
import mss.tools
import numpy as np
from PIL import Image

from core.interfaces.screen_controller import ScreenController


class MSSScreen(ScreenController):
    """
    MSS implementation of the ScreenController interface.

    Provides high-performance screen capture with support for
    full-screen, region, and multi-monitor captures.
    """

    def __init__(self) -> None:
        self._sct = mss.mss()

    # ==========================================================
    # Screen Capture
    # ==========================================================

    def capture(self) -> np.ndarray:
        """
        Capture the primary monitor.

        Returns:
            RGB NumPy image.
        """

        monitor = self._sct.monitors[1]

        screenshot = self._sct.grab(monitor)

        return np.array(screenshot)[:, :, :3]

    def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        """
        Capture a rectangular region.
        """

        monitor = {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }

        screenshot = self._sct.grab(monitor)

        return np.array(screenshot)[:, :, :3]

    # ==========================================================
    # Save
    # ==========================================================

    def save(
        self,
        image: Any,
        path: str | Path,
    ) -> None:
        """
        Save an image.
        """

        image = Image.fromarray(image)

        image.save(path)

    # ==========================================================
    # Information
    # ==========================================================

    def size(
        self,
    ) -> tuple[int, int]:
        """
        Returns primary monitor size.
        """

        monitor = self._sct.monitors[1]

        return (
            monitor["width"],
            monitor["height"],
        )

    def monitors(
        self,
    ) -> list[dict]:
        """
        Returns monitor metadata.
        """

        return list(self._sct.monitors[1:])

    # ==========================================================
    # Capture by Monitor
    # ==========================================================

    def capture_monitor(
        self,
        monitor_index: int,
    ) -> np.ndarray:
        """
        Capture a specific monitor.
        """

        monitor = self._sct.monitors[monitor_index]

        screenshot = self._sct.grab(monitor)

        return np.array(screenshot)[:, :, :3]

    # ==========================================================
    # Cleanup
    # ==========================================================

    def close(self) -> None:
        """
        Release MSS resources.
        """

        self._sct.close()