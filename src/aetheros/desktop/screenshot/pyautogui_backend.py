from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pyautogui

from ...core.interfaces.screenshot_controller import (
    ScreenshotController,
)


class PyAutoGuiScreenshot(ScreenshotController):
    """
    PyAutoGUI implementation of ScreenshotController.
    """

    def __init__(
        self,
        output_dir: str | Path = "screenshots",
    ) -> None:

        self._output_dir = Path(output_dir)

        self._output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ==========================================================
    # Capture
    # ==========================================================

    def capture(self) -> Path:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        path = (
            self._output_dir
            / f"screenshot_{timestamp}.png"
        )

        image = pyautogui.screenshot()

        image.save(path)

        return path

    # ==========================================================
    # Region
    # ==========================================================

    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Path:

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )

        path = (
            self._output_dir
            / f"region_{timestamp}.png"
        )

        image = pyautogui.screenshot(
            region=(
                x,
                y,
                width,
                height,
            )
        )

        image.save(path)

        return path

    # ==========================================================
    # Screen size
    # ==========================================================

    def screen_size(self) -> tuple[int, int]:

        size = pyautogui.size()

        return (
            size.width,
            size.height,
        )