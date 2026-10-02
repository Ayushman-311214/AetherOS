from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any

from ...core.errors.base_error import ErrorContext
from ...core.errors.vision_error import VisionError
from ...core.logging import get_logger
from ..image import Image
from ..models.detection import Detection
from .base import DetectionProvider


class YOLOProvider(DetectionProvider):
    """
    Ultralytics YOLO implementation.

    Supports object detection using YOLOv8/YOLOv11 models.

    Availability
    ------------
    ``ultralytics`` is an optional dependency and its weights are a separate
    download, so neither is required at import time:

    - construction never imports ultralytics and never loads weights
    - :attr:`available` reports whether the package *and* the weights are present
    - the model is loaded on the first :meth:`detect` call

    Weights must already exist on disk unless ``allow_download=True``. Left to
    itself ultralytics fetches missing weights over the network, which would put
    an internet dependency into startup and into the test suite.
    """

    def __init__(
        self,
        model: str | Path = "yolo11n.pt",
        allow_download: bool = False,
        *,
        device: str = "",
        imgsz: int = 640,
        confidence: float = 0.25,
    ) -> None:

        self._weights = Path(model)
        self._allow_download = allow_download
        self._logger = get_logger("vision.detection")

        # Perf/hardware knobs, all from config (§5/§13):
        #   device     -- "" means auto (CUDA when available, else CPU)
        #   imgsz      -- YOLO inference size (longest side)
        #   confidence -- default detection threshold
        self._device_pref = device
        self._imgsz = imgsz
        self._confidence = confidence

        # Resolved to a real torch device string on first build, then reused.
        self._device: str | None = None

        self._model: Any | None = None

    # ==========================================================
    # Provider Info
    # ==========================================================

    @property
    def name(self) -> str:
        return "Ultralytics YOLO"

    @property
    def version(self) -> str:

        if not self._package_installed:
            return "unavailable"

        try:
            import ultralytics

            return str(
                getattr(ultralytics, "__version__", "unknown")
            )

        except Exception:
            return "unknown"

    @property
    def available(self) -> bool:
        """
        Whether detection can run without a download.
        """

        if not self._package_installed:
            return False

        return self._allow_download or self._weights.is_file()

    @property
    def weights(self) -> Path:
        return self._weights

    @property
    def _package_installed(self) -> bool:
        # find_spec rather than import: importing ultralytics pulls in torch.
        return importlib.util.find_spec("ultralytics") is not None

    # ==========================================================
    # Detection
    # ==========================================================

    async def detect(
        self,
        image: Image,
        confidence: float | None = None,
    ) -> list[Detection]:

        if image is None:
            raise VisionError(
                code="INVALID_IMAGE",
                message="No image supplied to object detection.",
                context=self._context("detect"),
            )

        # None means "use the configured default" -- the threshold is a config
        # value, not something every caller should have to pass.
        conf = self._confidence if confidence is None else confidence

        return await asyncio.to_thread(
            self._detect_sync,
            image,
            conf,
        )

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def close(self) -> None:

        self._model = None

    # ==========================================================
    # Internal — model
    # ==========================================================

    def _build(self) -> Any:

        if not self._package_installed:
            raise VisionError(
                code="DETECTION_UNAVAILABLE",
                message="Ultralytics is not installed.",
                hint=(
                    "Install ultralytics to enable object detection. Other "
                    "vision features work without it."
                ),
                context=self._context("initialize"),
            )

        if not self._allow_download and not self._weights.is_file():
            raise VisionError(
                code="DETECTION_MODEL_MISSING",
                message=f"YOLO weights not found: {self._weights}",
                hint=(
                    "Point the provider at a local .pt file, or construct it "
                    "with allow_download=True to fetch the weights."
                ),
                context=self._context("initialize"),
            )

        try:
            from ultralytics import YOLO

            model = YOLO(str(self._weights))

        except Exception as exc:
            raise VisionError(
                code="DETECTION_INIT_FAILED",
                message="YOLO model could not be loaded.",
                context=self._context("initialize"),
                cause=exc,
            ) from exc

        # Resolve and pin the device once, at init, and move the weights onto
        # it. Doing this here (not per predict) means the model lives on the GPU
        # for its whole lifetime instead of being copied across the PCIe bus on
        # every call.
        self._device = self._resolve_device()

        try:
            model.to(self._device)

        except Exception as exc:
            # A device move can fail (e.g. a stale "cuda:1" pin); fall back to
            # CPU rather than losing detection entirely.
            self._logger.bind(
                device=self._device,
                error=str(exc),
            ).warning("Could not move YOLO model to device; falling back to CPU.")
            self._device = "cpu"
            model.to("cpu")

        # Logged once, at init -- §5 wants the device, model and input size
        # visible exactly once so an operator can confirm the GPU is actually in
        # use without every detection spamming the log.
        self._logger.bind(
            weights=str(self._weights),
            version=self.version,
            imgsz=self._imgsz,
        ).info("Vision device: {} | YOLO detector initialized.", self._device.upper())

        return model

    def _resolve_device(self) -> str:
        """
        Decide which torch device detection runs on.

        Empty preference means auto: CUDA when torch reports it, else CPU. An
        explicit "cuda"/"cuda:N" is honoured only when CUDA is actually
        available -- forcing CUDA on a CPU-only build (this environment ships
        ``torch==2.8.0+cpu``) would crash inference, so it degrades to CPU with a
        warning instead.
        """

        try:
            import torch

            cuda_ok = bool(torch.cuda.is_available())

        except Exception:
            cuda_ok = False

        pref = (self._device_pref or "").strip().lower()

        if not pref:
            return "cuda:0" if cuda_ok else "cpu"

        if pref.startswith("cuda"):
            if cuda_ok:
                return self._device_pref.strip()

            self._logger.warning(
                "VISION_DETECTION_DEVICE requested CUDA but no CUDA device is "
                "available; using CPU."
            )
            return "cpu"

        return pref

    def _model_or_build(self) -> Any:

        if self._model is None:
            self._model = self._build()

        return self._model

    # ==========================================================
    # Internal — inference
    # ==========================================================

    def _detect_sync(
        self,
        image: Image,
        confidence: float,
    ) -> list[Detection]:

        model = self._model_or_build()

        # Ultralytics treats a bare numpy array as BGR, the same convention as
        # OpenCV, and rejects a 4-channel frame.
        frame = image.without_alpha().bgr().data

        try:
            results = model.predict(
                source=frame,
                conf=confidence,
                imgsz=self._imgsz,
                device=self._device,
                verbose=False,
            )

        except Exception as exc:
            raise VisionError(
                code="DETECTION_FAILED",
                message="Object detection failed.",
                context=self._context(
                    "detect",
                    details={
                        "width": image.width,
                        "height": image.height,
                    },
                ),
                cause=exc,
            ) from exc

        return self._parse(results)

    def _parse(
        self,
        results: Any,
    ) -> list[Detection]:

        detections: list[Detection] = []

        for result in results or []:

            names = getattr(result, "names", {}) or {}

            for box in getattr(result, "boxes", None) or []:

                cls = int(box.cls.item())

                x1, y1, x2, y2 = (
                    int(value)
                    for value in box.xyxy[0].tolist()
                )

                detections.append(
                    Detection(
                        label=str(names.get(cls, cls)),
                        confidence=float(box.conf.item()),
                        left=x1,
                        top=y1,
                        right=x2,
                        bottom=y2,
                    )
                )

        return detections

    # ==========================================================
    # Internal — errors
    # ==========================================================

    def _context(
        self,
        operation: str,
        details: dict[str, Any] | None = None,
    ) -> ErrorContext:

        return ErrorContext(
            module="vision.detection",
            operation=operation,
            details={
                "provider": "yolo",
                "weights": str(self._weights),
                **(details or {}),
            },
        )
