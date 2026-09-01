from __future__ import annotations

from pathlib import Path

import cv2
import mss
import numpy as np

from ...core.errors.vision_error import VisionError
from ...core.errors.base_error import ErrorContext
from ...core.interfaces.screen_controller import ScreenController


class MSSScreen(ScreenController):
    """
    MSS implementation of the ScreenController interface.

    Provides high-performance screen capture with support for
    full-screen, region, and multi-monitor captures.
    """

    def __init__(self) -> None:
        try:
            self._sct = mss.mss()

        except Exception as exc:
            # No display (a CI container, a headless session): mss raises on
            # construction rather than on first grab, so the failure has to be
            # translated here or the DI container hands out a half-built object.
            raise VisionError(
                code="SCREEN_UNAVAILABLE",
                message="Screen capture backend could not be initialized.",
                hint=(
                    "MSS needs an attached display. On a headless machine, "
                    "capture-based tools are unavailable."
                ),
                context=ErrorContext(
                    module="desktop.screen",
                    operation="initialize",
                ),
                cause=exc,
            ) from exc

    # ==========================================================
    # Screen Capture
    # ==========================================================

    def capture(self) -> np.ndarray:
        """
        Capture the primary monitor.

        Returns:
            BGR NumPy image of shape (height, width, 3).
        """

        return self._grab(self._sct.monitors[1])

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

        if width <= 0 or height <= 0:
            raise VisionError(
                code="INVALID_REGION",
                message=(
                    f"Capture region must have positive size, "
                    f"got {width}x{height}."
                ),
                context=ErrorContext(
                    module="desktop.screen",
                    operation="capture_region",
                    details={
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height,
                    },
                ),
            )

        return self._grab(
            {
                "left": left,
                "top": top,
                "width": width,
                "height": height,
            }
        )

    # ==========================================================
    # Save
    # ==========================================================

    def save(
        self,
        image: np.ndarray,
        path: str | Path,
    ) -> None:
        """
        Write a captured BGR frame to disk.

        cv2.imwrite expects BGR, which is exactly what capture() returns, so no
        conversion happens here. Writing the array with an RGB-oriented encoder
        instead would swap the red and blue channels of every saved screenshot.
        """

        target = Path(path)

        if target.parent and not target.parent.exists():
            raise VisionError(
                code="SAVE_FAILED",
                message=f"Directory does not exist: {target.parent}",
                context=ErrorContext(
                    module="desktop.screen",
                    operation="save",
                ),
            )

        # imwrite reports failure by returning False rather than raising.
        if not cv2.imwrite(str(target), image):
            raise VisionError(
                code="SAVE_FAILED",
                message=f"Could not write screenshot to {target}.",
                hint="Check the file extension is a format OpenCV can encode.",
                context=ErrorContext(
                    module="desktop.screen",
                    operation="save",
                ),
            )

    # ==========================================================
    # Information
    # ==========================================================

    def size(self) -> tuple[int, int]:
        """
        Returns primary monitor size as (width, height).
        """

        monitor = self._sct.monitors[1]

        return (
            int(monitor["width"]),
            int(monitor["height"]),
        )

    def monitors(self) -> list[dict]:
        """
        Returns monitor metadata.

        Index 0 of ``mss.monitors`` is the virtual bounding box of every
        screen, not a physical monitor, so it is dropped.
        """

        return [dict(monitor) for monitor in self._sct.monitors[1:]]

    # ==========================================================
    # Capture by Monitor
    # ==========================================================

    def capture_monitor(
        self,
        monitor_index: int,
    ) -> np.ndarray:
        """
        Capture a specific monitor (1 = primary).
        """

        monitors = self._sct.monitors

        if not 0 <= monitor_index < len(monitors):
            raise VisionError(
                code="INVALID_MONITOR",
                message=(
                    f"Monitor {monitor_index} does not exist "
                    f"({len(monitors) - 1} connected)."
                ),
                context=ErrorContext(
                    module="desktop.screen",
                    operation="capture_monitor",
                ),
            )

        return self._grab(monitors[monitor_index])

    # ==========================================================
    # Internal
    # ==========================================================

    def _grab(
        self,
        monitor: dict,
    ) -> np.ndarray:
        """
        Grab a region and drop the alpha channel.

        mss hands back BGRA; slicing to three channels leaves BGR, which is the
        colour space the whole vision pipeline is defined in.
        """

        try:
            screenshot = self._sct.grab(monitor)

        except Exception as exc:
            raise VisionError(
                code="CAPTURE_FAILED",
                message="Screen capture failed.",
                context=ErrorContext(
                    module="desktop.screen",
                    operation="grab",
                    details={"monitor": monitor},
                ),
                cause=exc,
            ) from exc

        frame = np.asarray(screenshot, dtype=np.uint8)[:, :, :3]

        # asarray over a raw ScreenShot is a view onto mss's reusable buffer;
        # the next grab() would mutate a frame the caller still holds.
        return np.ascontiguousarray(frame)

    # ==========================================================
    # Cleanup
    # ==========================================================

    def close(self) -> None:
        """
        Release MSS resources.
        """

        self._sct.close()
