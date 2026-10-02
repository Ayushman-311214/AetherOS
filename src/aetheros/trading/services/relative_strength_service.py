"""
Relative-strength (sector/benchmark) service.

Computes how one instrument has performed relative to a benchmark over a fixed
lookback window -- the deterministic engine behind the spec's "positive sector
strength" evidence line (CLAUDE.md sections 2, 5, 27). It follows the same shape
as :class:`RegimeService`: the service operates purely on two ``MarketData``
domain objects it is handed (no LLM, no I/O), so it is trivially unit-testable
with crafted candles, and identical inputs always yield the identical read
(section 22).

The read is honest about its own reliability (sections 9, 15, 28): mock,
unusable or too-thin data on *either* series yields ``Direction.UNKNOWN`` with
the reason recorded in ``limitations`` rather than a fabricated lean, and a
benchmark drawn from MOCK data can never make the comparison reliable even when
the instrument's own data is real. When the read is determinate it emits a
single ``EvidenceType.MARKET_CONTEXT`` :class:`Evidence` item so downstream
layers can consume the excess-return claim like any other piece of evidence.

This increment is deliberately standalone: the service and its tool stand beside
the existing pipeline and are not fused into the orchestrator, so no existing
behaviour changes.
"""

from __future__ import annotations

from ...config.settings import Settings
from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.market_data import MarketData
from ..domain.provenance import DataQuality, Provenance
from ..domain.relative_strength import RelativeStrengthAnalysis

# Excess return over the window that maps to a full-strength (weight 1.0)
# evidence claim; anything larger is clamped. 10% out/under-performance over the
# lookback is treated as a strong relative move. This scales the *weight* of a
# single piece of evidence -- it is never a probability.
_FULL_WEIGHT_EXCESS = 0.10


class RelativeStrengthService:
    """Deterministic instrument-vs-benchmark relative-strength read over candles."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def default_benchmark(self) -> str:
        """The configured benchmark symbol used when a caller names none."""
        return self._settings.TRADING_BENCHMARK_SYMBOL

    def analyze(
        self,
        instrument_data: MarketData,
        benchmark_data: MarketData,
        *,
        lookback: int | None = None,
    ) -> RelativeStrengthAnalysis:
        window = lookback if lookback is not None else self._settings.TRADING_RS_LOOKBACK
        min_bars = self._settings.TRADING_RS_MIN_BARS
        dead_band = self._settings.TRADING_RS_DEAD_BAND

        limitations: list[str] = []
        if instrument_data.provenance.is_mock:
            limitations.append(
                "Instrument data is MOCK; relative strength is illustrative, not "
                "a real market read."
            )
        if benchmark_data.provenance.is_mock:
            limitations.append(
                "Benchmark data is MOCK; relative strength is illustrative, not "
                "a real market read."
            )
        if not instrument_data.quality.ok:
            limitations.extend(instrument_data.quality.issues)
        if not benchmark_data.quality.ok:
            limitations.extend(
                f"benchmark: {issue}" for issue in benchmark_data.quality.issues
            )

        # Align to the shorter of the two usable series and the requested window.
        n = min(len(instrument_data.candles), len(benchmark_data.candles))
        used = min(window, n)

        both_usable = (
            instrument_data.quality.usable and benchmark_data.quality.usable
        )
        if not both_usable or used < min_bars:
            if used < min_bars:
                limitations.append(
                    f"Only {used} aligned candles; need at least {min_bars} for a "
                    "relative-strength read."
                )
            return self._unknown(
                instrument_data, benchmark_data, used, tuple(limitations)
            )

        inst_ret = self._window_return(instrument_data, used)
        bench_ret = self._window_return(benchmark_data, used)
        if inst_ret is None or bench_ret is None:
            limitations.append(
                "A window start price was non-positive; relative return "
                "undetermined."
            )
            return self._unknown(
                instrument_data, benchmark_data, used, tuple(limitations)
            )

        excess = inst_ret - bench_ret
        if excess > dead_band:
            direction = Direction.UP
        elif excess < -dead_band:
            direction = Direction.DOWN
        else:
            direction = Direction.SIDEWAYS

        weight = min(1.0, abs(excess) / _FULL_WEIGHT_EXCESS)
        confidence = Confidence.from_score(weight)
        observation = self._describe(
            direction, inst_ret, bench_ret, excess, used,
            benchmark_data.instrument.key,
        )
        evidence = self._evidence(
            instrument_data, direction, weight, confidence, excess, used,
            benchmark_data.instrument.key, observation,
        )

        return RelativeStrengthAnalysis(
            instrument=instrument_data.instrument,
            benchmark_key=benchmark_data.instrument.key,
            timeframe_value=instrument_data.timeframe.value,
            lookback=used,
            instrument_return=round(inst_ret, 6),
            benchmark_return=round(bench_ret, 6),
            relative_return=round(excess, 6),
            direction=direction,
            confidence=confidence,
            quality=instrument_data.quality,
            provenance=instrument_data.provenance,
            benchmark_quality=benchmark_data.quality,
            benchmark_provenance=benchmark_data.provenance,
            evidence=evidence,
            observation=observation,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _window_return(data: MarketData, used: int) -> float | None:
        """Simple return over the last ``used`` closes, or None if it can't form."""
        closes = data.closes()
        first = float(closes[-used])
        last = float(closes[-1])
        if first <= 0.0:
            return None
        return last / first - 1.0

    @staticmethod
    def _describe(
        direction: Direction,
        inst_ret: float,
        bench_ret: float,
        excess: float,
        used: int,
        benchmark_key: str,
    ) -> str:
        verb = {
            Direction.UP: "outperformed",
            Direction.DOWN: "underperformed",
            Direction.SIDEWAYS: "tracked",
        }[direction]
        return (
            f"Over {used} bars the instrument returned {inst_ret * 100:.2f}% vs "
            f"{benchmark_key} {bench_ret * 100:.2f}% ({excess * 100:+.2f}% excess): "
            f"{verb} the benchmark."
        )

    def _evidence(
        self,
        instrument_data: MarketData,
        direction: Direction,
        weight: float,
        confidence: Confidence,
        excess: float,
        used: int,
        benchmark_key: str,
        detail: str,
    ) -> Evidence:
        return Evidence(
            instrument_key=instrument_data.instrument.key,
            type=EvidenceType.MARKET_CONTEXT,
            assertion=Assertion.CALCULATED,
            direction=direction,
            detail=detail,
            weight=weight,
            confidence=confidence,
            provenance=instrument_data.provenance,
            quality=instrument_data.quality,
            data={
                "benchmark": benchmark_key,
                "relative_return": round(excess, 6),
                "lookback": used,
            },
        )

    @staticmethod
    def _unknown(
        instrument_data: MarketData,
        benchmark_data: MarketData,
        used: int,
        limitations: tuple[str, ...],
    ) -> RelativeStrengthAnalysis:
        return RelativeStrengthAnalysis(
            instrument=instrument_data.instrument,
            benchmark_key=benchmark_data.instrument.key,
            timeframe_value=instrument_data.timeframe.value,
            lookback=used,
            instrument_return=None,
            benchmark_return=None,
            relative_return=None,
            direction=Direction.UNKNOWN,
            confidence=Confidence.LOW,
            quality=instrument_data.quality,
            provenance=instrument_data.provenance,
            benchmark_quality=benchmark_data.quality,
            benchmark_provenance=benchmark_data.provenance,
            evidence=None,
            observation=(
                "Relative strength undetermined: insufficient or unusable data."
            ),
            limitations=limitations,
        )
