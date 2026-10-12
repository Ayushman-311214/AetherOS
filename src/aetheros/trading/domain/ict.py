"""
ICT (Inner Circle Trader) value objects.

Where :mod:`aetheros.trading.domain.smc` describes *where* the market left a
footprint, these describe *when* it did. ICT is a time-based framework: a kill
zone, a Judas swing, a Power-of-Three session and a session model are all
defined by the session of the trading day a move happened in, so every object
here is anchored to explicit, timezone-aware timestamps rather than to bar
indices alone.

Three honesty rules run through every object here (CLAUDE.md sections 5, 28):

- A detection is never asserted without the reason it was derived from -- each
  carries ``evidence`` (the deterministic facts that triggered it) and a
  ``confidence`` band, which is a *label*, never a probability.
- Absence is first-class. A session with no predecessor, a kill zone with no
  bars in it, or a day with too little history to read a bias is reported as
  undefined/empty rather than forced into a pattern (``UNDEFINED``,
  ``Direction.UNKNOWN``).
- Nothing here is a prediction or a trade decision. ICT detects and describes;
  the strategy/signal/decision layers (Phases 7+) are what interpret it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .enums import (
    AMDPhase,
    Confidence,
    Direction,
    ICTConcept,
    KillZoneName,
    LiquidityPoolKind,
    SessionModelKind,
    SessionName,
    TrendState,
)
from .provenance import Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _require_finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite.")


# ----------------------------------------------------------------------
# Session / time definitions
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TradingSession:
    """
    A recurring daily session window, defined in an exchange-local timezone.

    ``start`` and ``end`` are wall-clock times in ``timezone`` (an IANA name),
    so daylight-saving transitions are handled by ``zoneinfo`` rather than by a
    fixed UTC offset. A window whose ``end`` is not after its ``start`` wraps
    midnight (the Asian session does), which membership and window building
    both account for.

    Membership is evaluated in the session's **local wall clock**: a timestamp
    is converted to ``timezone`` and compared against the window, which is what
    makes the same UTC instant fall in different sessions either side of a DST
    change.
    """

    name: SessionName
    start: time
    end: time
    timezone: str
    label: str = ""

    def __post_init__(self) -> None:
        if not self.timezone:
            raise ValueError("A session must name its timezone.")
        if self.start == self.end:
            raise ValueError("A session window must have non-zero length.")

    @property
    def wraps_midnight(self) -> bool:
        return self.end <= self.start

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def contains(self, timestamp: datetime) -> bool:
        """Whether ``timestamp`` falls inside this session, in local wall clock."""
        local = timestamp.astimezone(self.tzinfo).time()
        if self.wraps_midnight:
            return local >= self.start or local < self.end
        return self.start <= local < self.end

    def window_on(self, day: date) -> tuple[datetime, datetime]:
        """The concrete ``(open, close)`` datetimes of this session on ``day``."""
        start = datetime.combine(day, self.start, tzinfo=self.tzinfo)
        end_day = day + timedelta(days=1) if self.wraps_midnight else day
        end = datetime.combine(end_day, self.end, tzinfo=self.tzinfo)
        return start, end

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "label": self.label,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "timezone": self.timezone,
            "wraps_midnight": self.wraps_midnight,
        }


@dataclass(frozen=True, slots=True)
class KillZone:
    """
    A named kill zone: a narrow, high-activity sub-window of a session.

    ``session`` records which session the zone belongs to, so a detection can
    always be attributed to the session that produced it.
    """

    name: KillZoneName
    session: SessionName
    start: time
    end: time
    timezone: str
    label: str = ""

    def __post_init__(self) -> None:
        if not self.timezone:
            raise ValueError("A kill zone must name its timezone.")
        if self.start == self.end:
            raise ValueError("A kill zone window must have non-zero length.")

    @property
    def wraps_midnight(self) -> bool:
        return self.end <= self.start

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def contains(self, timestamp: datetime) -> bool:
        """Whether ``timestamp`` falls inside this kill zone, in local wall clock."""
        local = timestamp.astimezone(self.tzinfo).time()
        if self.wraps_midnight:
            return local >= self.start or local < self.end
        return self.start <= local < self.end

    def window_on(self, day: date) -> tuple[datetime, datetime]:
        """The concrete ``(open, close)`` datetimes of this zone on ``day``."""
        start = datetime.combine(day, self.start, tzinfo=self.tzinfo)
        end_day = day + timedelta(days=1) if self.wraps_midnight else day
        end = datetime.combine(end_day, self.end, tzinfo=self.tzinfo)
        return start, end

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "session": self.session.value,
            "label": self.label,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "timezone": self.timezone,
        }


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """
    One session as it actually occurred in the data.

    This is the measured counterpart of :class:`TradingSession`: rather than the
    definition of when a session runs, it is the bars that fell inside it --
    their open/close and the extremes price reached -- plus the bar indices so a
    caller can trace any detection back to the candles.
    """

    session: SessionName
    start_at: datetime
    end_at: datetime
    open: float
    high: float
    low: float
    close: float
    candle_count: int
    first_index: int
    last_index: int

    def __post_init__(self) -> None:
        if self.end_at <= self.start_at:
            raise ValueError("A session window must end after it starts.")
        for label, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            _require_finite(value, f"Session {label}")
        if self.high < self.low:
            raise ValueError("A session high cannot be below its low.")
        if not (self.low <= self.open <= self.high):
            raise ValueError("A session open must lie within its range.")
        if not (self.low <= self.close <= self.high):
            raise ValueError("A session close must lie within its range.")
        if self.candle_count < 1:
            raise ValueError("A session window must contain at least one bar.")
        if self.last_index < self.first_index:
            raise ValueError("A session window cannot end before it begins.")

    @property
    def range(self) -> float:
        return self.high - self.low

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session.value,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "range": self.range,
            "candle_count": self.candle_count,
            "first_index": self.first_index,
            "last_index": self.last_index,
        }


# ----------------------------------------------------------------------
# Detections
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DailyBias:
    """
    The directional bias for the trading day, read from the previous day.

    ``prior_day_*`` are the completed day's levels and ``price_ratio`` the
    current price's position within that day's range (0 at its low, 1 at its
    high, deliberately unclamped). ``position`` is the premium/discount label of
    that ratio. UNKNOWN is first-class: without two completed days there is no
    bias to read, and none is invented.
    """

    direction: Direction
    prior_day_date: date
    prior_day_high: float
    prior_day_low: float
    prior_day_close: float
    last_price: float
    price_ratio: float
    position: str  # "premium" | "discount" | "equilibrium"
    timeframe: str
    trend: TrendState = TrendState.UNKNOWN
    confidence: Confidence = Confidence.LOW
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("high", self.prior_day_high),
            ("low", self.prior_day_low),
            ("close", self.prior_day_close),
            ("last price", self.last_price),
            ("price ratio", self.price_ratio),
        ):
            _require_finite(value, f"Prior-day {label}")
        if self.prior_day_high <= self.prior_day_low:
            raise ValueError("A prior-day high must be above its low.")
        if self.position not in ("premium", "discount", "equilibrium"):
            raise ValueError(f"Unknown range position '{self.position}'.")

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.DAILY_BIAS

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "direction": self.direction.value,
            "prior_day_date": self.prior_day_date.isoformat(),
            "prior_day_high": self.prior_day_high,
            "prior_day_low": self.prior_day_low,
            "prior_day_close": self.prior_day_close,
            "last_price": self.last_price,
            "price_ratio": self.price_ratio,
            "position": self.position,
            "timeframe": self.timeframe,
            "trend": self.trend.value,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class MarketStructureShift:
    """
    A change of character **confirmed by displacement**.

    A break against the prevailing structure is only a market structure shift if
    the move that produced it was displaced -- price left with intent, rather
    than drifting through the level. Displacement is *measured* here, never
    asserted: ``displacement`` is the breaking candle's body as a multiple of
    average true range, and ``left_fair_value_gap`` records whether the leg left
    a three-candle imbalance behind it. Either is sufficient.
    """

    direction: Direction
    index: int
    timestamp: datetime
    timeframe: str
    broken_level: float
    broken_index: int
    break_price: float
    prior_trend: TrendState
    displacement: float
    left_fair_value_gap: bool
    session: SessionName | None = None
    confidence: Confidence = Confidence.MEDIUM
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.broken_level <= 0 or self.break_price <= 0:
            raise ValueError("Market structure shift prices must be positive.")
        for label, value in (
            ("broken level", self.broken_level),
            ("break price", self.break_price),
            ("displacement", self.displacement),
        ):
            _require_finite(value, f"Market structure shift {label}")
        if self.displacement < 0:
            raise ValueError("Displacement cannot be negative.")
        if self.broken_index >= self.index:
            raise ValueError("A shift can only reference an earlier swing point.")

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.MARKET_STRUCTURE_SHIFT

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "direction": self.direction.value,
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "broken_level": self.broken_level,
            "broken_index": self.broken_index,
            "break_price": self.break_price,
            "prior_trend": self.prior_trend.value,
            "displacement": self.displacement,
            "left_fair_value_gap": self.left_fair_value_gap,
            "session": self.session.value if self.session else None,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class KillZoneWindow:
    """
    A kill zone as it actually occurred, with what price did inside it.

    ``range_share`` is the zone's range as a fraction of the whole session's
    range, so "did the move originate here?" is a measurement rather than an
    impression. ``swept_level`` records the prior session extreme the zone took
    out, when it took one.
    """

    name: KillZoneName
    session: SessionName
    start_at: datetime
    end_at: datetime
    open: float
    high: float
    low: float
    close: float
    candle_count: int
    range_share: float
    timeframe: str
    first_index: int
    last_index: int
    swept_level: float | None = None
    swept_direction: Direction | None = None
    confidence: Confidence = Confidence.MEDIUM
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.end_at <= self.start_at:
            raise ValueError("A kill zone window must end after it starts.")
        for label, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
            ("range share", self.range_share),
        ):
            _require_finite(value, f"Kill zone {label}")
        if self.high < self.low:
            raise ValueError("A kill zone high cannot be below its low.")
        if not 0.0 <= self.range_share <= 1.0:
            raise ValueError("A kill zone range share must lie within 0 and 1.")
        if self.candle_count < 1:
            raise ValueError("A kill zone window must contain at least one bar.")
        if self.swept_level is not None:
            _require_finite(self.swept_level, "Swept level")
            if self.swept_level <= 0:
                raise ValueError("A swept level must be positive.")

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.KILL_ZONE

    @property
    def range(self) -> float:
        return self.high - self.low

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "name": self.name.value,
            "session": self.session.value,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "range": self.range,
            "range_share": self.range_share,
            "candle_count": self.candle_count,
            "first_index": self.first_index,
            "last_index": self.last_index,
            "swept_level": self.swept_level,
            "swept_direction": (
                self.swept_direction.value if self.swept_direction else None
            ),
            "timeframe": self.timeframe,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class OTEZone:
    """
    The optimal trade entry band: a retracement window inside an impulse leg.

    ``band_top``/``band_bottom`` bound the entry zone, computed from the leg's
    range (``leg_high`` - ``leg_low``) and the configured Fibonacci ratios --
    ``low_ratio`` nearer the origin of the leg, ``high_ratio`` deeper into it.
    ``retracement_ratio`` is how deep price actually came back (0 at the leg's
    terminus, 1 at its origin), which is what says whether the band was reached.
    """

    direction: Direction
    leg_high: float
    leg_low: float
    band_top: float
    band_bottom: float
    low_ratio: float
    high_ratio: float
    retracement_ratio: float
    in_zone: bool
    index: int
    timestamp: datetime
    timeframe: str
    confidence: Confidence = Confidence.MEDIUM
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("leg high", self.leg_high),
            ("leg low", self.leg_low),
            ("band top", self.band_top),
            ("band bottom", self.band_bottom),
            ("retracement ratio", self.retracement_ratio),
        ):
            _require_finite(value, f"OTE {label}")
        if self.leg_high <= self.leg_low:
            raise ValueError("An OTE leg must have a high above its low.")
        if self.band_top <= self.band_bottom:
            raise ValueError("An OTE band top must be above its bottom.")
        if not 0.0 < self.low_ratio < self.high_ratio < 1.0:
            raise ValueError(
                "OTE ratios must satisfy 0 < low_ratio < high_ratio < 1."
            )

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.OTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "direction": self.direction.value,
            "leg_high": self.leg_high,
            "leg_low": self.leg_low,
            "band_top": self.band_top,
            "band_bottom": self.band_bottom,
            "low_ratio": self.low_ratio,
            "high_ratio": self.high_ratio,
            "retracement_ratio": self.retracement_ratio,
            "in_zone": self.in_zone,
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class LiquidityPool:
    """
    Resting liquidity at a price level.

    ``direction`` is the side the pool serves: UP for liquidity resting *above*
    a high (buy-side -- the stops of shorts), DOWN for liquidity resting *below*
    a low (sell-side). ``taken`` records that price has since traded through the
    level, which is a measurement, not a forecast.
    """

    kind: LiquidityPoolKind
    direction: Direction
    level: float
    index: int
    timestamp: datetime
    timeframe: str
    taken: bool = False
    taken_index: int | None = None
    session: SessionName | None = None
    confidence: Confidence = Confidence.MEDIUM
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.level <= 0:
            raise ValueError("A liquidity pool level must be positive.")
        _require_finite(self.level, "Liquidity pool level")
        if self.taken and self.taken_index is None:
            raise ValueError("A taken pool must record the bar that took it.")
        if self.taken_index is not None and self.taken_index < self.index:
            raise ValueError("A pool cannot be taken before it forms.")

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.LIQUIDITY_POOL

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "kind": self.kind.value,
            "direction": self.direction.value,
            "level": self.level,
            "index": self.index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "taken": self.taken,
            "taken_index": self.taken_index,
            "session": self.session.value if self.session else None,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class JudasSwing:
    """
    The false opening move: liquidity taken one way, then reversed.

    ``swept_level`` is the prior session extreme the opening window took out and
    ``sweep_extreme`` the wick that took it. ``direction`` is the direction of
    the **reversal**, which is what the pattern is named for -- the opening move
    is the manipulation, and the session's close back through its own open is
    the confirmation.
    """

    session: SessionName
    direction: Direction
    swept_level: float
    sweep_extreme: float
    sweep_index: int
    session_open: float
    reversal_price: float
    reversal_index: int
    timestamp: datetime
    timeframe: str
    confidence: Confidence = Confidence.MEDIUM
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
            ("swept level", self.swept_level),
            ("sweep extreme", self.sweep_extreme),
            ("session open", self.session_open),
            ("reversal price", self.reversal_price),
        ):
            _require_finite(value, f"Judas swing {label}")
        if self.swept_level <= 0:
            raise ValueError("A Judas swing swept level must be positive.")
        if self.sweep_index < 0:
            raise ValueError("A Judas swing must record the bar that swept.")
        if self.reversal_index < self.sweep_index:
            raise ValueError("A Judas swing cannot reverse before it sweeps.")

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.JUDAS_SWING

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "session": self.session.value,
            "direction": self.direction.value,
            "swept_level": self.swept_level,
            "sweep_extreme": self.sweep_extreme,
            "sweep_index": self.sweep_index,
            "session_open": self.session_open,
            "reversal_price": self.reversal_price,
            "reversal_index": self.reversal_index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class AMDPhaseWindow:
    """One measured third of a session, as used by the Power of Three read."""

    phase: AMDPhase
    start_at: datetime
    end_at: datetime
    open: float
    high: float
    low: float
    close: float
    candle_count: int
    range_share: float

    def __post_init__(self) -> None:
        if self.end_at <= self.start_at:
            raise ValueError("An AMD phase must end after it starts.")
        for label, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
            ("range share", self.range_share),
        ):
            _require_finite(value, f"AMD phase {label}")
        if self.high < self.low:
            raise ValueError("An AMD phase high cannot be below its low.")
        if not 0.0 <= self.range_share <= 1.0:
            raise ValueError("An AMD phase range share must lie within 0 and 1.")
        if self.candle_count < 1:
            raise ValueError("An AMD phase must contain at least one bar.")

    @property
    def range(self) -> float:
        return self.high - self.low

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase.value,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "range": self.range,
            "range_share": self.range_share,
            "candle_count": self.candle_count,
        }


@dataclass(frozen=True, slots=True)
class PowerOfThree:
    """
    A session decomposed into accumulation, manipulation and distribution.

    ``phases`` holds exactly the three measured thirds in order. ``direction`` is
    the session's realised direction -- the side distribution ultimately took --
    and ``manipulation_side`` the side the false move went, which is the
    opposite of ``direction`` in a textbook Power of Three.
    """

    session: SessionName
    start_at: datetime
    end_at: datetime
    direction: Direction
    manipulation_side: Direction
    phases: tuple[AMDPhaseWindow, ...]
    session_open: float
    session_close: float
    timeframe: str
    confidence: Confidence = Confidence.MEDIUM
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_finite(self.session_open, "Session open")
        _require_finite(self.session_close, "Session close")
        if self.end_at <= self.start_at:
            raise ValueError("A Power of Three window must end after it starts.")
        expected = (
            AMDPhase.ACCUMULATION,
            AMDPhase.MANIPULATION,
            AMDPhase.DISTRIBUTION,
        )
        if tuple(phase.phase for phase in self.phases) != expected:
            raise ValueError(
                "A Power of Three must hold exactly the accumulation, "
                "manipulation and distribution phases, in that order."
            )

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.POWER_OF_THREE

    @property
    def accumulation(self) -> AMDPhaseWindow:
        return self.phases[0]

    @property
    def manipulation(self) -> AMDPhaseWindow:
        return self.phases[1]

    @property
    def distribution(self) -> AMDPhaseWindow:
        return self.phases[2]

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "session": self.session.value,
            "start_at": self.start_at.isoformat(),
            "end_at": self.end_at.isoformat(),
            "direction": self.direction.value,
            "manipulation_side": self.manipulation_side.value,
            "phases": [phase.to_dict() for phase in self.phases],
            "session_open": self.session_open,
            "session_close": self.session_close,
            "timeframe": self.timeframe,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class SessionModel:
    """
    How one session behaved relative to the session before it.

    ``kind`` is the pattern label; ``UNDEFINED`` is first-class and means there
    was no predecessor to compare against, or too little data to characterise
    the relationship -- never a forced pattern. ``level_taken`` records the
    predecessor's extreme this session reached, when it reached one.
    """

    session: SessionName
    previous_session: SessionName | None
    kind: SessionModelKind
    direction: Direction
    level_taken: float | None
    timestamp: datetime
    timeframe: str
    confidence: Confidence = Confidence.LOW
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.level_taken is not None:
            _require_finite(self.level_taken, "Level taken")
            if self.level_taken <= 0:
                raise ValueError("A taken level must be positive.")
        if self.kind is not SessionModelKind.UNDEFINED and self.previous_session is None:
            raise ValueError("A defined session model must name the session it follows.")

    @property
    def concept(self) -> ICTConcept:
        return ICTConcept.SESSION_MODEL

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept.value,
            "session": self.session.value,
            "previous_session": (
                self.previous_session.value if self.previous_session else None
            ),
            "kind": self.kind.value,
            "direction": self.direction.value,
            "level_taken": self.level_taken,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "confidence": self.confidence.value,
            "evidence": list(self.evidence),
        }


# ----------------------------------------------------------------------
# Aggregate
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ICTAnalysis:
    """The complete deterministic ICT read for one instrument/timeframe."""

    instrument_key: str
    timeframe: str
    last_price: float
    exchange_timezone: str
    sessions: tuple[SessionWindow, ...] = ()
    daily_bias: DailyBias | None = None
    market_structure_shifts: tuple[MarketStructureShift, ...] = ()
    kill_zones: tuple[KillZoneWindow, ...] = ()
    ote: OTEZone | None = None
    liquidity_pools: tuple[LiquidityPool, ...] = ()
    judas_swings: tuple[JudasSwing, ...] = ()
    power_of_three: tuple[PowerOfThree, ...] = ()
    session_models: tuple[SessionModel, ...] = ()
    provenance: Provenance | None = None
    limitations: tuple[str, ...] = ()
    computed_at: datetime = field(default_factory=_utcnow)

    @property
    def resting_pools(self) -> tuple[LiquidityPool, ...]:
        """Pools price has not yet traded through -- a derived view, not a re-detect."""
        return tuple(pool for pool in self.liquidity_pools if not pool.taken)

    @property
    def taken_pools(self) -> tuple[LiquidityPool, ...]:
        return tuple(pool for pool in self.liquidity_pools if pool.taken)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "last_price": self.last_price,
            "exchange_timezone": self.exchange_timezone,
            "sessions": [window.to_dict() for window in self.sessions],
            "daily_bias": self.daily_bias.to_dict() if self.daily_bias else None,
            "market_structure_shifts": [
                shift.to_dict() for shift in self.market_structure_shifts
            ],
            "kill_zones": [zone.to_dict() for zone in self.kill_zones],
            "ote": self.ote.to_dict() if self.ote else None,
            "liquidity_pools": [pool.to_dict() for pool in self.liquidity_pools],
            "judas_swings": [swing.to_dict() for swing in self.judas_swings],
            "power_of_three": [amd.to_dict() for amd in self.power_of_three],
            "session_models": [model.to_dict() for model in self.session_models],
            # Derived views, so a caller does not have to re-filter.
            "resting_pools": [pool.to_dict() for pool in self.resting_pools],
            "taken_pools": [pool.to_dict() for pool in self.taken_pools],
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "limitations": list(self.limitations),
            "computed_at": self.computed_at.isoformat(),
        }
