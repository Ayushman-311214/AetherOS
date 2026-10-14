from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import numpy as np


class ScreenController(ABC):
    """
    Abstract interface for raw screen-capture backends (MSS, DXGI, ...).

    Capture returns pixels rather than a file path: the vision engine consumes
    frames in memory, and forcing every capture through a temporary PNG would
    add disk I/O to the OCR path for no benefit. When a saved file *is* the
    product, capture a frame and hand it to :meth:`save` — that keeps one
    capture backend rather than two whose colour handling can drift apart.

    Colour space
    ------------
    ``capture`` and ``capture_region`` return **BGR** ``uint8`` arrays of shape
    ``(height, width, 3)``. BGR is what OpenCV, PaddleOCR and PaddleX all treat
    as the default for a raw numpy array, so returning anything else here would
    silently swap the red and blue channels of every downstream consumer.
    """

    # ==========================================================
    # Screen Capture
    # ==========================================================

    @abstractmethod
    def capture(self) -> np.ndarray:
        """
        Capture the primary monitor as a BGR array.
        """
        ...

    @abstractmethod
    def capture_region(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> np.ndarray:
        """
        Capture a rectangular region as a BGR array.
        """
        ...

    # ==========================================================
    # Utilities
    # ==========================================================

    @abstractmethod
    def save(
        self,
        image: np.ndarray,
        path: str | Path,
    ) -> None:
        """
        Write a BGR array to disk, preserving its colours.
        """
        ...

    # ==========================================================
    # Screen Information
    # ==========================================================

    @abstractmethod
    def size(self) -> tuple[int, int]:
        """
        Return the primary monitor resolution as ``(width, height)``.
        """
        ...

    @abstractmethod
    def monitors(self) -> list[dict[str, Any]]:
        """
        Return metadata for every connected monitor.
        """
        ...

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def close(self) -> None:
        """
        Release backend resources.

        Concrete, not abstract: a backend holding no OS handle has nothing to
        release, and shutdown code should be able to call this unconditionally.
        """

        return None
