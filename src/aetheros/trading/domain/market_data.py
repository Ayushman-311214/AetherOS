"""
Market-data value objects: Candle, Quote, MarketData.

MarketData is the canonical container the technical, structure and evidence
layers consume. It exposes numpy views of the OHLCV series so indicator maths
stays vectorised and deterministic, and it carries its own Provenance and
DataQuality so no downstream stage has to guess where the numbers came from.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import numpy as np

from .enums import Timeframe
from .instrument import Instrument
from .provenance import DataQuality, Provenance


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Candle:
    """A single OHLCV bar. Timestamp is the bar's open time (UTC)."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Candle timestamp must be timezone-aware.")
        object.__setattr__(self, "timestamp", self.timestamp.astimezone(UTC))

        values = (self.open, self.high, self.low, self.close, self.volume)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("Candle OHLCV values must be finite.")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("Candle high must be >= open, low, and close.")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("Candle low must be <= open, high, and close.")
        if self.volume < 0:
            raise ValueError("Candle volume must be non-negative.")

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
class Quote:
    """A latest-price snapshot for an instrument."""

    instrument: Instrument
    price: float
    timestamp: datetime
    provenance: Provenance
    bid: float | None = None
    ask: float | None = None
    volume: float | None = None
    change_pct: float | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.price) or self.price <= 0:
            raise ValueError("Quote price must be a finite positive number.")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("Quote timestamp must be timezone-aware.")
        for value, name in ((self.bid, "bid"), (self.ask, "ask")):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"Quote {name} must be a finite positive number.")
        if self.volume is not None and (
            not math.isfinite(self.volume) or self.volume < 0
        ):
            raise ValueError("Quote volume must be finite and non-negative.")
        if self.change_pct is not None and not math.isfinite(self.change_pct):
            raise ValueError("Quote change_pct must be finite.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument.to_dict(),
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "change_pct": self.change_pct,
            "provenance": self.provenance.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class MarketData:
    """A timeframed OHLCV series with provenance and quality."""

    instrument: Instrument
    timeframe: Timeframe
    candles: tuple[Candle, ...]
    provenance: Provenance
    quality: DataQuality
    retrieved_at: datetime = field(default_factory=_utcnow)

    # ---- vectorised views (computed on demand, not stored) ----

    def closes(self) -> np.ndarray:
        return np.array([c.close for c in self.candles], dtype=float)

    def opens(self) -> np.ndarray:
        return np.array([c.open for c in self.candles], dtype=float)

    def highs(self) -> np.ndarray:
        return np.array([c.high for c in self.candles], dtype=float)

    def lows(self) -> np.ndarray:
        return np.array([c.low for c in self.candles], dtype=float)

    def volumes(self) -> np.ndarray:
        return np.array([c.volume for c in self.candles], dtype=float)

    @property
    def count(self) -> int:
        return len(self.candles)

    @property
    def last_price(self) -> float | None:
        return self.candles[-1].close if self.candles else None

    @property
    def last_timestamp(self) -> datetime | None:
        return self.candles[-1].timestamp if self.candles else None

    def window(self, start: int, end: int | None = None) -> MarketData:
        """
        A sub-series ``[start, end)`` carrying this series' provenance and quality.

        Half-open, like every other window in the trading core, and bounds-checked:
        a slice that runs off the end of the series is a caller bug and fails
        loudly here rather than quietly returning a shorter series to a
        backtest. An empty result is allowed -- "no bars in this window" is a
        real answer the callers already handle -- but an out-of-range one is not.

        This is the slicing primitive the backtester and the walk-forward
        splitter both use, so the past-only guarantee is defined in exactly one
        place.
        """
        stop = len(self.candles) if end is None else end
        if start < 0 or stop < start or stop > len(self.candles):
            raise ValueError(
                f"A window [{start}, {stop}) does not fit a series of "
                f"{len(self.candles)} bars."
            )
        return MarketData(
            instrument=self.instrument,
            timeframe=self.timeframe,
            candles=self.candles[start:stop],
            provenance=self.provenance,
            quality=self.quality,
            retrieved_at=self.retrieved_at,
        )

    def to_dict(self, *, include_candles: bool = False, tail: int = 20) -> dict[str, Any]:
        """
        Serialise for a tool result.

        By default the full candle series is *not* included -- returning
        thousands of bars to the LLM is exactly the anti-pattern the spec warns
        against. Only a small tail is attached, plus summary stats. Pass
        ``include_candles=True`` when the raw bars are genuinely the product.
        """
        payload: dict[str, Any] = {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe.value,
            "count": self.count,
            "last_price": self.last_price,
            "last_timestamp": (
                self.last_timestamp.isoformat() if self.last_timestamp else None
            ),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
        }
        if include_candles:
            payload["candles"] = [c.to_dict() for c in self.candles]
        elif self.candles:
            payload["recent_candles"] = [c.to_dict() for c in self.candles[-tail:]]
        return payload
