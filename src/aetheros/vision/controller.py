from __future__ import annotations

from ..core.errors.base_error import ErrorContext
from ..core.errors.vision_error import VisionError
from ..core.logging import get_logger

from .image import Image
from .models import Detection, TemplateMatch, TextBlock
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

    Optional capabilities
    ---------------------
    Object detection and template matching depend on providers that may not be
    installed. Rather than failing at construction, the service reports what it
    can do through :attr:`has_detector` / :attr:`has_template` / :attr:`has_ocr`,
    so a caller can degrade instead of crashing.
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
    # Capabilities
    # ==========================================================

    @property
    def has_ocr(self) -> bool:
        """
        Whether text recognition can actually run.
        """

        return self._ocr.available

    @property
    def has_detector(self) -> bool:

        return (
            self._detector is not None
            and self._detector.available
        )

    @property
    def has_template(self) -> bool:

        return (
            self._template is not None
            and self._template.available
        )

    def capabilities(self) -> dict[str, bool]:
        """
        A serialisable summary of what this service can do.
        """

        return {
            "ocr": self.has_ocr,
            "detection": self.has_detector,
            "template": self.has_template,
            "image_processing": True,
        }

    # ==========================================================
    # OCR
    # ==========================================================

    async def read_text(
        self,
        image: Image,
    ) -> list[TextBlock]:
        """
        Recognise text in an image.

        An empty list means "no readable text", which is a valid outcome. A
        genuinely broken OCR backend raises :class:`VisionError`.
        """

        self._require_image(image, operation="read_text")

        blocks = await self._ocr.read_text(image)

        self._logger.bind(
            blocks=len(blocks),
            source=image.source,
        ).debug("Text recognition complete.")

        return blocks

    # ==========================================================
    # Object Detection
    # ==========================================================

    async def detect_objects(
        self,
        image: Image,
    ) -> list[Detection]:

        self._require_image(image, operation="detect_objects")

        if self._detector is None:
            raise VisionError(
                code="DETECTION_UNAVAILABLE",
                message="No detection provider is configured.",
                hint=(
                    "Object detection needs a DetectionProvider; check "
                    "has_detector before calling."
                ),
                context=ErrorContext(
                    module="vision",
                    operation="detect_objects",
                ),
            )

        detections = await self._detector.detect(image)

        self._logger.bind(
            detections=len(detections),
        ).debug("Object detection complete.")

        return detections

    # ==========================================================
    # Template Matching
    # ==========================================================

    async def find_template(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
    ) -> list[TemplateMatch]:

        self._require_image(image, operation="find_template")
        self._require_image(template, operation="find_template")

        if self._template is None:
            raise VisionError(
                code="TEMPLATE_UNAVAILABLE",
                message="No template provider is configured.",
                hint=(
                    "Template matching needs a TemplateProvider; check "
                    "has_template before calling."
                ),
                context=ErrorContext(
                    module="vision",
                    operation="find_template",
                ),
            )

        return await self._template.find(
            image=image,
            template=template,
            threshold=threshold,
        )

    # ==========================================================
    # Text Search
    # ==========================================================

    async def find_text(
        self,
        image: Image,
        query: str,
        case_sensitive: bool = False,
    ) -> list[TextBlock]:
        """
        Recognise text and return only the blocks matching ``query``.
        """

        if not query:
            raise VisionError(
                code="INVALID_ARGUMENT",
                message="Search query must not be empty.",
                context=ErrorContext(
                    module="vision",
                    operation="find_text",
                ),
            )

        blocks = await self.read_text(image)

        return [
            block
            for block in blocks
            if block.matches(query, case_sensitive=case_sensitive)
        ]

    # ==========================================================
    # OpenCV Helpers
    # ==========================================================

    async def resize(
        self,
        image: Image,
        width: int,
        height: int,
    ) -> Image:

        self._require_image(image, operation="resize")

        return await self._cv.resize(
            image,
            width,
            height,
        )

    async def grayscale(
        self,
        image: Image,
    ) -> Image:

        self._require_image(image, operation="grayscale")

        return await self._cv.grayscale(
            image,
        )

    async def blur(
        self,
        image: Image,
        kernel: int = 5,
    ) -> Image:

        self._require_image(image, operation="blur")

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

        self._require_image(image, operation="edges")

        return await self._cv.edges(
            image,
            low,
            high,
        )

    # ==========================================================
    # Lifecycle
    # ==========================================================

    async def shutdown(self) -> None:
        """
        Release provider resources.

        Each provider is closed independently: one backend failing to release a
        model must not leave the others loaded.
        """

        for provider in (self._ocr, self._cv, self._detector, self._template):

            if provider is None:
                continue

            closer = getattr(provider, "close", None)

            if not callable(closer):
                continue

            try:
                closer()

            except Exception as exc:
                self._logger.bind(
                    provider=provider.name,
                    error=str(exc),
                ).warning("Vision provider did not close cleanly.")

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _require_image(
        image: Image | None,
        operation: str,
    ) -> None:
        """
        Reject a missing image here rather than inside a provider.

        A None slipping through surfaces deep in OpenCV as an unhelpful
        ``AttributeError: 'NoneType' object has no attribute 'data'``.
        """

        if isinstance(image, Image):
            return

        raise VisionError(
            code="INVALID_IMAGE",
            message=(
                f"Expected a vision Image, got {type(image).__name__}."
            ),
            hint="Wrap raw arrays with Image.from_numpy() first.",
            context=ErrorContext(
                module="vision",
                operation=operation,
            ),
        )
