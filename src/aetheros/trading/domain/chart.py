"""
Chart value objects: the renderable projection of a candle series.

A :class:`ChartData` is what a chart *draws*: the same bars as
:class:`~aetheros.trading.domain.market_data.MarketData` projected onto plain
(time, OHLCV) points with precomputed time/price ranges, plus whatever
annotations have been placed on it. The transformation is pure -- no I/O, no
provider, no rendering -- so any consumer (a tool result, a future renderer,
the hybrid screenshot+API context) sees one stable shape with the series'
Provenance still attached (CLAUDE.md sections 9, 13).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import Timeframe
from .instrument import Instrument
from .provenance import Provenance


def _aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")


def _finite(value: float, field_name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite.")


class ChartAnnotationKind:
    """Namespace of annotation kind constants (kept as plain strings for JSON)."""

    HLINE = "hline"
    VLINE = "vline"
    TRENDLINE = "trendline"
    ZONE = "zone"
    MARKER = "marker"
    NOTE = "note"


@dataclass(frozen=True, slots=True)
class ChartAnnotation:
    """
    One structured annotation placed on a chart.

    Validation is per-kind: an hline needs a price, a vline a timestamp, a
    trendline two (time, price) points with distinct times, a zone two ordered
    prices. Anything else is rejected rather than drawn wrong.
    """

    kind: str
    label: str = ""
    price: float | None = None
    price2: float | None = None
    timestamp: datetime | None = None
    timestamp2: datetime | None = None
    note: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _aware(self.created_at, "created_at")
        if self.price is not None:
            _finite(self.price, "price")
        if self.price2 is not None:
            _finite(self.price2, "price2")

        if self.kind == ChartAnnotationKind.HLINE:
            if self.price is None:
                raise ValueError("An hline annotation requires a price.")
        elif self.kind == ChartAnnotationKind.VLINE:
            if self.timestamp is None:
                raise ValueError("A vline annotation requires a timestamp.")
            _aware(self.timestamp, "timestamp")
        elif self.kind == ChartAnnotationKind.TRENDLINE:
            if self.timestamp is None or self.timestamp2 is None:
                raise ValueError("A trendline requires two timestamps.")
            if self.price is None or self.price2 is None:
                raise ValueError("A trendline requires two prices.")
            _aware(self.timestamp, "timestamp")
            _aware(self.timestamp2, "timestamp2")
            if self.timestamp == self.timestamp2:
                raise ValueError("A trendline's two points must differ in time.")
        elif self.kind == ChartAnnotationKind.ZONE:
            if self.price is None or self.price2 is None:
                raise ValueError("A zone requires two prices.")
            if self.price2 <= self.price:
                raise ValueError("A zone's price2 must be above price.")
        elif self.kind in (ChartAnnotationKind.MARKER, ChartAnnotationKind.NOTE):
            if self.timestamp is None:
                raise ValueError(f"A {self.kind} annotation requires a timestamp.")
            _aware(self.timestamp, "timestamp")
            if self.kind == ChartAnnotationKind.MARKER and self.price is None:
                raise ValueError("A marker annotation requires a price.")
        else:
            raise ValueError(f"Unknown annotation kind '{self.kind}'.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "price": self.price,
            "price2": self.price2,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "timestamp2": self.timestamp2.isoformat() if self.timestamp2 else None,
            "note": self.note,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ChartPoint:
    """One candle projected to a plain (time, OHLCV) point."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        _aware(self.timestamp, "timestamp")
        for name in ("open", "high", "low", "close", "volume"):
            _finite(getattr(self, name), name)
        if self.volume < 0:
            raise ValueError("ChartPoint volume must be non-negative.")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("ChartPoint high must be >= open, low, and close.")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("ChartPoint low must be <= open, high, and close.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


@dataclass(frozen=True, slots=True)
class ChartData:
    """The renderable projection of a candle series with its annotations."""

    instrument: Instrument
    timeframe: Timeframe
    points: tuple[ChartPoint, ...]
    annotations: tuple[ChartAnnotation, ...] = ()
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("ChartData requires at least one point.")
        timestamps = [p.timestamp for p in self.points]
        if any(
            b <= a
            for a, b in zip(timestamps, timestamps[1:], strict=False)
        ):
            raise ValueError("ChartData points must have strictly increasing time.")

    @property
    def time_start(self) -> datetime:
        return self.points[0].timestamp

    @property
    def time_end(self) -> datetime:
        return self.points[-1].timestamp

    @property
    def price_low(self) -> float:
        return min(p.low for p in self.points)

    @property
    def price_high(self) -> float:
        return max(p.high for p in self.points)

    def to_dict(self, *, include_points: bool = False, tail: int = 20) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe.value,
            "point_count": len(self.points),
            "time_start": self.time_start.isoformat(),
            "time_end": self.time_end.isoformat(),
            "price_low": self.price_low,
            "price_high": self.price_high,
            "annotations": [a.to_dict() for a in self.annotations],
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }
        if include_points:
            payload["points"] = [p.to_dict() for p in self.points]
        else:
            payload["recent_points"] = [p.to_dict() for p in self.points[-tail:]]
        return payload


@dataclass(frozen=True, slots=True)
class ChartState:
    """
    The identity of one open chart: instrument, timeframe, visible range and
    annotations. A value object -- the service derives new states, nothing
    mutates in place.
    """

    instrument: Instrument
    timeframe: Timeframe
    visible_start: datetime
    visible_end: datetime
    annotations: tuple[ChartAnnotation, ...] = ()
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _aware(self.visible_start, "visible_start")
        _aware(self.visible_end, "visible_end")
        if self.visible_end < self.visible_start:
            raise ValueError("visible_end cannot precede visible_start.")
        _aware(self.updated_at, "updated_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe.value,
            "visible_start": self.visible_start.isoformat(),
            "visible_end": self.visible_end.isoformat(),
            "annotations": [a.to_dict() for a in self.annotations],
            "updated_at": self.updated_at.isoformat(),
        }
