"""
Broad-market macro-context service.

Reads *what the overall market is doing* -- risk-on, risk-off or neutral -- from
a market benchmark's own regime (CLAUDE.md sections 2, 5, 27). It is the context
a single-name signal sits inside, distinct from an instrument's own regime and
from relative strength (instrument-vs-benchmark).

It does NOT re-implement the trend/volatility maths: it composes
:class:`RegimeService` (dependency-injected) on the benchmark's candles and maps
the resulting :class:`MarketRegime` to a :class:`MarketPosture` (section 22 --
reuse, never duplicate). The service itself does no I/O -- the caller fetches the
benchmark candles and hands them in -- so it is trivially unit-testable and
deterministic.

The read inherits every honesty guarantee of the regime read it composes
(sections 5, 28): mock, unusable or too-thin benchmark data yields
``MarketPosture.UNKNOWN`` with ``is_reliable`` False and no fabricated posture.
When the read is determinate it emits a single ``EvidenceType.MACRO``
:class:`Evidence` item.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

from ...config.settings import Settings
from ..domain.enums import (
    Assertion,
    Confidence,
    EvidenceType,
    MarketPosture,
)
from ..domain.evidence import Evidence
from ..domain.macro import MacroContext
from ..domain.market_data import MarketData
from .regime_service import RegimeService


class MacroContextService:
    """Deterministic broad-market risk-posture read over a benchmark's candles."""

    def __init__(self, regime: RegimeService, settings: Settings) -> None:
        self._regime = regime
        self._settings = settings

    @property
    def default_benchmark(self) -> str:
        """The configured benchmark symbol used when a caller names none."""
        return self._settings.TRADING_BENCHMARK_SYMBOL

    async def analyze(self, benchmark_data: MarketData) -> MacroContext:
        regime = await self._regime.detect(benchmark_data)
        posture = MarketPosture.from_regime(regime.regime)

        limitations = tuple(regime.limitations)
        observation = self._describe(posture, regime.regime, benchmark_data)

        evidence = None
        if posture is not MarketPosture.UNKNOWN:
            evidence = self._evidence(
                benchmark_data, posture, regime.trend_strength, regime.confidence,
                observation,
            )

        return MacroContext(
            benchmark=benchmark_data.instrument,
            timeframe_value=benchmark_data.timeframe.value,
            posture=posture,
            regime=regime.regime,
            confidence=regime.confidence,
            quality=regime.quality,
            provenance=regime.provenance,
            evidence=evidence,
            observation=observation,
            limitations=limitations,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _describe(
        posture: MarketPosture,
        regime,
        benchmark_data: MarketData,
    ) -> str:
        key = benchmark_data.instrument.key
        if posture is MarketPosture.UNKNOWN:
            return (
                f"Broad-market posture undetermined: the {key} benchmark regime is "
                "insufficient or unusable."
            )
        phrase = {
            MarketPosture.RISK_ON: "risk-on (the broad market is trending up)",
            MarketPosture.RISK_OFF: (
                "risk-off (the broad market is trending down or whipsawing)"
            ),
            MarketPosture.NEUTRAL: "neutral (the broad market is range-bound)",
        }[posture]
        return f"Broad market ({key}, regime '{regime.value}') is {phrase}."

    def _evidence(
        self,
        benchmark_data: MarketData,
        posture: MarketPosture,
        trend_strength: float | None,
        confidence: Confidence,
        detail: str,
    ) -> Evidence:
        weight = trend_strength if trend_strength is not None else 0.0
        weight = max(0.0, min(1.0, weight))
        return Evidence(
            instrument_key=benchmark_data.instrument.key,
            type=EvidenceType.MACRO,
            assertion=Assertion.CALCULATED,
            direction=posture.direction,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=benchmark_data.provenance,
            quality=benchmark_data.quality,
            data={
                "posture": posture.value,
                "benchmark": benchmark_data.instrument.key,
            },
        )
