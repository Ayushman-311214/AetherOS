"""
Structured grounding types.

Three small dataclasses carry the whole contract:

* :class:`GroundingTarget` -- the parsed natural-language request (what to find,
  what kind of thing, any spatial relation or ordinal).
* :class:`GroundingCandidate` -- one possible on-screen match, with geometry, a
  source (``"ocr"`` or ``"detection"``), a score and a human-readable reason.
* :class:`GroundingResult` -- the public answer handed back to the agent: the
  selected element's bbox and centre, a confidence band, whether it is safe to
  act on, and the evidence for the choice.

Geometry mirrors :class:`~aetheros.vision.models.text.TextBlock` and
:class:`~aetheros.vision.models.detection.Detection` (left/top/right/bottom) so
candidates wrap either source without translation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Confidence band labels. The numeric thresholds live in configuration
# (Settings.GROUNDING_CONFIDENCE_*) -- these are just the names the agent sees.
BAND_HIGH = "HIGH"
BAND_MEDIUM = "MEDIUM"
BAND_LOW = "LOW"
BAND_NONE = "NONE"


@dataclass(slots=True)
class GroundingTarget:
    """A natural-language target parsed into structured intent."""

    raw: str
    text: str = ""
    element_type: str | None = None
    relation: str | None = None
    anchor: str | None = None
    ordinal: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "text": self.text,
            "element_type": self.element_type,
            "relation": self.relation,
            "anchor": self.anchor,
            "ordinal": self.ordinal,
        }


@dataclass(slots=True)
class GroundingCandidate:
    """One possible on-screen match for a target.

    Wraps either an OCR ``TextBlock`` or a detected ``Detection``: the geometry
    is identical, ``source`` records which perception produced it, and ``score``
    is this candidate's match strength (0..1) against the target.
    """

    text: str
    left: int
    top: int
    right: int
    bottom: int
    score: float
    source: str
    element_type: str | None = None
    reason: str = ""

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return (
            self.left + self.width // 2,
            self.top + self.height // 2,
        )

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)

    def to_dict(self) -> dict[str, Any]:
        cx, cy = self.center
        return {
            "text": self.text,
            "bbox": {
                "x": self.left,
                "y": self.top,
                "width": self.width,
                "height": self.height,
            },
            "center": {"x": cx, "y": cy},
            "score": round(self.score, 4),
            "source": self.source,
            "element_type": self.element_type,
            "reason": self.reason,
        }


@dataclass(slots=True)
class GroundingResult:
    """The public grounding answer handed to the agent.

    ``success`` says whether a usable element was found at all. ``safe_to_act``
    is the stricter gate: it is only true when confidence reached the HIGH band
    and the match was unambiguous, so an agent can click on it without a second
    look. A MEDIUM or LOW result still carries a bbox and centre (so a human or
    a confirm step can use it) but must not be auto-actioned.
    """

    success: bool
    query: str
    matched_text: str | None = None
    element_type: str | None = None
    bbox: dict[str, int] | None = None
    center: dict[str, int] | None = None
    confidence: float = 0.0
    confidence_band: str = BAND_NONE
    source: str = ""
    safe_to_act: bool = False
    reason: str = ""
    candidates_considered: int = 0
    target: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "query": self.query,
            "matched_text": self.matched_text,
            "element_type": self.element_type,
            "bbox": self.bbox,
            "center": self.center,
            "confidence": round(self.confidence, 4),
            "confidence_band": self.confidence_band,
            "source": self.source,
            "safe_to_act": self.safe_to_act,
            "reason": self.reason,
            "candidates_considered": self.candidates_considered,
            "target": self.target,
        }

    @classmethod
    def from_candidate(
        cls,
        candidate: GroundingCandidate,
        *,
        query: str,
        confidence: float,
        band: str,
        safe_to_act: bool,
        reason: str,
        candidates_considered: int,
        target: dict[str, Any],
    ) -> "GroundingResult":
        cx, cy = candidate.center
        return cls(
            success=True,
            query=query,
            matched_text=candidate.text,
            element_type=candidate.element_type,
            bbox={
                "x": candidate.left,
                "y": candidate.top,
                "width": candidate.width,
                "height": candidate.height,
            },
            center={"x": cx, "y": cy},
            confidence=confidence,
            confidence_band=band,
            source=candidate.source,
            safe_to_act=safe_to_act,
            reason=reason,
            candidates_considered=candidates_considered,
            target=target,
        )

    @classmethod
    def failure(
        cls,
        *,
        query: str,
        reason: str,
        candidates_considered: int = 0,
        target: dict[str, Any] | None = None,
    ) -> "GroundingResult":
        return cls(
            success=False,
            query=query,
            confidence=0.0,
            confidence_band=BAND_NONE,
            safe_to_act=False,
            reason=reason,
            candidates_considered=candidates_considered,
            target=target or {},
        )


__all__ = [
    "GroundingTarget",
    "GroundingCandidate",
    "GroundingResult",
    "BAND_HIGH",
    "BAND_MEDIUM",
    "BAND_LOW",
    "BAND_NONE",
]
