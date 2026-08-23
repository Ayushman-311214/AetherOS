from __future__ import annotations

import asyncio

import cv2
import os
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

from paddleocr import PaddleOCR

from ..image import Image
from ..models.text import TextBlock
from .base import OCRProvider


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
            enable_mkldnn=False,
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

        results = self._ocr.predict(rgb)

        blocks: list[TextBlock] = []

        if not results:
            return blocks

        for result in results:
            if result is None:
                continue

            # PaddleOCR 3.x returns structured prediction results.
            # Extract the underlying result dictionary.
            data = getattr(result, "json", None)

            if callable(data):
                data = data()

            if not isinstance(data, dict):
                continue

            # PaddleOCR 3.x OCR result fields.
            rec_texts = data.get("rec_texts", [])
            rec_scores = data.get("rec_scores", [])
            rec_boxes = data.get("rec_boxes", [])

            for text, confidence, box in zip(
                rec_texts,
                rec_scores,
                rec_boxes,
            ):
                if not text:
                    continue

                # rec_boxes are normally [x1, y1, x2, y2]
                if len(box) != 4:
                    continue

                x1, y1, x2, y2 = [int(v) for v in box]

                blocks.append(
                    TextBlock(
                        text=str(text),
                        confidence=float(confidence),
                        left=x1,
                        top=y1,
                        right=x2,
                        bottom=y2,
                    )
                )

        return blocks