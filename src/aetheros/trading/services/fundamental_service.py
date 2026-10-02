"""
Fundamental-analysis service.

Fetches a sourced :class:`FundamentalSnapshot` through an injected
:class:`FundamentalsProvider`, scores each reported metric with a deterministic
signed rubric, and fuses the results into a single auditable
:class:`FundamentalAnalysis` -- the net health/valuation lean, the per-metric
factors behind it, the FUNDAMENTAL :class:`Evidence` it yields, and an honest
``is_reliable`` gate plus ``limitations`` (spec sections 5, 9, 26 item #9).

Every honesty discipline of the rest of the domain holds here: the lean is a
derived interpretation over sourced figures, never presented as the source's own
claim (section 15); a MOCK snapshot, or too few reported metrics to judge, can
never masquerade as a real, reliable read (sections 2, 28, 61); and the scorer
is deterministic, so the same figures always yield the same read. The service
performs no LLM call.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import (
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
)
from ..domain.evidence import Evidence
from ..domain.fundamentals import (
    FundamentalAnalysis,
    FundamentalFactor,
    FundamentalSnapshot,
)
from ..domain.instrument import Instrument
from ..domain.provenance import DataQuality, Provenance
from ..errors import FundamentalsError
from ..events import FundamentalsAnalyzed
from ..providers.fundamentals_base import FundamentalsProvider

logger = get_logger("trading.fundamentals")

# Dead-band on the mean signed health score: |mean| below this is SIDEWAYS
# (metrics reported but no clear lean) rather than a weak directional call.
_DIRECTION_BAND = 0.15

_MOCK_LIMITATION = (
    "Fundamental read rests on synthetic MOCK financials (SourceTier.MOCK) — "
    "not real filings. The read is illustrative only and is not reliable."
)


class FundamentalAnalysisService:
    """Deterministic fundamental analysis for one instrument."""

    def __init__(
        self,
        provider: FundamentalsProvider,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._provider = provider
        self._settings = settings
        self._event_bus = event_bus

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_mock(self) -> bool:
        return self._provider.is_mock

    async def analyze(self, symbol: str | Instrument) -> FundamentalAnalysis:
        instrument = self._coerce_instrument(symbol)

        try:
            snapshot = await self._provider.get_fundamentals(instrument)
        except FundamentalsError:
            raise
        except Exception as exc:  # provider misbehaved -> typed, honest error
            raise FundamentalsError(
                f"Fundamentals provider '{self._provider.name}' failed for "
                f"{instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        analysis = self._analyze_snapshot(instrument, snapshot)
        await self._emit(analysis)
        return analysis

    # ------------------------------------------------------------------
    # Deterministic scoring rubric (pure)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_metric(metric: str, v: float) -> tuple[float, str]:
        """
        Map one reported metric to a signed score in [-1, 1] and a reason.

        Positive = healthy/attractive, negative = weak/expensive, 0 = neutral.
        Bands are fixed and deterministic so the same figure always scores the
        same; a metric this rubric does not recognise returns a neutral 0.
        """
        if metric == "net_income":
            return (0.5, "profitable") if v > 0 else (-1.0, "unprofitable (net loss)")
        if metric == "net_margin":
            if v >= 0.15:
                return 1.0, f"strong net margin ({v:.0%})"
            if v >= 0.05:
                return 0.5, f"healthy net margin ({v:.0%})"
            if v < 0:
                return -1.0, f"negative net margin ({v:.0%})"
            return 0.0, f"thin net margin ({v:.0%})"
        if metric == "operating_margin":
            if v >= 0.15:
                return 1.0, f"strong operating margin ({v:.0%})"
            if v >= 0.05:
                return 0.5, f"healthy operating margin ({v:.0%})"
            if v < 0:
                return -1.0, f"negative operating margin ({v:.0%})"
            return 0.0, f"thin operating margin ({v:.0%})"
        if metric == "gross_margin":
            if v >= 0.40:
                return 0.5, f"high gross margin ({v:.0%})"
            if v < 0.20:
                return -0.5, f"low gross margin ({v:.0%})"
            return 0.0, f"moderate gross margin ({v:.0%})"
        if metric == "revenue_growth_yoy":
            if v >= 0.15:
                return 1.0, f"revenue growing fast ({v:+.0%} YoY)"
            if v >= 0.03:
                return 0.5, f"revenue growing ({v:+.0%} YoY)"
            if v < 0:
                return -1.0, f"revenue contracting ({v:+.0%} YoY)"
            return 0.0, f"flat revenue ({v:+.0%} YoY)"
        if metric == "earnings_growth_yoy":
            if v >= 0.15:
                return 1.0, f"earnings growing fast ({v:+.0%} YoY)"
            if v >= 0.0:
                return 0.5, f"earnings growing ({v:+.0%} YoY)"
            return -1.0, f"earnings falling ({v:+.0%} YoY)"
        if metric == "return_on_equity":
            if v >= 0.15:
                return 1.0, f"strong ROE ({v:.0%})"
            if v >= 0.08:
                return 0.5, f"decent ROE ({v:.0%})"
            if v < 0:
                return -1.0, f"negative ROE ({v:.0%})"
            return 0.0, f"weak ROE ({v:.0%})"
        if metric == "debt_to_equity":
            if v <= 0.5:
                return 1.0, f"low leverage (D/E {v:.2f})"
            if v <= 1.0:
                return 0.5, f"moderate leverage (D/E {v:.2f})"
            if v >= 2.5:
                return -1.0, f"high leverage (D/E {v:.2f})"
            if v >= 1.5:
                return -0.5, f"elevated leverage (D/E {v:.2f})"
            return 0.0, f"leverage in range (D/E {v:.2f})"
        if metric == "current_ratio":
            if v >= 1.5:
                return 0.5, f"comfortable liquidity (current {v:.2f})"
            if v < 1.0:
                return -1.0, f"liquidity risk (current {v:.2f})"
            return 0.0, f"adequate liquidity (current {v:.2f})"
        if metric == "free_cash_flow":
            return (0.5, "positive free cash flow") if v > 0 else (-1.0, "burning cash")
        if metric == "pe_ratio":
            if v < 0:
                return -1.0, "loss-making (negative P/E)"
            if v <= 20:
                return 0.5, f"reasonable P/E ({v:.1f})"
            if v >= 40:
                return -0.5, f"rich P/E ({v:.1f})"
            return 0.0, f"moderate P/E ({v:.1f})"
        if metric == "pb_ratio":
            if v <= 1.5:
                return 0.5, f"trades near book (P/B {v:.1f})"
            if v >= 6:
                return -0.5, f"expensive vs book (P/B {v:.1f})"
            return 0.0, f"moderate P/B ({v:.1f})"
        if metric == "price_to_sales":
            if v <= 2:
                return 0.5, f"reasonable P/S ({v:.1f})"
            if v >= 10:
                return -0.5, f"expensive P/S ({v:.1f})"
            return 0.0, f"moderate P/S ({v:.1f})"
        if metric == "dividend_yield":
            return (0.25, f"pays a dividend ({v:.1%})") if v > 0 else (0.0, "no dividend")
        return 0.0, ""

    # ------------------------------------------------------------------
    # Aggregation (pure, deterministic)
    # ------------------------------------------------------------------

    def _analyze_snapshot(
        self, instrument: Instrument, snapshot: FundamentalSnapshot
    ) -> FundamentalAnalysis:
        is_mock = self._provider.is_mock
        provenance = Provenance(
            source=self._provider.name,
            tier=self._provider.tier,
            detail="deterministic signed-factor rubric over sourced financials",
        )

        factors: list[FundamentalFactor] = []
        for metric in snapshot.reported_metrics:
            value = getattr(snapshot, metric)
            # 'revenue' is a scale, not a directional signal on its own — skip.
            if metric == "revenue":
                continue
            score, detail = self._score_metric(metric, float(value))
            fdir = (
                Direction.UP if score > 0 else Direction.DOWN if score < 0 else Direction.SIDEWAYS
            )
            factors.append(
                FundamentalFactor(
                    metric=metric,
                    value=float(value),
                    direction=fdir,
                    score=score,
                    detail=detail,
                )
            )

        scored_count = len(factors)
        min_metrics = self._settings.TRADING_FUND_MIN_METRICS

        issues: list[str] = []
        if is_mock:
            issues.append(_MOCK_LIMITATION)
        if snapshot.metric_count == 0:
            issues.append("No fundamental metrics were reported for the instrument.")
            status = DataQualityStatus.MISSING
        elif scored_count < min_metrics:
            issues.append(
                f"Only {scored_count} metric(s) scored (< {min_metrics}); coverage "
                f"is too thin to judge fundamentals."
            )
            status = DataQualityStatus.PARTIAL
        else:
            status = DataQualityStatus.OK
        quality = DataQuality(status=status, issues=tuple(issues), freshness_seconds=0.0)

        if scored_count == 0:
            health_score = 0.0
            direction = Direction.UNKNOWN
            confidence = Confidence.LOW
        else:
            health_score = round(sum(f.score for f in factors) / scored_count, 6)
            if health_score >= _DIRECTION_BAND:
                direction = Direction.UP
            elif health_score <= -_DIRECTION_BAND:
                direction = Direction.DOWN
            else:
                direction = Direction.SIDEWAYS
            if scored_count < min_metrics:
                confidence = Confidence.LOW
            else:
                confidence = Confidence.from_score(abs(health_score))

        is_reliable = quality.usable and not is_mock and scored_count >= min_metrics

        limitations = self._build_limitations(
            is_mock=is_mock,
            scored_count=scored_count,
            min_metrics=min_metrics,
            is_reliable=is_reliable,
        )
        evidence = self._build_evidence(
            instrument=instrument,
            direction=direction,
            health_score=health_score,
            factors=tuple(factors),
            provenance=provenance,
            quality=quality,
        )

        return FundamentalAnalysis(
            instrument=instrument,
            snapshot=snapshot,
            direction=direction,
            health_score=health_score,
            confidence=confidence,
            factors=tuple(factors),
            evidence=evidence,
            provenance=provenance,
            quality=quality,
            is_reliable=is_reliable,
            limitations=limitations,
        )

    @staticmethod
    def _build_limitations(
        *, is_mock: bool, scored_count: int, min_metrics: int, is_reliable: bool
    ) -> tuple[str, ...]:
        limitations: list[str] = []
        if is_mock:
            limitations.append(_MOCK_LIMITATION)
        if scored_count == 0:
            limitations.append(
                "No fundamental metrics were reported, so this provides no signal."
            )
        elif scored_count < min_metrics:
            limitations.append(
                f"Only {scored_count} metric(s) scored (< {min_metrics}); the "
                f"fundamental read is too thin to be reliable."
            )
        if not is_reliable and not is_mock and scored_count >= min_metrics:
            # Defensive: keep the honesty note present if some future gate flips.
            limitations.append(
                "Fundamental read is not reliable for this instrument."
            )
        return tuple(limitations)

    def _build_evidence(
        self,
        *,
        instrument: Instrument,
        direction: Direction,
        health_score: float,
        factors: tuple[FundamentalFactor, ...],
        provenance: Provenance,
        quality: DataQuality,
    ) -> tuple[Evidence, ...]:
        """
        Derive discrete FUNDAMENTAL Evidence from the health read.

        An aggregate claim captures the fused net lean; per-metric claims record
        each directional factor. All are soft evidence: weights are capped below
        the technical layer's, and a MOCK provenance keeps every item
        ``is_reliable == False``.
        """
        items: list[Evidence] = []

        if direction in (Direction.UP, Direction.DOWN):
            weight = round(min(0.6, 0.2 + abs(health_score) * 0.5), 4)
            items.append(
                Evidence(
                    instrument_key=instrument.key,
                    type=EvidenceType.FUNDAMENTAL,
                    assertion=Assertion.CALCULATED,
                    direction=direction,
                    detail=(
                        f"Fundamental health leans {direction.value} "
                        f"(score {health_score:+.2f} over {len(factors)} metrics)."
                    ),
                    weight=weight,
                    confidence=Confidence.from_score(weight),
                    provenance=provenance,
                    quality=quality,
                    data={"health_score": health_score, "metrics": len(factors)},
                )
            )

        for f in factors:
            if f.direction not in (Direction.UP, Direction.DOWN):
                continue
            weight = round(min(0.4, abs(f.score) * 0.4), 4)
            items.append(
                Evidence(
                    instrument_key=instrument.key,
                    type=EvidenceType.FUNDAMENTAL,
                    assertion=Assertion.CALCULATED,
                    direction=f.direction,
                    detail=f"{f.metric} reads {f.direction.value}: {f.detail}",
                    weight=weight,
                    confidence=Confidence.from_score(weight),
                    provenance=provenance,
                    quality=quality,
                    data={"metric": f.metric, "value": f.value, "score": f.score},
                )
            )
        return tuple(items)

    # ------------------------------------------------------------------
    # Coercion + events
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_instrument(symbol: str | Instrument) -> Instrument:
        if isinstance(symbol, Instrument):
            return symbol
        try:
            return Instrument.parse(symbol)
        except ValueError as exc:
            raise FundamentalsError(str(exc), context={"symbol": symbol}) from exc

    async def _emit(self, analysis: FundamentalAnalysis) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                FundamentalsAnalyzed(
                    instrument_key=analysis.instrument.key,
                    direction=analysis.direction.value,
                    health_score=analysis.health_score,
                    confidence=analysis.confidence.value,
                    scored_metric_count=analysis.scored_metric_count,
                    reported_metric_count=analysis.snapshot.metric_count,
                    is_reliable=analysis.is_reliable,
                    source_tier=analysis.provenance.tier.value
                    if analysis.provenance
                    else "",
                )
            )
        except Exception:  # event delivery must never break analysis
            logger.exception("Failed to publish FundamentalsAnalyzed")

