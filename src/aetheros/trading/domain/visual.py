"""
Visual-observation value objects (spec Phase 17).

A visual observation is what the vision subsystem read off a chart screenshot:
a text block (symbol, timeframe, price, indicator label), a detected object
(support/resistance drawing, trendline, volume panel, UI control), or the
honest record that nothing readable was found. It is the visual counterpart to
a candle-derived fact, and it is deliberately weaker: every observation carries
its confidence, its bounding box where one exists, its source and its
timestamp, so downstream fusion can weigh it below API-derived numbers and
never mistake a visual guess for a measured value.

These objects are the trading side of the bridge. They hold no pixels and run
no models -- they are built by :class:`VisualObservationService` from the
vision subsystem's own reads (``TextBlock`` / ``Detection``), which already
carry confidence and bounding boxes. Nothing here duplicates OCR, detection,
or capture: those live in ``vision/`` and ``desktop/`` and are consumed
through their interfaces.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class VisualObservation:
    """
    One thing vision read off a chart screenshot.

    ``kind`` names what was read (``"text"``, ``"object"``, ``"empty"`` --
    the last being the honest "nothing readable" record, not a failure).
    ``label`` is the read itself (the OCR string, the detection label).
    ``confidence`` is the vision backend's own 0..1 score, preserved verbatim
    and never upgraded. ``bbox`` is (left, top, right, bottom) pixels where
    the backend supplied one, else ``None``. ``source`` names the vision
    capability that produced it (``"ocr"``, ``"detection"``).
    """

    kind: str
    label: str
    confidence: float
    source: str
    bbox: tuple[int, int, int, int] | None = None
    observed_at: datetime = field(default_factory=_utcnow)
    id: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("text", "object", "empty"):
            raise ValueError(f"Unknown visual-observation kind '{self.kind}'.")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Visual-observation confidence must lie in [0, 1].")
        if not self.source.strip():
            raise ValueError("A visual observation must name its source.")
        if not self.id:
            payload = "|".join(
                (
                    self.kind,
                    self.label.strip().lower(),
                    self.source,
                    f"{self.confidence:.4f}",
                )
            )
            digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
            object.__setattr__(self, "id", f"vo_{digest[:16]}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "confidence": self.confidence,
            "source": self.source,
            "bbox": list(self.bbox) if self.bbox is not None else None,
            "observed_at": self.observed_at.isoformat(),
        }
