"""
The evidence ledger.

:class:`EvidenceLedger` is what the signal engine aggregates over: every
:class:`~aetheros.trading.domain.evidence.Evidence` item the sources produced,
plus an explicit :class:`MissingSource` for each expected source that supplied
nothing. It is the single place the aggregation, the contradiction split and
the missing-data accounting live -- so "what evidence was there, what was
against it, and what was missing" is answerable in one pass.

The two honesty rules it enforces structurally:

* **Missing is not neutral.** A source that supplied no evidence is a
  ``MissingSource`` with a reason, counted toward ``coverage`` -- it is never
  folded into the score as if it had voted, and it is never dropped silently.
* **Unreliable evidence can never tip a direction.** Only ``is_reliable``
  (usable, non-mock, observed/calculated/detected) items contribute to the net
  weight; unreliable items are listed but scored as zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.enums import Direction, EvidenceType
from ..domain.evidence import Evidence


@dataclass(frozen=True, slots=True)
class MissingSource:
    """
    An expected evidence source that supplied nothing for this assessment.

    ``source`` names the category that was absent (an ``EvidenceType`` value or
    a feature-layer name); ``reason`` is why it is missing ("not provided",
    "insufficient bars", "provider offline"). Being recorded here is what stops
    the ledger ever treating an absent source as a neutral vote.
    """

    source: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class EvidenceLedger:
    """
    The aggregated evidence for one assessment.

    ``items`` is every evidence item supplied; ``missing`` is the explicit
    accounting of the expected sources that contributed none. The supporting /
    opposing split is *relative to* ``fused_direction`` -- the same ledger can
    be read for either side.
    """

    items: tuple[Evidence, ...] = ()
    missing: tuple[MissingSource, ...] = ()
    fused_direction: Direction = Direction.UNKNOWN

    # ------------------------------------------------------------------
    # Directional accounting (reliable items only)
    # ------------------------------------------------------------------

    def _directional(self, side: Direction) -> tuple[Evidence, ...]:
        return tuple(
            e
            for e in self.items
            if e.is_reliable and e.direction is side
        )

    @property
    def supporting(self) -> tuple[Evidence, ...]:
        """Reliable items agreeing with the fused direction."""
        return self._directional(self.fused_direction)

    @property
    def opposing(self) -> tuple[Evidence, ...]:
        """Reliable items contradicting the fused direction."""
        other = (
            Direction.DOWN
            if self.fused_direction is Direction.UP
            else Direction.UP
        )
        if self.fused_direction not in (Direction.UP, Direction.DOWN):
            return ()
        return self._directional(other)

    @property
    def reliable(self) -> tuple[Evidence, ...]:
        return tuple(e for e in self.items if e.is_reliable)

    @property
    def reliable_count(self) -> int:
        return len(self.reliable)

    def weight_for(self, side: Direction) -> float:
        return round(sum(e.weight for e in self._directional(side)), 6)

    @property
    def supporting_weight(self) -> float:
        return self.weight_for(self.fused_direction)

    @property
    def opposing_weight(self) -> float:
        if self.fused_direction not in (Direction.UP, Direction.DOWN):
            return 0.0
        other = (
            Direction.DOWN
            if self.fused_direction is Direction.UP
            else Direction.UP
        )
        return self.weight_for(other)

    @property
    def net_weight(self) -> float:
        """Supporting minus opposing weight (signed)."""
        return round(self.supporting_weight - self.opposing_weight, 6)

    # ------------------------------------------------------------------
    # Coverage (how much of the expected evidence actually arrived)
    # ------------------------------------------------------------------

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    def coverage(self, expected_sources: int) -> float:
        """
        Share of expected sources that supplied evidence, in ``[0,1]``.

        ``expected_sources`` is the count of sources the caller asked for;
        supplied = expected - missing. Used as a confidence input -- a read
        resting on half its expected evidence is honestly thinner than one on
        all of it.
        """
        if expected_sources <= 0:
            return 0.0
        supplied = max(0, expected_sources - self.missing_count)
        return round(min(1.0, supplied / expected_sources), 4)

    def by_type(self, evidence_type: EvidenceType) -> tuple[Evidence, ...]:
        return tuple(e for e in self.items if e.type is evidence_type)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fused_direction": self.fused_direction.value,
            "item_count": len(self.items),
            "reliable_count": self.reliable_count,
            "supporting_weight": self.supporting_weight,
            "opposing_weight": self.opposing_weight,
            "net_weight": self.net_weight,
            "missing": [m.to_dict() for m in self.missing],
            "items": [e.to_dict() for e in self.items],
        }
