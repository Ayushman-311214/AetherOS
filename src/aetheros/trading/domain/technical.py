"""
Technical-analysis value objects.

TechnicalSnapshot holds the *latest* scalar reading of each indicator plus a
little context (timeframe, provenance, how many bars fed it). Full indicator
series stay in the indicator functions; the snapshot is what evidence and the
LLM context builder consume, so it is deliberately compact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Timeframe
from .provenance import Provenance


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MACDReading:
    macd: float
    signal: float
    histogram: float

    def to_dict(self) -> dict[str, Any]:
        return {"macd": self.macd, "signal": self.signal, "histogram": self.histogram}


@dataclass(frozen=True, slots=True)
class BollingerReading:
    middle: float
    upper: float
    lower: float

    @property
    def width(self) -> float:
        if self.middle == 0:
            return 0.0
        return (self.upper - self.lower) / self.middle

    def to_dict(self) -> dict[str, Any]:
        return {
            "middle": self.middle,
            "upper": self.upper,
            "lower": self.lower,
            "width": self.width,
        }


@dataclass(frozen=True, slots=True)
class TechnicalSnapshot:
    """Latest values of the computed indicators for one timeframe."""

    timeframe: Timeframe
    last_price: float
    bars: int
    provenance: Provenance
    computed_at: datetime = field(default_factory=_utcnow)

    sma_fast: float | None = None
    sma_slow: float | None = None
    ema_fast: float | None = None
    ema_slow: float | None = None
    rsi: float | None = None
    macd: MACDReading | None = None
    atr: float | None = None
    bollinger: BollingerReading | None = None
    vwap: float | None = None
    adx: float | None = None
    volume_ma: float | None = None
    return_pct: float | None = None
    volatility: float | None = None

    # Parameters actually used, so a reading is reproducible.
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeframe": self.timeframe.value,
            "last_price": self.last_price,
            "bars": self.bars,
            "computed_at": self.computed_at.isoformat(),
            "sma_fast": self.sma_fast,
            "sma_slow": self.sma_slow,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "rsi": self.rsi,
            "macd": self.macd.to_dict() if self.macd else None,
            "atr": self.atr,
            "bollinger": self.bollinger.to_dict() if self.bollinger else None,
            "vwap": self.vwap,
            "adx": self.adx,
            "volume_ma": self.volume_ma,
            "return_pct": self.return_pct,
            "volatility": self.volatility,
            "params": self.params,
            "provenance": self.provenance.to_dict(),
        }
