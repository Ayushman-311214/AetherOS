from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class VisionProvider(ABC):
    """
    Abstract interface for vision providers.

    Every vision implementation must implement this interface.
    """

    # ==========================================================
    # Lifecycle
    # ==========================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Load vision models.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Release resources.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Returns True if the provider is ready.
        """
        ...

    # ==========================================================
    # Image Loading
    # ==========================================================

    @abstractmethod
    def load_image(
        self,
        image: str | Path | Any,
    ) -> Any:
        """
        Load an image.
        """
        ...

    @abstractmethod
    def save_image(
        self,
        image: Any,
        path: str | Path,
    ) -> None:
        """
        Save an image.
        """
        ...

    # ==========================================================
    # OCR
    # ==========================================================

    @abstractmethod
    async def extract_text(
        self,
        image: Any,
    ) -> str:
        """
        Extract text from an image.
        """
        ...

    @abstractmethod
    async def extract_text_with_boxes(
        self,
        image: Any,
    ) -> list[dict[str, Any]]:
        """
        OCR with bounding boxes.
        """
        ...

    # ==========================================================
    # Object Detection
    # ==========================================================

    @abstractmethod
    async def detect_objects(
        self,
        image: Any,
    ) -> list[dict[str, Any]]:
        """
        Detect objects.
        """
        ...

    @abstractmethod
    async def detect_ui_elements(
        self,
        image: Any,
    ) -> list[dict[str, Any]]:
        """
        Detect UI elements.
        """
        ...

    # ==========================================================
    # Template Matching
    # ==========================================================

    @abstractmethod
    async def find_template(
        self,
        image: Any,
        template: Any,
        confidence: float = 0.8,
    ) -> tuple[int, int] | None:
        """
        Locate a template.
        """
        ...

    # ==========================================================
    # Image Processing
    # ==========================================================

    @abstractmethod
    async def resize(
        self,
        image: Any,
        width: int,
        height: int,
    ) -> Any:
        ...

    @abstractmethod
    async def crop(
        self,
        image: Any,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> Any:
        ...

    @abstractmethod
    async def grayscale(
        self,
        image: Any,
    ) -> Any:
        ...

    @abstractmethod
    async def preprocess(
        self,
        image: Any,
    ) -> Any:
        """
        Apply preprocessing before OCR or detection.
        """
        ...

    # ==========================================================
    # Classification
    # ==========================================================

    @abstractmethod
    async def classify(
        self,
        image: Any,
    ) -> dict[str, Any]:
        """
        Classify image.
        """
        ...

    @abstractmethod
    async def caption(
        self,
        image: Any,
    ) -> str:
        """
        Generate an image caption.
        """
        ...

    # ==========================================================
    # Embeddings
    # ==========================================================

    @abstractmethod
    async def embedding(
        self,
        image: Any,
    ) -> list[float]:
        """
        Generate image embedding.
        """
        ...