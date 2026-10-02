"""
Evidence value object.

Evidence is the atomic unit the decision layers reason over: a single, sourced,
confidence-weighted claim about an instrument ("RSI is 72, overbought" /
"price closed above the 50-day SMA"). Every Evidence carries:

- what kind of thing it is (EvidenceType) and how the claim was arrived at
  (Assertion: OBSERVED / CALCULATED / DETECTED / INFERRED / UNCERTAIN),
- the directional lean it supports and how strongly (weight 0..1),
- its provenance and a data-quality read, so a stale or mock input never
  silently masquerades as a fresh primary observation,
- a *deterministic* stable id derived from its content, so the same evidence
  computed twice gets the same id and downstream persistence (deferred Memory
  layer) can dedupe and cross-reference without a database round-trip.

The id is content-addressed rather than random precisely so a prediction and
its evidence stay auditable across runs (spec sections 8, 15, 61).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Assertion, Confidence, Direction, EvidenceType
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stable_id(
    *,
    instrument_key: str,
    evidence_type: str,
    assertion: str,
    direction: str,
    detail: str,
) -> str:
    """
    Content-addressed id: same claim -> same id, independent of wall-clock.

    Deliberately excludes timestamps and weights so that re-deriving the "same"
    structural fact (e.g. "price above SMA50") is recognised as the same piece
    of evidence rather than a brand-new one every tick.
    """
    payload = "|".join(
        (instrument_key, evidence_type, assertion, direction, detail.strip().lower())
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"ev_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class Evidence:
    """A single sourced, weighted claim supporting a directional read."""

    instrument_key: str
    type: EvidenceType
    assertion: Assertion
    direction: Direction
    detail: str
    weight: float  # 0..1 strength of THIS piece, not a probability
    confidence: Confidence
    provenance: Provenance
    quality: DataQuality
    created_at: datetime = field(default_factory=_utcnow)
    data: dict[str, Any] = field(default_factory=dict)

    # Deterministic, content-addressed. Computed in __post_init__ if not given.
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                _stable_id(
                    instrument_key=self.instrument_key,
                    evidence_type=self.type.value,
                    assertion=self.assertion.value,
                    direction=self.direction.value,
                    detail=self.detail,
                ),
            )
        # Clamp weight into [0, 1] rather than trusting the caller.
        w = self.weight
        if w < 0.0 or w > 1.0:
            object.__setattr__(self, "weight", max(0.0, min(1.0, w)))

    @property
    def is_reliable(self) -> bool:
        """Usable, non-mock, and at least calculated/observed (not inferred)."""
        return (
            self.quality.usable
            and not self.provenance.is_mock
            and self.assertion in (Assertion.OBSERVED, Assertion.CALCULATED, Assertion.DETECTED)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instrument_key": self.instrument_key,
            "type": self.type.value,
            "assertion": self.assertion.value,
            "direction": self.direction.value,
            "detail": self.detail,
            "weight": self.weight,
            "confidence": self.confidence.value,
            "created_at": self.created_at.isoformat(),
            "data": self.data,
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
        }
