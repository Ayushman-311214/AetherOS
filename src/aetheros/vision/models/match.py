from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TemplateMatch:
    """
    Represents a template match result.
    """

    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.x + self.width // 2,
            self.y + self.height // 2,
        )

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "center": self.center,
            "bbox": self.bbox,
        }
