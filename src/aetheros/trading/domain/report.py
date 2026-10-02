"""
Composed trading-report value object.

A :class:`TradingReport` is the final, auditable product of the deterministic
core: it ties one instrument's evidence-grounded analysis, its risk geometry,
an optional walk-forward backtest and the critic's go/no-go verdict into the
single situation report the spec's section 27 describes. It is assembled by the
:class:`OrchestrationService`; it computes nothing itself, so there is a single
source of truth for every number (the sub-objects it holds).

Two honesty rules are structural here, not optional:

* **No fabricated probability.** A calibrated P(up)/P(down) belongs to the later
  quant/calibration layers (spec sections 6, 7); until those exist and are
  validated on real data, ``probability`` is ``None`` and the omission is stated
  as a limitation -- never a made-up percentage (sections 2, 3, 61).
* **The recommendation is the critic's verdict, projected.** APPROVED/REJECTED/
  NO_TRADE is a deterministic function of the critic, so a report can never be
  more confident than the adversary that judged it. Mock or unusable data yields
  NO_TRADE, the spec's preferred "insufficient evidence" outcome (section 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .analysis import TradingAnalysis
from .backtest import BacktestResult
from .critique import CriticReport
from .enums import Confidence, Direction, ReportRecommendation, TrendState
from .event_calendar import EventCalendar
from .fundamentals import FundamentalAnalysis
from .instrument import Instrument
from .news import NewsAnalysis
from .probability import ProbabilityEstimate
from .anomaly import AnomalyAnalysis
from .breakout import BreakoutAnalysis
from .divergence import DivergenceAnalysis
from .historical_analogue import HistoricalAnalogueAnalysis
from .macro import MacroContext
from .multi_timeframe import MultiTimeframeAnalysis
from .provenance import DataQuality, Provenance
from .regime import RegimeAnalysis
from .relative_strength import RelativeStrengthAnalysis
from .risk import RiskAssessment

PIPELINE_VERSION = "deterministic-core/1.0"

_PROBABILITY_LIMITATION = (
    "No calibrated probability is surfaced: the estimate did not pass its "
    "out-of-sample reliability gate, and the spec forbids reporting an "
    "unvalidated one (sections 6, 7, 61)."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class TradingReport:
    """The final composed situation report for one instrument (spec section 27)."""

    analysis: TradingAnalysis
    risk: RiskAssessment
    critique: CriticReport
    recommendation: ReportRecommendation
    horizon: int
    provenance: Provenance
    backtest: BacktestResult | None = None
    probability: ProbabilityEstimate | None = None
    news: NewsAnalysis | None = None
    calendar: EventCalendar | None = None
    fundamentals: FundamentalAnalysis | None = None
    regime: RegimeAnalysis | None = None
    relative_strength: RelativeStrengthAnalysis | None = None
    anomaly: AnomalyAnalysis | None = None
    historical_analogue: HistoricalAnalogueAnalysis | None = None
    macro: MacroContext | None = None
    multi_timeframe: MultiTimeframeAnalysis | None = None
    divergence: DivergenceAnalysis | None = None
    breakout: BreakoutAnalysis | None = None
    limitations: tuple[str, ...] = ()
    pipeline_version: str = PIPELINE_VERSION
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def instrument(self) -> Instrument:
        return self.analysis.instrument

    @property
    def direction(self) -> Direction:
        return self.analysis.direction

    @property
    def confidence(self) -> Confidence:
        return self.analysis.confidence

    @property
    def trend(self) -> TrendState:
        return self.analysis.structure.trend

    @property
    def quality(self) -> DataQuality:
        return self.analysis.quality

    @property
    def is_actionable(self) -> bool:
        """
        A report is actionable only when every honest gate agrees: the analysis
        rests on usable, non-mock data with a real direction, the risk plan is
        actionable, and the critic APPROVED. Any single failure -> not actionable.
        """
        return (
            self.analysis.is_actionable
            and self.risk.is_actionable
            and self.critique.approved
        )

    def to_dict(self) -> dict[str, Any]:
        structure = self.analysis.structure
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.analysis.timeframe_value,
            "last_price": self.analysis.last_price,
            "recommendation": self.recommendation.value,
            "is_actionable": self.is_actionable,
            "signal": {
                "direction": self.direction.value,
                "confidence": self.confidence.value,
                "directional_score": self.analysis.directional_score,
            },
            # A calibrated probability is surfaced only when the estimate passed
            # its own out-of-sample reliability gate; otherwise it is null and the
            # reason is carried in `limitations` (spec sections 3, 6, 61).
            "probability": (
                self.probability.to_dict()
                if (self.probability is not None and self.probability.is_reliable)
                else None
            ),
            "market_regime": {
                "trend": structure.trend.value,
                "trend_strength": structure.trend_strength,
                # The deterministic trending/ranging/volatile read, surfaced
                # whenever the regime layer ran and labelled by its own
                # `is_reliable` flag so a MOCK or too-thin read can never pass
                # for a real one (spec sections 5, 8, 28). When the layer is
                # absent this is null and only the structure-derived trend above
                # is shown -- backward compatible with reports built without a
                # regime. It is situational context, never a price prediction.
                "regime": self.regime.to_dict() if self.regime else None,
            },
            "key_levels": {
                "supports": [lvl.to_dict() for lvl in structure.supports],
                "resistances": [lvl.to_dict() for lvl in structure.resistances],
            },
            "risk": self.risk.to_dict(),
            "invalidation": self.risk.invalidation,
            "horizon": {"bars": self.horizon, "timeframe": self.analysis.timeframe_value},
            "evidence": [e.to_dict() for e in self.analysis.evidence],
            "technical": self.analysis.technical.to_dict(),
            "structure": structure.to_dict(),
            "volume": self.analysis.volume.to_dict() if self.analysis.volume else None,
            "critique": self.critique.to_dict(),
            "backtest": self.backtest.to_dict() if self.backtest else None,
            # News/sentiment is surfaced whenever the layer ran, always labelled
            # by its own `is_reliable` flag so a MOCK or too-thin read can never
            # be mistaken for a trustworthy signal (spec sections 9, 28). It is
            # advisory only -- it never lifts the recommendation above the
            # critic's verdict.
            "news": self.news.to_dict() if self.news else None,
            # The event/economic calendar is surfaced whenever the layer ran,
            # labelled by its own `is_reliable` flag so a MOCK calendar can never
            # pass for a real one (spec sections 5, 15, 28). A high-impact event
            # inside the horizon is scheduled fact the critic can veto on, never a
            # claim about what price will do.
            "calendar": self.calendar.to_dict() if self.calendar else None,
            # The fundamental read is surfaced whenever the layer ran, labelled by
            # its own `is_reliable` flag so MOCK or too-thin financials can never
            # pass for a trustworthy read (spec sections 9, 28). It is advisory,
            # longer-horizon context -- a derived interpretation over sourced
            # figures that never lifts the recommendation above the critic's verdict.
            "fundamentals": self.fundamentals.to_dict() if self.fundamentals else None,
            # The relative-strength (sector/benchmark) read is surfaced whenever
            # the layer ran, labelled by its own `is_reliable` flag so a MOCK or
            # too-thin read can never pass for a real one (spec sections 2, 9, 27,
            # 28). It is the deterministic "positive/negative sector strength"
            # evidence line -- situational context that never lifts the
            # recommendation above the critic's verdict.
            "relative_strength": (
                self.relative_strength.to_dict() if self.relative_strength else None
            ),
            # The statistical-anomaly read is surfaced whenever the layer ran,
            # labelled by its own `is_reliable` flag so a MOCK or too-thin read
            # can never pass for a real one (spec sections 5, 9, 27, 28). It flags
            # an unusual last-bar return/volume/gap as a DETECTED event -- notable
            # context that never lifts the recommendation above the critic's
            # verdict, and a quiet tape is an honest "no anomaly" read.
            "anomaly": self.anomaly.to_dict() if self.anomaly else None,
            # The historical-analogue read is surfaced whenever the layer ran,
            # labelled by its own `is_reliable` flag so a MOCK or too-thin read
            # can never pass for a real one (spec sections 1, 7, 15, 27, 28). It
            # is look-ahead-safe pattern-matching over the instrument's own past
            # -- situational context that never lifts the recommendation above the
            # critic's verdict, and never a prediction.
            "historical_analogue": (
                self.historical_analogue.to_dict()
                if self.historical_analogue
                else None
            ),
            # The broad-market macro posture is surfaced whenever the layer ran,
            # labelled by its own `is_reliable` flag so a MOCK or too-thin
            # benchmark read can never pass for a real one (spec sections 2, 5,
            # 27, 28). It is the market backdrop a single-name signal sits inside
            # -- situational context that never lifts the recommendation above the
            # critic's verdict, and never a prediction.
            "macro": self.macro.to_dict() if self.macro else None,
            # The multi-timeframe confirmation is surfaced whenever the layer ran,
            # labelled by its own `is_reliable` flag so a MOCK or too-thin read on
            # either timeframe can never pass for a real one (spec sections 5, 28).
            # It says whether the higher-timeframe trend confirms or conflicts with
            # the base read -- context that never lifts the recommendation above
            # the critic's verdict, and never a prediction.
            "multi_timeframe": (
                self.multi_timeframe.to_dict() if self.multi_timeframe else None
            ),
            # Momentum divergence is surfaced whenever the layer ran, labelled by
            # its own `is_reliable` flag so a MOCK or too-thin read can never pass
            # for a real one (spec sections 5, 28). It flags a weakening trend
            # (price/oscillator divergence) -- context that never lifts the
            # recommendation above the critic's verdict, and never a prediction.
            "divergence": self.divergence.to_dict() if self.divergence else None,
            # A channel breakout is surfaced whenever the layer ran, labelled by
            # its own `is_reliable` flag so a MOCK or too-thin read can never pass
            # for a real one (spec sections 5, 28). It flags the latest close
            # pushing beyond the prior-N-bar channel -- price-action context that
            # never lifts the recommendation above the critic's verdict.
            "breakout": self.breakout.to_dict() if self.breakout else None,
            "limitations": list(self.limitations),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "model": {"pipeline": self.pipeline_version},
            "created_at": self.created_at.isoformat(),
        }
