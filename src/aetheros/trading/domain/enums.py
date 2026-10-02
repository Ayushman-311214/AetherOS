"""
Enumerations shared across the Trading Intelligence domain.

Every enum inherits from ``str`` so values serialise directly to JSON in tool
results and event payloads without a custom encoder.
"""

from __future__ import annotations

from enum import Enum


class Timeframe(str, Enum):
    """Supported candle timeframes."""

    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

    @property
    def seconds(self) -> int:
        return {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800,
        }[self.value]

    @classmethod
    def parse(cls, value: str) -> "Timeframe":
        """Resolve a user/tool string to a Timeframe, raising ValueError if unknown."""
        normalised = value.strip().lower()
        for member in cls:
            if member.value == normalised:
                return member
        raise ValueError(
            f"Unknown timeframe '{value}'. "
            f"Supported: {', '.join(m.value for m in cls)}."
        )


class Direction(str, Enum):
    """Directional bias of a signal or piece of evidence."""

    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"


class TrendState(str, Enum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    UNKNOWN = "unknown"


class MarketRegime(str, Enum):
    """
    The prevailing *character* of the market, classified deterministically from
    trend strength (ADX) and realised volatility (ATR as a fraction of price).

    This is distinct from ``Direction`` and ``TrendState``: a regime says what
    *kind* of behaviour price is exhibiting, and therefore which analytical tools
    are trustworthy right now. A trend-following read is compatible with a
    TRENDING regime, suspect in a RANGING one, and least reliable in a whipsawing
    VOLATILE one. UNKNOWN is first-class: mock, unusable or too-thin data yields
    UNKNOWN rather than a fabricated regime (CLAUDE.md sections 5, 28).
    """

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

    @property
    def is_trending(self) -> bool:
        return self in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN)

    @property
    def direction(self) -> "Direction":
        """The directional bias implied by the regime -- never a probability."""
        if self is MarketRegime.TRENDING_UP:
            return Direction.UP
        if self is MarketRegime.TRENDING_DOWN:
            return Direction.DOWN
        if self is MarketRegime.RANGING:
            return Direction.SIDEWAYS
        return Direction.UNKNOWN


class MarketPosture(str, Enum):
    """
    The broad-market risk posture, derived from a market benchmark's own regime.

    Distinct from an instrument's ``MarketRegime`` (which characterises that one
    instrument) and from relative strength (instrument-vs-benchmark): this is a
    read of *what the overall market is doing*, the context a single-name signal
    sits inside. A bullish name in a RISK_OFF tape is riskier than the same name
    in a RISK_ON one. UNKNOWN is first-class: mock, unusable or too-thin
    benchmark data yields UNKNOWN rather than a fabricated posture (CLAUDE.md
    sections 2, 5, 28).
    """

    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"

    @property
    def direction(self) -> "Direction":
        """The directional bias implied by the posture -- never a probability."""
        if self is MarketPosture.RISK_ON:
            return Direction.UP
        if self is MarketPosture.RISK_OFF:
            return Direction.DOWN
        if self is MarketPosture.NEUTRAL:
            return Direction.SIDEWAYS
        return Direction.UNKNOWN

    @classmethod
    def from_regime(cls, regime: "MarketRegime") -> "MarketPosture":
        """Map a benchmark's regime to a broad-market risk posture.

        A trending-up market is risk-on and a trending-down market is risk-off;
        a whipsawing VOLATILE tape is treated as risk-off (elevated volatility is
        a caution, not a green light); a RANGING tape is neutral; anything
        undetermined stays UNKNOWN.
        """
        return {
            MarketRegime.TRENDING_UP: cls.RISK_ON,
            MarketRegime.TRENDING_DOWN: cls.RISK_OFF,
            MarketRegime.VOLATILE: cls.RISK_OFF,
            MarketRegime.RANGING: cls.NEUTRAL,
            MarketRegime.UNKNOWN: cls.UNKNOWN,
        }[regime]


