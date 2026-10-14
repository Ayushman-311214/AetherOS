from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TextBlock:
    """
    Represents detected text from OCR.
    """

    text: str
    confidence: float

    left: int
    top: int
    right: int
    bottom: int

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.left + self.width // 2,
            self.top + self.height // 2,
        )

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (
            self.left,
            self.top,
            self.right,
            self.bottom,
        )

    # ==========================================================
    # Utilities
    # ==========================================================

    def contains(
        self,
        x: int,
        y: int,
    ) -> bool:
        """
        Check whether a point lies inside the text block.
        """

        return (
            self.left <= x <= self.right
            and
            self.top <= y <= self.bottom
        )

    def matches(
        self,
        query: str,
        case_sensitive: bool = False,
    ) -> bool:
        """
        Check if text contains query.
        """

        if case_sensitive:
            return query in self.text

        return query.lower() in self.text.lower()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to serializable dictionary.
        """

        return {
            "text": self.text,
            "confidence": self.confidence,
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "width": self.width,
            "height": self.height,
            "center": self.center,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"TextBlock("
            f"text={self.text!r}, "
            f"confidence={self.confidence:.2f}, "
            f"bbox={self.bbox})"
        )
