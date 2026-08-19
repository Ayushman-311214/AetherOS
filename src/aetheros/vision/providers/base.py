from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..image import Image


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
    ) -> list[str]:
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
    ) -> list[Any]:
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
    ) -> list[Any]:
        raise NotImplementedError