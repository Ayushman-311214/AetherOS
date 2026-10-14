"""
Visual-observation service (spec Phase 17).

Turns what the vision subsystem already read off a chart screenshot into
trading-side :class:`VisualObservation` records -- and, where a read is worth
fusing, into VISUAL :class:`Evidence` with provenance. The service runs no
models and owns no pixels: it takes the vision reads the caller hands it
(``TextBlock`` / ``Detection`` lists from ``VisionService``) plus the capture
provenance, and translates them one-to-one.

Two honesty rules govern the translation (spec sections 16, 28):

* Confidence is preserved verbatim, never upgraded. A 0.71 OCR read stays a
  0.71 observation; the fusion layer weighs it below API-derived numbers.
* An empty vision result is an honest ``"empty"`` observation ("nothing
  readable"), not a failure and never a fabricated read. Only genuinely
  directional, high-enough-confidence reads become Evidence -- and even then
  as ``Assertion.UNCERTAIN`` (visual, never measured), so the critic can
  never mistake them for a calculated fact.
"""

from __future__ import annotations

from ...core.logging import get_logger
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.market_data import MarketData
from ..domain.visual import VisualObservation

logger = get_logger("trading.visual")

#: Below this vision confidence a read is recorded as an observation but never
#: promoted to Evidence -- too weak to lean on, still worth remembering.
EVIDENCE_CONFIDENCE_FLOOR = 0.5


class VisualObservationService:
    """Builds visual observations (and optional VISUAL evidence) from vision reads."""

    def observe_text(
        self,
        blocks: list,
        *,
        instrument_key: str,
    ) -> tuple[VisualObservation, ...]:
        """One observation per OCR text block; an honest empty when none."""
        if not blocks:
            return (
                VisualObservation(
                    kind="empty",
                    label="no readable text",
                    confidence=0.0,
                    source="ocr",
                ),
            )
        return tuple(
            VisualObservation(
                kind="text",
                label=str(block.text),
                confidence=float(block.confidence),
                source="ocr",
                bbox=tuple(block.bbox),
            )
            for block in blocks
        )

    def observe_objects(
        self,
        detections: list,
        *,
        instrument_key: str,
    ) -> tuple[VisualObservation, ...]:
        """One observation per detected object; an honest empty when none."""
        if not detections:
            return (
                VisualObservation(
                    kind="empty",
                    label="no detected objects",
                    confidence=0.0,
                    source="detection",
                ),
            )
        return tuple(
            VisualObservation(
                kind="object",
                label=str(detection.label),
                confidence=float(detection.confidence),
                source="detection",
                bbox=tuple(detection.bbox),
            )
            for detection in detections
        )

    def to_evidence(
        self,
        observations: tuple[VisualObservation, ...],
        data: MarketData,
    ) -> tuple[Evidence, ...]:
        """
        Promote strong visual reads to VISUAL evidence.

        Only ``"text"``/``"object"`` observations at or above
        ``EVIDENCE_CONFIDENCE_FLOOR`` qualify, and every item is
        ``Assertion.UNCERTAIN`` with ``Direction.UNKNOWN`` -- a visual read
        describes what the chart *shows*, it never asserts a directional fact.
        Weight equals the vision confidence, capped at 0.5 so a visual guess
        can never outweigh an API-derived number in fusion.
        """
        items: list[Evidence] = []
        for obs in observations:
            if obs.kind == "empty":
                continue
            if obs.confidence < EVIDENCE_CONFIDENCE_FLOOR:
                continue
            weight = min(0.5, obs.confidence)
            items.append(
                Evidence(
                    instrument_key=data.instrument.key,
                    type=EvidenceType.VISUAL,
                    assertion=Assertion.UNCERTAIN,
                    direction=Direction.UNKNOWN,
                    detail=f"Vision ({obs.source}) read '{obs.label}' "
                    f"at confidence {obs.confidence:.2f}.",
                    weight=weight,
                    confidence=Confidence.from_score(obs.confidence),
                    provenance=data.provenance,
                    quality=data.quality,
                    data={
                        "observation_id": obs.id,
                        "bbox": list(obs.bbox) if obs.bbox else None,
                    },
                )
            )
        return tuple(items)
