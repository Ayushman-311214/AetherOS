from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Detection:
    """
    Represents a detected object.
    """

    label: str
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
        Check whether a point lies inside the detection.
        """

        return (
            self.left <= x <= self.right
            and
            self.top <= y <= self.bottom
        )

    def intersects(
        self,
        other: "Detection",
    ) -> bool:
        """
        Check if two detections overlap.
        """

        return not (
            self.right < other.left
            or
            self.left > other.right
            or
            self.bottom < other.top
            or
            self.top > other.bottom
        )

    def iou(
        self,
        other: "Detection",
    ) -> float:
        """
        Calculate Intersection over Union (IoU).
        """

        x1 = max(self.left, other.left)
        y1 = max(self.top, other.top)
        x2 = min(self.right, other.right)
        y2 = min(self.bottom, other.bottom)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)

        union = (
            self.area
            + other.area
            - intersection
        )

        return intersection / union

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to a serializable dictionary.
        """

        return {
            "label": self.label,
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
            f"Detection("
            f"label={self.label!r}, "
            f"confidence={self.confidence:.2f}, "
            f"bbox={self.bbox})"
        )