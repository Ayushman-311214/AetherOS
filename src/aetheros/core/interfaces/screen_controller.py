# from __future__ import annotations

# from abc import ABC, abstractmethod
# from pathlib import Path
# from typing import Any


# class ScreenController(ABC):
#     """
#     Abstract interface for screen operations.

#     Every screen implementation (MSS, PIL, DXGI, etc.)
#     must implement this interface.
#     """

#     # ==========================================================
#     # Screen Information
#     # ==========================================================

#     @abstractmethod
#     def size(self) -> tuple[int, int]:
#         """
#         Returns the primary screen resolution.

#         Example:
#             (1920, 1080)
#         """
#         ...

#     @abstractmethod
#     def monitors(self) -> list[dict[str, Any]]:
#         """
#         Returns information about all connected monitors.
#         """
#         ...

#     # ==========================================================
#     # Screenshot
#     # ==========================================================

#     @abstractmethod
#     def screenshot(
#         self,
#         save_path: str | Path | None = None,
#     ) -> Any:
#         """
#         Capture the entire screen.

#         Returns:
#             Image object
#         """
#         ...

#     @abstractmethod
#     def screenshot_region(
#         self,
#         x: int,
#         y: int,
#         width: int,
#         height: int,
#         save_path: str | Path | None = None,
#     ) -> Any:
#         """
#         Capture a region of the screen.
#         """
#         ...

#     @abstractmethod
#     def screenshot_monitor(
#         self,
#         monitor: int,
#         save_path: str | Path | None = None,
#     ) -> Any:
#         """
#         Capture an entire monitor.
#         """
#         ...

#     # ==========================================================
#     # Pixel Operations
#     # ==========================================================

#     @abstractmethod
#     def pixel(
#         self,
#         x: int,
#         y: int,
#     ) -> tuple[int, int, int]:
#         """
#         Returns RGB color of a pixel.
#         """
#         ...

#     @abstractmethod
#     def pixel_matches(
#         self,
#         x: int,
#         y: int,
#         rgb: tuple[int, int, int],
#         tolerance: int = 0,
#     ) -> bool:
#         """
#         Check whether a pixel matches a given color.
#         """
#         ...

#     # ==========================================================
#     # Utilities
#     # ==========================================================

#     @abstractmethod
#     def save(
#         self,
#         image: Any,
#         path: str | Path,
#     ) -> None:
#         """
#         Save an image to disk.
#         """
#         ...


from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class ScreenshotController(ABC):
    """
    Abstract interface for screen capture operations.
    """

    @abstractmethod
    def capture(self) -> Path:
        """
        Capture the full screen and return the image path.
        """
        ...

    @abstractmethod
    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Path:
        """
        Capture a screen region and return the image path.
        """
        ...

    @abstractmethod
    def screen_size(self) -> tuple[int, int]:
        """
        Return screen width and height.
        """
        ...