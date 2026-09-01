from __future__ import annotations

from abc import ABC, abstractmethod

from ..image import Image
from ..models import Detection, TemplateMatch, TextBlock


# ==========================================================
# Base Provider
# ==========================================================

class BaseVisionProvider(ABC):
    """
    Base class for all vision providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def version(self) -> str:
        """Provider version."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """
        Whether this provider can actually run.

        Concrete and ``True`` by default: providers built on always-present
        dependencies are always usable. Providers wrapping an optional package
        or a downloadable model override this so callers can degrade gracefully
        instead of discovering the problem as an ImportError at import time.
        """

        return True


# ==========================================================
# OpenCV Provider
# ==========================================================

class VisionProvider(BaseVisionProvider):
    """
    Image processing provider.
    """

    @abstractmethod
    async def resize(
        self,
        image: Image,
        width: int,
        height: int,
    ) -> Image:
        raise NotImplementedError

    @abstractmethod
    async def grayscale(
        self,
        image: Image,
    ) -> Image:
        raise NotImplementedError

    @abstractmethod
    async def blur(
        self,
        image: Image,
        kernel: int = 5,
    ) -> Image:
        raise NotImplementedError

    @abstractmethod
    async def edges(
        self,
        image: Image,
        low: int = 100,
        high: int = 200,
    ) -> Image:
        raise NotImplementedError


# ==========================================================
# OCR
# ==========================================================

class OCRProvider(BaseVisionProvider):
    """
    OCR provider interface.
    """

    @abstractmethod
    async def read_text(
        self,
        image: Image,
    ) -> list[TextBlock]:
        """
        Recognise text, returning one block per detected region.

        Returns an empty list when the image contains no readable text — that is
        a valid result, not an error. Genuine failures (backend unavailable,
        model missing, malformed input) raise
        :class:`~aetheros.core.errors.vision_error.VisionError`.
        """
        raise NotImplementedError


# ==========================================================
# Object Detection
# ==========================================================

class DetectionProvider(BaseVisionProvider):
    """
    Object detection provider.
    """

    @abstractmethod
    async def detect(
        self,
        image: Image,
    ) -> list[Detection]:
        raise NotImplementedError


# ==========================================================
# Template Matching
# ==========================================================

class TemplateProvider(BaseVisionProvider):
    """
    Template matching provider.
    """

    @abstractmethod
    async def find(
        self,
        image: Image,
        template: Image,
        threshold: float = 0.90,
    ) -> list[TemplateMatch]:
        raise NotImplementedError