from __future__ import annotations

import cv2
import numpy as np

from vision.image import Image
from vision.providers.base import VisionProvider


class OpenCVProvider(VisionProvider):
    """
    OpenCV implementation of VisionProvider.

    Responsible for image processing operations.
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

        resized = cv2.resize(
            image.data,
            (width, height),
            interpolation=cv2.INTER_LINEAR,
        )

        return Image(
            data=resized,
            source=image.source,
            metadata=image.metadata.copy(),
        )

    # ==========================================================
    # Grayscale
    # ==========================================================

    async def grayscale(
        self,
        image: Image,
    ) -> Image:

        if image.channels == 1:
            return image

        gray = cv2.cvtColor(
            image.data,
            cv2.COLOR_BGR2GRAY,
        )

        return Image(
            data=gray,
            source=image.source,
            metadata=image.metadata.copy(),
        )

    # ==========================================================
    # Gaussian Blur
    # ==========================================================

    async def blur(
        self,
        image: Image,
        kernel: int = 5,
    ) -> Image:

        blurred = cv2.GaussianBlur(
            image.data,
            (kernel, kernel),
            0,
        )

        return Image(
            data=blurred,
            source=image.source,
            metadata=image.metadata.copy(),
        )

    # ==========================================================
    # Edge Detection
    # ==========================================================

    async def edges(
        self,
        image: Image,
        low: int = 100,
        high: int = 200,
    ) -> Image:

        gray = image

        if image.channels != 1:
            gray = await self.grayscale(image)

        edge = cv2.Canny(
            gray.data,
            low,
            high,
        )

        return Image(
            data=edge,
            source=image.source,
            metadata=image.metadata.copy(),
        )

    # ==========================================================
    # Threshold
    # ==========================================================

    async def threshold(
        self,
        image: Image,
        value: int = 127,
    ) -> Image:

        gray = image

        if image.channels != 1:
            gray = await self.grayscale(image)

        _, binary = cv2.threshold(
            gray.data,
            value,
            255,
            cv2.THRESH_BINARY,
        )

        return Image(
            data=binary,
            source=image.source,
            metadata=image.metadata.copy(),
        )

    # ==========================================================
    # Morphology
    # ==========================================================

    async def dilate(
        self,
        image: Image,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> Image:

        kernel = np.ones(
            (kernel_size, kernel_size),
            np.uint8,
        )

        result = cv2.dilate(
            image.data,
            kernel,
            iterations=iterations,
        )

        return Image(
            data=result,
            source=image.source,
            metadata=image.metadata.copy(),
        )

    async def erode(
        self,
        image: Image,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> Image:

        kernel = np.ones(
            (kernel_size, kernel_size),
            np.uint8,
        )

        result = cv2.erode(
            image.data,
            kernel,
            iterations=iterations,
        )

        return Image(
            data=result,
            source=image.source,
            metadata=image.metadata.copy(),
        )