"""
Technical-analysis service.

Turns a MarketData series into a compact TechnicalSnapshot by running the
deterministic indicator functions and taking the last finite value of each.
Indicators that lack enough bars are left as ``None`` rather than guessed --
an honest "not enough data" instead of a fabricated number (spec section 61).

No LLM, no I/O; given the same candles it always produces the same snapshot.
"""

from __future__ import annotations

from ...core.logging import get_logger
from .. import indicators as ind
from ..domain.enums import SourceTier, Timeframe
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..domain.technical import BollingerReading, MACDReading, TechnicalSnapshot
from ..errors import InsufficientDataError

logger = get_logger("trading.technical")

# Default indicator parameters. Exposed on the snapshot's ``params`` so a
# reading is reproducible.
DEFAULT_PARAMS: dict[str, int] = {
    "sma_fast": 20,
    "sma_slow": 50,
    "ema_fast": 12,
    "ema_slow": 26,
    "rsi": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "atr": 14,
    "bollinger": 20,
    "adx": 14,
    "volume_ma": 20,
    "volatility": 20,
}

# Below this many bars there is nothing meaningful to compute at all.
MIN_BARS = 2


class TechnicalAnalysisService:
    """Computes latest-value technical readings from a candle series."""

    def __init__(self, params: dict[str, int] | None = None) -> None:
        self._params = {**DEFAULT_PARAMS, **(params or {})}

    def compute(self, data: MarketData) -> TechnicalSnapshot:
        candles = data.candles
        if len(candles) < MIN_BARS:
            raise InsufficientDataError(
                f"Need at least {MIN_BARS} candles for technical analysis, "
                f"got {len(candles)}.",
                context={
                    "instrument": data.instrument.key,
                    "bars": len(candles),
                },
            )

        closes = data.closes()
        highs = data.highs()
        lows = data.lows()
        volumes = data.volumes()
        p = self._params

        macd_line, signal_line, hist = ind.macd(
            closes, p["macd_fast"], p["macd_slow"], p["macd_signal"]
        )
        macd_reading = None
        m, s, h = ind.last_finite(macd_line), ind.last_finite(signal_line), ind.last_finite(hist)
        if None not in (m, s, h):
            macd_reading = MACDReading(macd=m, signal=s, histogram=h)

        mid, upper, lower = ind.bollinger(closes, p["bollinger"])
        boll_reading = None
        bm, bu, bl = ind.last_finite(mid), ind.last_finite(upper), ind.last_finite(lower)
        if None not in (bm, bu, bl):
            boll_reading = BollingerReading(middle=bm, upper=bu, lower=bl)

        return_pct = None
        rets = ind.returns(closes)
        last_ret = ind.last_finite(rets)
        if last_ret is not None:
            return_pct = last_ret * 100.0

        snapshot = TechnicalSnapshot(
            timeframe=data.timeframe,
            last_price=float(closes[-1]),
            bars=len(candles),
            provenance=Provenance(
                source=data.provenance.source,
                tier=SourceTier.DERIVED if not data.provenance.is_mock else SourceTier.MOCK,
                detail="computed technical indicators",
            ),
            sma_fast=ind.last_finite(ind.sma(closes, p["sma_fast"])),
            sma_slow=ind.last_finite(ind.sma(closes, p["sma_slow"])),
            ema_fast=ind.last_finite(ind.ema(closes, p["ema_fast"])),
            ema_slow=ind.last_finite(ind.ema(closes, p["ema_slow"])),
            rsi=ind.last_finite(ind.rsi(closes, p["rsi"])),
            macd=macd_reading,
            atr=ind.last_finite(ind.atr(highs, lows, closes, p["atr"])),
            bollinger=boll_reading,
            vwap=ind.last_finite(ind.vwap(highs, lows, closes, volumes)),
            adx=ind.last_finite(ind.adx(highs, lows, closes, p["adx"])),
            volume_ma=ind.last_finite(ind.volume_ma(volumes, p["volume_ma"])),
            return_pct=return_pct,
            volatility=ind.last_finite(ind.volatility(closes, p["volatility"])),
            params=dict(self._params),
        )
        return snapshot
