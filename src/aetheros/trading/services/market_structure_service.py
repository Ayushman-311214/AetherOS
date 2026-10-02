"""
Market-structure service.

Derives *what the price action is doing* from a candle series: swing pivots,
support/resistance levels clustered from those pivots, the higher-high /
higher-low pattern, an overall trend read, and structural signals such as a
breakout above the most recent resistance. Everything is deterministic and
every detection carries the evidence (reference price, touch count) it was
derived from -- the service never asserts a pattern without a reason
(CLAUDE.md sections 5, 8).
"""

from __future__ import annotations

import numpy as np

from ...core.logging import get_logger
from ..domain.enums import Confidence, Direction, StructureSignalType, TrendState
from ..domain.market_data import MarketData
from ..domain.structure import Level, MarketStructure, StructureSignal, SwingPoint
from ..errors import InsufficientDataError

logger = get_logger("trading.structure")


class MarketStructureService:
    """Swing/level/trend detection over a candle series."""

    def __init__(
        self,
        *,
        pivot_window: int = 3,
        level_tolerance_pct: float = 0.5,
        min_bars: int = 10,
    ) -> None:
        if pivot_window < 1:
            raise ValueError("pivot_window must be >= 1.")
        self._k = pivot_window
        self._tol = level_tolerance_pct / 100.0
        self._min_bars = min_bars

    def analyze(self, data: MarketData) -> MarketStructure:
        candles = data.candles
        if len(candles) < self._min_bars:
            raise InsufficientDataError(
                f"Need at least {self._min_bars} candles for structure "
                f"analysis, got {len(candles)}.",
                context={"instrument": data.instrument.key, "bars": len(candles)},
            )

        highs = data.highs()
        lows = data.lows()
        closes = data.closes()

        swings = self._find_swings(data)
        swing_highs = [s for s in swings if s.kind == "high"]
        swing_lows = [s for s in swings if s.kind == "low"]

        last_price = float(closes[-1])
        resistances = self._cluster_levels(
            [s.price for s in swing_highs], kind="resistance", last_price=last_price
        )
        supports = self._cluster_levels(
            [s.price for s in swing_lows], kind="support", last_price=last_price
        )

        hh, hl, lh, ll = self._pattern(swing_highs, swing_lows)
        trend, strength = self._trend(closes, hh, hl, lh, ll)
        signals = self._signals(
            last_price=last_price,
            supports=supports,
            resistances=resistances,
            highs=highs,
            lows=lows,
        )

        return MarketStructure(
            trend=trend,
            trend_strength=strength,
            swings=tuple(swings),
            supports=tuple(supports),
            resistances=tuple(resistances),
            signals=tuple(signals),
            higher_highs=hh,
            higher_lows=hl,
            lower_highs=lh,
            lower_lows=ll,
        )

    # ------------------------------------------------------------------

    def _find_swings(self, data: MarketData) -> list[SwingPoint]:
        highs = data.highs()
        lows = data.lows()
        candles = data.candles
        k = self._k
        n = len(candles)
        swings: list[SwingPoint] = []
        for i in range(k, n - k):
            window_high = highs[i - k : i + k + 1]
            window_low = lows[i - k : i + k + 1]
            if highs[i] == window_high.max() and highs[i] > highs[i - 1]:
                swings.append(
                    SwingPoint(
                        index=i,
                        timestamp=candles[i].timestamp,
                        price=float(highs[i]),
                        kind="high",
                    )
                )
            if lows[i] == window_low.min() and lows[i] < lows[i - 1]:
                swings.append(
                    SwingPoint(
                        index=i,
                        timestamp=candles[i].timestamp,
                        price=float(lows[i]),
                        kind="low",
                    )
                )
        swings.sort(key=lambda s: s.index)
        return swings

    def _cluster_levels(
        self, prices: list[float], *, kind: str, last_price: float
    ) -> list[Level]:
        if not prices:
            return []
        ordered = sorted(prices)
        clusters: list[list[float]] = [[ordered[0]]]
        for price in ordered[1:]:
            anchor = clusters[-1][0]
            if anchor > 0 and abs(price - anchor) / anchor <= self._tol:
                clusters[-1].append(price)
            else:
                clusters.append([price])

        levels: list[Level] = []
        for cluster in clusters:
            touches = len(cluster)
            level_price = float(np.mean(cluster))
            # Confidence rises with touch count; a single touch is LOW.
            score = min(1.0, 0.3 + 0.2 * (touches - 1))
            levels.append(
                Level(
                    price=level_price,
                    kind=kind,
                    touches=touches,
                    confidence=Confidence.from_score(score),
                )
            )
        # Keep the levels most relevant to the current price (nearest first).
        levels.sort(key=lambda lvl: abs(lvl.price - last_price))
        return levels[:5]

    @staticmethod
    def _pattern(
        swing_highs: list[SwingPoint], swing_lows: list[SwingPoint]
    ) -> tuple[bool, bool, bool, bool]:
        def last_two(points: list[SwingPoint]) -> tuple[float, float] | None:
            if len(points) < 2:
                return None
            return points[-2].price, points[-1].price

        hh = hl = lh = ll = False
        highs = last_two(swing_highs)
        if highs is not None:
            hh = highs[1] > highs[0]
            lh = highs[1] < highs[0]
        lows = last_two(swing_lows)
        if lows is not None:
            hl = lows[1] > lows[0]
            ll = lows[1] < lows[0]
        return hh, hl, lh, ll

    @staticmethod
    def _trend(
        closes: np.ndarray, hh: bool, hl: bool, lh: bool, ll: bool
    ) -> tuple[TrendState, float]:
        # Structural vote from swing pattern.
        up_votes = int(hh) + int(hl)
        down_votes = int(lh) + int(ll)

        # Slope confirmation from a short vs long mean of closes.
        n = closes.size
        short = closes[-min(n, 10):].mean()
        long = closes[-min(n, 30):].mean()
        slope_up = short > long
        slope_down = short < long

        score_up = up_votes + (1 if slope_up else 0)
        score_down = down_votes + (1 if slope_down else 0)

        total = max(1, score_up + score_down)
        if score_up > score_down:
            return TrendState.UPTREND, round(score_up / 3.0, 3)
        if score_down > score_up:
            return TrendState.DOWNTREND, round(score_down / 3.0, 3)
        return TrendState.RANGE, round(abs(score_up - score_down) / total, 3)

    def _signals(
        self,
        *,
        last_price: float,
        supports: list[Level],
        resistances: list[Level],
        highs: np.ndarray,
        lows: np.ndarray,
    ) -> list[StructureSignal]:
        signals: list[StructureSignal] = []
        # Nearest resistance above / support below by original (unsorted) price.
        res_above = min(
            (lvl for lvl in resistances if lvl.price >= last_price),
            key=lambda lvl: lvl.price,
            default=None,
        )
        sup_below = max(
            (lvl for lvl in supports if lvl.price <= last_price),
            key=lambda lvl: lvl.price,
            default=None,
        )
        # Breakout: last price cleared a former resistance (now below price).
        res_below = [lvl for lvl in resistances if lvl.price < last_price]
        if res_below:
            nearest = max(res_below, key=lambda lvl: lvl.price)
            if (last_price - nearest.price) / nearest.price <= self._tol * 2:
                signals.append(
                    StructureSignal(
                        type=StructureSignalType.BREAKOUT,
                        direction=Direction.UP,
                        confidence=nearest.confidence,
                        reference_price=nearest.price,
                        observation=(
                            f"Price {last_price:.2f} is just above prior "
                            f"resistance {nearest.price:.2f}."
                        ),
                    )
                )
        sup_above = [lvl for lvl in supports if lvl.price > last_price]
        if sup_above:
            nearest = min(sup_above, key=lambda lvl: lvl.price)
            if (nearest.price - last_price) / nearest.price <= self._tol * 2:
                signals.append(
                    StructureSignal(
                        type=StructureSignalType.BREAKDOWN,
                        direction=Direction.DOWN,
                        confidence=nearest.confidence,
                        reference_price=nearest.price,
                        observation=(
                            f"Price {last_price:.2f} is just below prior "
                            f"support {nearest.price:.2f}."
                        ),
                    )
                )
        if not signals and res_above is not None and sup_below is not None:
            signals.append(
                StructureSignal(
                    type=StructureSignalType.RANGE,
                    direction=Direction.SIDEWAYS,
                    confidence=Confidence.LOW,
                    reference_price=last_price,
                    observation=(
                        f"Price {last_price:.2f} is between support "
                        f"{sup_below.price:.2f} and resistance "
                        f"{res_above.price:.2f}."
                    ),
                )
            )
        return signals
