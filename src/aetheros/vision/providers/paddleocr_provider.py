from __future__ import annotations

import asyncio
import importlib.util
import os
from typing import Any

import numpy as np

from ...core.errors.base_error import ErrorContext
from ...core.errors.vision_error import VisionError
from ...core.logging import get_logger
from ..image import Image
from ..models import TextBlock
from .base import OCRProvider

# oneDNN (mkldnn) is PaddleOCR's default CPU backend, and on paddlepaddle 3.x it
# fails outright under the PIR executor: the detection model carries a
# double-array attribute that the oneDNN instruction cannot lower, so the very
# first predict() raises
#
#     NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute
#     not support [pir::ArrayAttribute<pir::DoubleAttribute>]
#
# which surfaced here as VISION_OCR_FAILED on every single image.
#
# Setting FLAGS_use_mkldnn=0 in the environment does NOT help: PaddleX passes
# run_mode="mkldnn" to the predictor explicitly, and an explicit run_mode beats
# the global flag. The constructor argument is the only switch that takes
# effect, and it makes PaddleX select run_mode="paddle" — the plain CPU
# executor, which also keeps results reproducible across machines.
_ENABLE_MKLDNN = False

# PaddleX otherwise probes its model hosts over the network on construction,
# even when every model is already cached, costing a few seconds per process and
# making a machine with no route to those hosts wait on a doomed request. The
# download itself still happens when a model really is missing; this only skips
# the reachability probe.
_MODEL_SOURCE_CHECK_ENV = "PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"

# paddleocr is the API package; paddle is the native runtime that actually
# executes the models. Installing the first without the second is a common state
# (paddlepaddle has no wheel for every Python version), and it is indistinguish-
# able from a working install until inference is attempted — which is why both
# are checked.
_REQUIRED_PACKAGES = ("paddleocr", "paddle")


def _quiet_model_source_check() -> None:
    """
    Ask PaddleX not to probe its model hosts.

    Must run before paddleocr is imported: the setting is read as the package
    loads. setdefault, not assignment — an operator who set this deliberately
    keeps their value.
    """

    os.environ.setdefault(_MODEL_SOURCE_CHECK_ENV, "True")


