from __future__ import annotations

from typing import Any

from ..core.logging import get_logger

from .image import Image
from .providers.base import (
    OCRProvider,
    VisionProvider,
    DetectionProvider,
    TemplateProvider,
)


class VisionService:
    """
    High-level vision service.

    Coordinates OCR, computer vision,
    object detection and template matching.
    """

    def __init__(
        self,
        *,
        ocr: OCRProvider,
        cv: VisionProvider,
        detector: DetectionProvider | None = None,
        template: TemplateProvider | None = None,
    ) -> None:

        self._ocr = ocr
        self._cv = cv
        self._detector = detector
        self._template = template

        self._logger = get_logger("vision")

    # ==========================================================
    # OCR
    # ==========================================================

    async def read_text(
        self,
        image: Image,
    ) -> list[str]:

        self._logger.debug("Reading text.")

        return await self._ocr.read_text(image)

    # ==========================================================
    # Object Detection
    # ==========================================================

    async def detect_objects(
        self,
        image: Image,
    ) -> list[Any]:

        if self._detector is None:
            raise RuntimeError(
                "No detection provider configured."
            )

        return await self._detector.detect(image)

    # ==========================================================
    # Template Matching
    # ==========================================================

    async def find_template(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
    ) -> list[Any]:

        if self._template is None:
            raise RuntimeError(
                "No template provider configured."
            )

        return await self._template.find(
            image=image,
            template=template,
            threshold=threshold,
        )

    # ==========================================================
    # OpenCV Helpers
    # ==========================================================

    async def resize(
        self,
        image: Image,
        width: int,
        height: int,
    ) -> Image:

        return await self._cv.resize(
            image,
            width,
            height,
        )

    async def grayscale(
        self,
        image: Image,
    ) -> Image:

        return await self._cv.grayscale(
            image,
        )

    async def blur(
        self,
        image: Image,
        kernel: int = 5,
    ) -> Image:

        return await self._cv.blur(
            image,
            kernel,
        )

    async def edges(
        self,
        image: Image,
        low: int = 100,
        high: int = 200,
    ) -> Image:

        return await self._cv.edges(
            image,
            low,
            high,
        )
