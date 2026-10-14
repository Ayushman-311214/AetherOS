"""
Multi-timeframe confirmation service.

Compares an instrument's base-timeframe directional read to its
higher-timeframe read and classifies the alignment (CLAUDE.md section 5): a call
with the higher-timeframe trend is CONFIRMED, one against it is a CONFLICT, and a
trendless higher timeframe is NEUTRAL. It composes the analysis layer (section 22
-- reuse, never duplicate the signal maths): the caller runs both analyses and
hands the two :class:`TradingAnalysis` objects in, so the service is pure (no
LLM, no I/O) and trivially unit-testable, and identical inputs always yield the
identical read.

It is honest about its own reliability (sections 5, 28): mock, unusable or
too-thin data on *either* timeframe, or an undetermined higher-timeframe trend,
yields ``TimeframeAlignment.UNKNOWN`` with ``is_reliable`` False and no fabricated
alignment. When the higher-timeframe trend is determinate on reliable data it
emits a single ``EvidenceType.TREND`` :class:`Evidence` item carrying that trend
as context.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

from ...config.settings import Settings
from ..domain.analysis import TradingAnalysis
from ..domain.enums import (
    Assertion,
    Confidence,
    Direction,
    EvidenceType,
    TimeframeAlignment,
)
from ..domain.evidence import Evidence
from ..domain.multi_timeframe import MultiTimeframeAnalysis

_WEIGHTS = {
    TimeframeAlignment.CONFIRMED: 0.6,
    TimeframeAlignment.CONFLICT: 0.2,
    TimeframeAlignment.NEUTRAL: 0.3,
    TimeframeAlignment.UNKNOWN: 0.0,
}


class MultiTimeframeService:
    """Deterministic base-vs-higher-timeframe confirmation read."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def default_higher_timeframe(self) -> str:
        """The higher timeframe used when a caller names none."""
        return self._settings.TRADING_MTF_HIGHER_TIMEFRAME

    def analyze(
        self,
        base: TradingAnalysis,
        higher: TradingAnalysis,
    ) -> MultiTimeframeAnalysis:
        base_dir = base.direction
        higher_dir = higher.direction

        limitations: list[str] = []
        if base.provenance.is_mock:
            limitations.append(
                "Base-timeframe data is MOCK; multi-timeframe read is illustrative."
            )
        if higher.provenance.is_mock:
            limitations.append(
                "Higher-timeframe data is MOCK; multi-timeframe read is illustrative."
            )
        if not base.quality.usable:
            limitations.append("Base-timeframe data is unusable.")
        if not higher.quality.usable:
            limitations.append("Higher-timeframe data is unusable.")

        alignment = self._classify(base_dir, higher_dir)
        weight = _WEIGHTS[alignment]
        confidence = Confidence.from_score(weight)
        observation = self._describe(
            alignment, base_dir, higher_dir, base.timeframe_value,
            higher.timeframe_value,
        )

        both_usable = base.quality.usable and higher.quality.usable
        any_mock = base.provenance.is_mock or higher.provenance.is_mock
        evidence = None
        if both_usable and not any_mock and higher_dir in (Direction.UP, Direction.DOWN):
            evidence = self._evidence(
                base, higher.timeframe_value, higher_dir, weight, confidence,
                alignment, observation,
            )

        return MultiTimeframeAnalysis(
            instrument=base.instrument,
            base_timeframe=base.timeframe_value,
            higher_timeframe=higher.timeframe_value,
            base_direction=base_dir,
            higher_direction=higher_dir,
            alignment=alignment,
            confidence=confidence,
            quality=base.quality,
            provenance=base.provenance,
            higher_quality=higher.quality,
            higher_provenance=higher.provenance,
            evidence=evidence,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _classify(base_dir: Direction, higher_dir: Direction) -> TimeframeAlignment:
        if higher_dir is Direction.UNKNOWN or base_dir is Direction.UNKNOWN:
            return TimeframeAlignment.UNKNOWN
        if higher_dir in (Direction.UP, Direction.DOWN):
            if base_dir is higher_dir:
                return TimeframeAlignment.CONFIRMED
            if base_dir in (Direction.UP, Direction.DOWN):
                return TimeframeAlignment.CONFLICT
        # Higher timeframe is trendless (SIDEWAYS), or base has no side.
        return TimeframeAlignment.NEUTRAL

    @staticmethod
    def _describe(
        alignment: TimeframeAlignment,
        base_dir: Direction,
        higher_dir: Direction,
        base_tf: str,
        higher_tf: str,
    ) -> str:
        if alignment is TimeframeAlignment.UNKNOWN:
            return (
                f"Multi-timeframe alignment undetermined ({base_tf} "
                f"'{base_dir.value}' vs {higher_tf} '{higher_dir.value}')."
            )
        verb = {
            TimeframeAlignment.CONFIRMED: "confirms",
            TimeframeAlignment.CONFLICT: "conflicts with",
            TimeframeAlignment.NEUTRAL: "is neutral to",
        }[alignment]
        return (
            f"The {higher_tf} trend '{higher_dir.value}' {verb} the {base_tf} "
            f"'{base_dir.value}' read."
        )

    def _evidence(
        self,
        base: TradingAnalysis,
        higher_tf: str,
        higher_dir: Direction,
        weight: float,
        confidence: Confidence,
        alignment: TimeframeAlignment,
        detail: str,
    ) -> Evidence:
        return Evidence(
            instrument_key=base.instrument.key,
            type=EvidenceType.TREND,
            assertion=Assertion.CALCULATED,
            direction=higher_dir,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=base.provenance,
            quality=base.quality,
            data={
                "alignment": alignment.value,
                "higher_timeframe": higher_tf,
            },
        )