class TimeframeAlignment(str, Enum):
    """
    How a base-timeframe directional read sits against the higher timeframe.

    A signal in the direction of the higher-timeframe trend is CONFIRMED
    (stronger); one against it is a CONFLICT (a counter-trend call, riskier); a
    higher timeframe with no trend, or a base read with no side, is NEUTRAL.
    UNKNOWN is first-class: mock, unusable or too-thin data on either timeframe
    yields UNKNOWN rather than a fabricated alignment (CLAUDE.md sections 5, 28).
    """

    CONFIRMED = "confirmed"
    CONFLICT = "conflict"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    """Qualitative confidence band. Never a probability."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def from_score(cls, score: float) -> "Confidence":
        """Map a 0..1 score to a band. This is a label, not a calibrated probability."""
        if score >= 0.70:
            return cls.HIGH
        if score >= 0.40:
            return cls.MEDIUM
        return cls.LOW


class EvidenceType(str, Enum):
    """
    Category of an evidence item.

    The numerical increment populates TECHNICAL/STRUCTURE/VOLUME/VOLATILITY/
    MOMENTUM/TREND. The remaining members are declared now so the Evidence model
    and fusion layer are stable for the external/visual intelligence modules
    that follow, without a later schema change.
    """

    TECHNICAL = "technical"
    MARKET_STRUCTURE = "market_structure"
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    MARKET_CONTEXT = "market_context"
    REGIME = "regime"
    NEWS = "news"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    OPTIONS = "options"
    CATALYST = "catalyst"
    ANOMALY = "anomaly"
    HISTORICAL = "historical"
    VISUAL = "visual"
    CHART = "chart"
    MACRO = "macro"


class SourceTier(str, Enum):
    """
    Provenance tier for an observation.

    MOCK is a first-class tier so synthetic/test data is never presentable as
    real market data (spec section 53/61).
    """

    PRIMARY = "primary"
    SECONDARY = "secondary"
    UNVERIFIED = "unverified"
    DERIVED = "derived"
    MOCK = "mock"


class DataQualityStatus(str, Enum):
    OK = "ok"
    STALE = "stale"
    PARTIAL = "partial"
    MISSING = "missing"
    INVALID = "invalid"


class StructureSignalType(str, Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    FAILED_BREAKOUT = "failed_breakout"
    FAILED_BREAKDOWN = "failed_breakdown"
    RANGE = "range"
    NONE = "none"


class Assertion(str, Enum):
    """
    Epistemic status of a value in user-facing output (spec section 56).

    Distinguishes what the system measured from what it inferred.
    """

    OBSERVED = "observed"
    CALCULATED = "calculated"
    DETECTED = "detected"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class RiskBand(str, Enum):
    """
    Qualitative risk level for a trade plan. Never a probability.

    UNKNOWN is first-class: when the inputs needed to judge risk (e.g. ATR) are
    absent, the honest answer is "unknown", not a fabricated MEDIUM.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"

    @classmethod
    def from_atr_pct(cls, atr_pct: float | None) -> "RiskBand":
        """Map ATR-as-fraction-of-price to a volatility band (deterministic)."""
        if atr_pct is None:
            return cls.UNKNOWN
        if atr_pct < 0.01:
            return cls.LOW
        if atr_pct < 0.03:
            return cls.MEDIUM
        return cls.HIGH

    def escalate(self) -> "RiskBand":
        """Bump one level toward HIGH; UNKNOWN becomes MEDIUM, HIGH is capped."""
        return {
            RiskBand.UNKNOWN: RiskBand.MEDIUM,
            RiskBand.LOW: RiskBand.MEDIUM,
            RiskBand.MEDIUM: RiskBand.HIGH,
            RiskBand.HIGH: RiskBand.HIGH,
        }[self]


class CheckStatus(str, Enum):
    """
    Outcome of one critic check.

    SKIPPED is first-class: a check the current build cannot perform yet (e.g.
    probability calibration before the quant layer exists) is reported as
    skipped, never silently passed (spec sections 5, 28).
    """

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIPPED = "skipped"


class CriticVerdict(str, Enum):
    """
    The critic's go/no-go decision on a proposed signal.

    INSUFFICIENT_EVIDENCE is distinct from REJECT: REJECT means the case was
    judged and found wanting (conflicting evidence, thin R:R, no historical
    edge); INSUFFICIENT_EVIDENCE means there was not enough sound input to judge
    at all. Preferring the latter over a fabricated APPROVE is the spec's core
    honesty rule (sections 28, 61).
    """

    APPROVE = "approve"
    REJECT = "reject"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReportRecommendation(str, Enum):
    """
    The final desk-level recommendation on a composed trading report.

    A deterministic projection of the critic's verdict onto an actionability
    label -- never a probability and never a promise. NO_TRADE is the honest
    outcome when there is not enough sound evidence to judge (spec sections 28,
    61), and is deliberately distinct from REJECTED (a judged, wanting case).
    """

    APPROVED = "approved"
    REJECTED = "rejected"
    NO_TRADE = "no_trade"

    @classmethod
    def from_verdict(cls, verdict: "CriticVerdict") -> "ReportRecommendation":
        if verdict is CriticVerdict.APPROVE:
            return cls.APPROVED
        if verdict is CriticVerdict.REJECT:
            return cls.REJECTED
        return cls.NO_TRADE


class PredictionOutcomeStatus(str, Enum):
    """
    The state of a past prediction checked against what actually happened.

    Resolution is honest about time: a prediction whose horizon has not yet
    elapsed in the available data is PENDING (too early to judge, never a
    fabricated verdict), and one whose entry bar cannot even be located in the
    data -- or that rests on unusable data -- is UNRESOLVABLE. RESOLVED means the
    realised move over the stated horizon was measured; whether that counts as a
    hit is a separate question, since a non-directional call (SIDEWAYS/UNKNOWN,
    or a NO_TRADE report) has no directional bet to score (spec sections 6, 29).
    """

    PENDING = "pending"
    RESOLVED = "resolved"
    UNRESOLVABLE = "unresolvable"
