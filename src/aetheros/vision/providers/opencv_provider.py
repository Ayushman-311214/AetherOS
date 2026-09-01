from __future__ import annotations

import cv2
import numpy as np

from ...core.errors.base_error import ErrorContext
from ...core.errors.vision_error import VisionError
from ..image import Image
from .base import VisionProvider


class OpenCVProvider(VisionProvider):
    """
    OpenCV implementation of VisionProvider.

    Responsible for image processing operations.

    Operations that reduce an image to one channel return an ``Image`` tagged
    ``color_space="gray"``. Leaving the tag at its BGR default would make a
    later ``rgb()`` call try to reorder channels that no longer exist.
    """

    @property
    def name(self) -> str:
        return "OpenCV"

    @property
    def version(self) -> str:
        return cv2.__version__

    # ==========================================================
    # Resize
    # ==========================================================

    async def resize(
        self,
        image: Image,
        width: int,
        height: int,
    ) -> Image:

        if width <= 0 or height <= 0:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Resize target must be positive, got {width}x{height}."
                ),
                context=self._context("resize"),
            )

        resized = cv2.resize(
            image.data,
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )

        return self._derive(image, resized)

    # ==========================================================
    # Grayscale
    # ==========================================================

    async def grayscale(
        self,
        image: Image,
    ) -> Image:
        """
        Convert to single-channel.

        Delegates to :meth:`Image.gray`, which picks the conversion from the
        image's declared colour space — a fixed ``COLOR_BGR2GRAY`` would weight
        the red and blue channels wrongly for RGB input.
        """

        return image.gray()

    # ==========================================================
    # Gaussian Blur
    # ==========================================================

    async def blur(
        self,
        image: Image,
        kernel: int = 5,
    ) -> Image:

        if kernel <= 0 or kernel % 2 == 0:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Gaussian blur kernel must be a positive odd number, "
                    f"got {kernel}."
                ),
                context=self._context("blur"),
            )

        blurred = cv2.GaussianBlur(
            image.data,
            (kernel, kernel),
            0,
        )

        return self._derive(image, blurred)

    # ==========================================================
    # Edge Detection
    # ==========================================================

    async def edges(
        self,
        image: Image,
        low: int = 100,
        high: int = 200,
    ) -> Image:

        if low < 0 or high < 0 or low >= high:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Canny thresholds must satisfy 0 <= low < high, "
                    f"got low={low}, high={high}."
                ),
                context=self._context("edges"),
            )

        edge = cv2.Canny(
            image.gray().data,
            low,
            high,
        )

        return self._derive(image, edge, color_space="gray")

    # ==========================================================
    # Threshold
    # ==========================================================

    async def threshold(
        self,
        image: Image,
        value: int = 127,
    ) -> Image:

        if not 0 <= value <= 255:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=(
                    f"Threshold must be within 0-255, got {value}."
                ),
                context=self._context("threshold"),
            )

        _, binary = cv2.threshold(
            image.gray().data,
            value,
            255,
            cv2.THRESH_BINARY,
        )

        return self._derive(image, binary, color_space="gray")

    # ==========================================================
    # Morphology
    # ==========================================================

    async def dilate(
        self,
        image: Image,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> Image:

        return self._derive(
            image,
            cv2.dilate(
                image.data,
                self._kernel(kernel_size, "dilate"),
                iterations=iterations,
            ),
        )

    async def erode(
        self,
        image: Image,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> Image:

        return self._derive(
            image,
            cv2.erode(
                image.data,
                self._kernel(kernel_size, "erode"),
                iterations=iterations,
            ),
        )

    # ==========================================================
    # Internal
    # ==========================================================

    def _kernel(
        self,
        size: int,
        operation: str,
    ) -> np.ndarray:

        if size <= 0:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message=f"Kernel size must be positive, got {size}.",
                context=self._context(operation),
            )

        return np.ones((size, size), np.uint8)

    @staticmethod
    def _derive(
        image: Image,
        data: np.ndarray,
        color_space: str | None = None,
    ) -> Image:
        """
        Wrap transformed pixels, carrying provenance and colour space over.
        """

        return Image(
            data=data,
            source=image.source,
            color_space=color_space or image.color_space,
            metadata=image.metadata.copy(),
        )

    @staticmethod
    def _context(operation: str) -> ErrorContext:

        return ErrorContext(
            module="vision.processing",
            operation=operation,
            details={"provider": "opencv"},
        )
