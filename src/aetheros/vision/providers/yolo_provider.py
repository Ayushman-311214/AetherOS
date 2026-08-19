from __future__ import annotations

import asyncio
from pathlib import Path

from ultralytics import YOLO

from ..image import Image
from ..models.detection import Detection
from .base import DetectionProvider


class YOLOProvider(DetectionProvider):
    """
    Ultralytics YOLO implementation.

    Supports object detection using YOLOv8/YOLOv11 models.
    """

    def __init__(
        self,
        model: str | Path = "yolo11n.pt",
    ) -> None:

        self._model = YOLO(str(model))

    # ==========================================================
    # Provider Info
    # ==========================================================

    @property
    def name(self) -> str:
        return "Ultralytics YOLO"

    @property
    def version(self) -> str:
        return "11"

    # ==========================================================
    # Detection
    # ==========================================================

    async def detect(
        self,
        image: Image,
        confidence: float = 0.25,
    ) -> list[Detection]:

        return await asyncio.to_thread(
            self._detect_sync,
            image,
            confidence,
        )

    # ==========================================================
    # Internal
    # ==========================================================

    def _detect_sync(
        self,
        image: Image,
        confidence: float,
    ) -> list[Detection]:

        results = self._model.predict(
            source=image.data,
            conf=confidence,
            verbose=False,
        )

        detections: list[Detection] = []

        for result in results:

            names = result.names

            for box in result.boxes:

                cls = int(box.cls.item())

                label = names[cls]

                conf = float(box.conf.item())

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0].tolist(),
                )

                detections.append(
                    Detection(
                        label=label,
                        confidence=conf,
                        left=x1,
                        top=y1,
                        right=x2,
                        bottom=y2,
                    )
                )

        return detections