from __future__ import annotations

import asyncio

import cv2

from paddleocr import PaddleOCR

from vision.image import Image
from vision.models.text import TextBlock
from vision.providers.base import OCRProvider


class PaddleOCRProvider(OCRProvider):
    """
    PaddleOCR implementation.

    Loads the OCR model once and reuses it.
    """

    def __init__(
        self,
        language: str = "en",
        use_angle_cls: bool = True,
    ) -> None:

        self._ocr = PaddleOCR(
            lang=language,
            use_angle_cls=use_angle_cls,
        )

    @property
    def name(self) -> str:
        return "PaddleOCR"

    @property
    def version(self) -> str:
        return "2.x"

    # ==========================================================
    # OCR
    # ==========================================================

    async def read_text(
        self,
        image: Image,
    ) -> list[TextBlock]:

        return await asyncio.to_thread(
            self._read_sync,
            image,
        )

    # ==========================================================
    # Internal
    # ==========================================================

    def _read_sync(
        self,
        image: Image,
    ) -> list[TextBlock]:

        rgb = cv2.cvtColor(
            image.data,
            cv2.COLOR_BGR2RGB,
        )

        result = self._ocr.ocr(
            rgb,
            cls=True,
        )

        blocks: list[TextBlock] = []

        if not result:
            return blocks

        for line in result:

            if line is None:
                continue

            for box, (text, confidence) in line:

                xs = [int(p[0]) for p in box]
                ys = [int(p[1]) for p in box]

                blocks.append(
                    TextBlock(
                        text=text,
                        confidence=float(confidence),

                        left=min(xs),
                        top=min(ys),
                        right=max(xs),
                        bottom=max(ys),
                    )
                )

        return blocks