class PaddleOCRProvider(OCRProvider):
    """
    PaddleOCR implementation of the OCR provider interface.

    Availability
    ------------
    PaddleOCR and its paddlepaddle runtime are heavyweight optional
    dependencies, and the recognition models are downloaded on first use. So:

    - construction never imports paddle and never touches the network
    - :attr:`available` reports whether both packages are installed
    - the model is built on the first :meth:`read_text` call and reused

    A vision engine on a machine without PaddleOCR therefore still starts, still
    registers its tools, and raises a specific ``VISION_OCR_UNAVAILABLE`` when
    text recognition is actually requested.
    """

    def __init__(
        self,
        language: str = "en",
        use_angle_cls: bool = False,
    ) -> None:

        self._language = language
        self._use_angle_cls = use_angle_cls
        self._logger = get_logger("vision.ocr")

        # Built lazily; None means "not built yet", not "unavailable".
        self._ocr: Any | None = None
        self._version: str | None = None

    # ==========================================================
    # Metadata
    # ==========================================================

    @property
    def name(self) -> str:
        return "PaddleOCR"

    @property
    def version(self) -> str:
        """
        The installed PaddleOCR version, or ``"unavailable"``.

        Read from the package rather than hardcoded — a hardcoded version turns
        every "which OCR build produced this text?" audit question into a guess.
        """

        if self._version is not None:
            return self._version

        if not self.available:
            self._version = "unavailable"
            return self._version

        try:
            _quiet_model_source_check()

            import paddleocr

            self._version = str(
                getattr(paddleocr, "__version__", "unknown")
            )

        except Exception:
            # Metadata must never be the thing that breaks a caller.
            self._version = "unknown"

        return self._version

    @property
    def available(self) -> bool:
        """
        Whether PaddleOCR *and* its paddle runtime are importable.

        Uses find_spec so the answer costs nothing: importing paddleocr pulls in
        the whole paddle runtime, which takes seconds.

        Both packages are required. Checking only ``paddleocr`` would report this
        provider as available on a machine with no runtime, and the eventual
        failure would then be reported as a model-initialization problem —
        pointing an operator at the network when the real fix is installing
        paddlepaddle.
        """

        return all(
            importlib.util.find_spec(package) is not None
            for package in _REQUIRED_PACKAGES
        )

    # ==========================================================
    # OCR
    # ==========================================================

    async def read_text(
        self,
        image: Image,
    ) -> list[TextBlock]:
        """
        Recognise text in an image.

        Returns an empty list for an image with no readable text.
        """

        if image is None:
            raise VisionError(
                code="INVALID_IMAGE",
                message="No image supplied to OCR.",
                context=self._context("read_text"),
            )

        # Model construction and inference both block for seconds; running them
        # on the event loop would stall every other agent in the process.
        return await asyncio.to_thread(self._read_sync, image)

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def close(self) -> None:
        """
        Release the OCR model.
        """

        if self._ocr is None:
            return

        closer = getattr(self._ocr, "close", None)

        if callable(closer):
            try:
                closer()

            except Exception as exc:
                # Shutdown must not raise: a failure to release the model would
                # otherwise mask whatever the process was actually shutting down for.
                self._logger.bind(error=str(exc)).warning(
                    "PaddleOCR did not close cleanly."
                )

        self._ocr = None

    # ==========================================================
    # Internal — model
    # ==========================================================

    def _build(self) -> Any:
        """
        Construct the PaddleOCR pipeline.
        """

        if not self.available:
            missing = [
                package
                for package in _REQUIRED_PACKAGES
                if importlib.util.find_spec(package) is None
            ]

            raise VisionError(
                code="OCR_UNAVAILABLE",
                message=(
                    "PaddleOCR is not usable: "
                    f"{', '.join(missing)} not installed."
                ),
                hint=(
                    "Install paddleocr and paddlepaddle to enable text "
                    "recognition. Other vision features work without them."
                ),
                context=self._context("initialize"),
            )

        _quiet_model_source_check()

        try:
            from paddleocr import PaddleOCR

        except Exception as exc:
            # paddleocr is present but its runtime is not — the usual cause is a
            # missing or mismatched paddlepaddle wheel.
            raise VisionError(
                code="OCR_UNAVAILABLE",
                message="PaddleOCR is installed but could not be imported.",
                hint=(
                    "Its paddlepaddle runtime is probably missing or built for "
                    "a different Python version."
                ),
                context=self._context("initialize"),
                cause=exc,
            ) from exc

        try:
            # Document orientation, unwarping and textline orientation each pull
            # a separate model. They are off by default because a screenshot is
            # already upright, and every extra model is another download that
            # has to succeed before any text can be read.
            ocr = PaddleOCR(
                lang=self._language,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=self._use_angle_cls,
                enable_mkldnn=_ENABLE_MKLDNN,
            )

        except Exception as exc:
            raise VisionError(
                code="OCR_INIT_FAILED",
                message="PaddleOCR model initialization failed.",
                hint=(
                    "The recognition models are downloaded on first use; this "
                    "fails without network access or a populated model cache."
                ),
                context=self._context("initialize"),
                cause=exc,
            ) from exc

        self._logger.bind(
            language=self._language,
            version=self.version,
        ).info("PaddleOCR initialized.")

        return ocr

    def _model(self) -> Any:
        """
        Return the pipeline, building it on first use.
        """

        if self._ocr is None:
            self._ocr = self._build()

        return self._ocr

    # ==========================================================
    # Internal — inference
    # ==========================================================

    def _read_sync(
        self,
        image: Image,
    ) -> list[TextBlock]:

        frame = self._prepare(image)

        ocr = self._model()

        try:
            # 3.x exposes predict(); 2.x only had ocr().
            predict = getattr(ocr, "predict", None)

            results = (
                predict(frame)
                if callable(predict)
                else ocr.ocr(frame)
            )

        except Exception as exc:
            raise VisionError(
                code="OCR_FAILED",
                message="Text recognition failed.",
                context=self._context(
                    "read_text",
                    details={
                        "width": image.width,
                        "height": image.height,
                    },
                ),
                cause=exc,
            ) from exc

        if not results:
            return []

        blocks: list[TextBlock] = []

        for result in results:
            if result is None:
                continue

            blocks.extend(self._parse(result))

        return blocks

    def _prepare(
        self,
        image: Image,
    ) -> np.ndarray:
        """
        Coerce an Image into what PaddleOCR accepts: 3-channel BGR uint8.

        PaddleX's image reader defaults to ``format="BGR"`` and returns a numpy
        array untouched, so it treats whatever it is handed as already being
        BGR. Converting to RGB first — as this provider used to — silently swaps
        the red and blue channels of every frame before recognition.
        """

        # Alpha and single-channel data both break the recognition model's
        # expected input shape.
        prepared = image.without_alpha()

        if prepared.color_space == "gray":
            prepared = Image.from_numpy(
                np.repeat(
                    prepared.data.reshape(
                        prepared.height,
                        prepared.width,
                        1,
                    ),
                    3,
                    axis=2,
                ),
                source=prepared.source,
                color_space="bgr",
            )
        else:
            prepared = prepared.bgr()

        frame = prepared.data

        if frame.dtype != np.uint8:
            raise VisionError(
                code="INVALID_IMAGE",
                message=(
                    f"OCR needs 8-bit image data, got {frame.dtype}."
                ),
                context=self._context("read_text"),
            )

        return np.ascontiguousarray(frame)

    # ==========================================================
    # Internal — result parsing
    # ==========================================================

    def _parse(
        self,
        result: Any,
    ) -> list[TextBlock]:
        """
        Turn one PaddleOCR result into TextBlocks.
        """

        fields = self._fields(result)

        if fields is not None:
            return self._parse_fields(fields)

        # PaddleOCR 2.x returned plain nested lists rather than result objects.
        return self._parse_legacy(result)

    def _fields(
        self,
        result: Any,
    ) -> dict[str, Any] | None:
        """
        Locate the recognition fields on a 3.x result object.

        PaddleX results subclass ``dict``, so the fields are readable directly.
        The ``json`` property is the documented accessor but wraps everything in
        a ``{"res": ...}`` envelope — reading ``rec_texts`` off that envelope
        yields nothing at all, which is how this provider came to report zero
        text for every image while raising no error.
        """

        if isinstance(result, dict) and "rec_texts" in result:
            return result

        payload = getattr(result, "json", None)

        if callable(payload):
            payload = payload()

        if isinstance(payload, dict):
            inner = payload.get("res", payload)

            if isinstance(inner, dict) and "rec_texts" in inner:
                return inner

        return None

    def _parse_fields(
        self,
        fields: dict[str, Any],
    ) -> list[TextBlock]:

        texts = list(fields.get("rec_texts") or [])
        scores = list(fields.get("rec_scores") or [])

        boxes = self._boxes(fields, count=len(texts))

        blocks: list[TextBlock] = []

        for index, text in enumerate(texts):
            if not text:
                continue

            box = boxes[index] if index < len(boxes) else None

            if box is None:
                continue

            confidence = (
                float(scores[index])
                if index < len(scores)
                else 0.0
            )

            left, top, right, bottom = box

            blocks.append(
                TextBlock(
                    text=str(text),
                    confidence=confidence,
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
            )

        return blocks

    def _boxes(
        self,
        fields: dict[str, Any],
        count: int,
    ) -> list[tuple[int, int, int, int] | None]:
        """
        Extract one axis-aligned box per recognised string.

        ``rec_boxes`` is already axis-aligned ``[x1, y1, x2, y2]``, but it comes
        back empty when document preprocessing is disabled, in which case the
        four-point ``rec_polys`` are all that is available.
        """

        raw_boxes = fields.get("rec_boxes")

        boxes: list[tuple[int, int, int, int] | None] = []

        if raw_boxes is not None and len(raw_boxes) > 0:
            for box in raw_boxes:
                boxes.append(self._rect(box))

        if len(boxes) >= count:
            return boxes

        polys = fields.get("rec_polys") or fields.get("dt_polys") or []

        for poly in polys:
            boxes.append(self._polygon_rect(poly))

        return boxes

    def _rect(
        self,
        box: Any,
    ) -> tuple[int, int, int, int] | None:

        try:
            values = [int(round(float(v))) for v in box]

        except (TypeError, ValueError):
            return None

        if len(values) != 4:
            return None

        left, top, right, bottom = values

        return (
            min(left, right),
            min(top, bottom),
            max(left, right),
            max(top, bottom),
        )

    def _polygon_rect(
        self,
        poly: Any,
    ) -> tuple[int, int, int, int] | None:
        """
        Reduce a rotated quadrilateral to its bounding box.
        """

        try:
            points = np.asarray(poly, dtype=float).reshape(-1, 2)

        except (TypeError, ValueError):
            return None

        if points.size == 0:
            return None

        return (
            int(round(points[:, 0].min())),
            int(round(points[:, 1].min())),
            int(round(points[:, 0].max())),
            int(round(points[:, 1].max())),
        )

    def _parse_legacy(
        self,
        result: Any,
    ) -> list[TextBlock]:
        """
        Parse the 2.x shape: ``[[box, (text, score)], ...]``.
        """

        if not isinstance(result, (list, tuple)):
            return []

        blocks: list[TextBlock] = []

        for entry in result:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                continue

            box, recognition = entry

            if not isinstance(recognition, (list, tuple)) or len(recognition) != 2:
                continue

            text, score = recognition

            if not text:
                continue

            rect = self._polygon_rect(box)

            if rect is None:
                continue

            left, top, right, bottom = rect

            blocks.append(
                TextBlock(
                    text=str(text),
                    confidence=float(score),
                    left=left,
                    top=top,
                    right=right,
                    bottom=bottom,
                )
            )

        return blocks

    # ==========================================================
    # Internal — errors
    # ==========================================================

    def _context(
        self,
        operation: str,
        details: dict[str, Any] | None = None,
    ) -> ErrorContext:

        return ErrorContext(
            module="vision.ocr",
            operation=operation,
            details={
                "provider": "paddleocr",
                "language": self._language,
                **(details or {}),
            },
        )
