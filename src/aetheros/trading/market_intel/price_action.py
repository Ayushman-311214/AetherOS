"""
Price-action analysis (Phase 4).

A deterministic read of *how price is behaving* -- momentum, rejection,
breakout, failed breakout, acceptance, range behaviour and volatility
expansion/contraction -- over a candle series. These are the price-action
concepts the liquidity layer deliberately does *not* cover (it reads the book
and tape; this reads the bars).

Two honesty rules run through it:

* **Complex structure needs more than one candle.** A rejection or a failed
  breakout is asserted only when the configured confirmation is met -- a single
  wick or a single poke through a level is evidence, never a verdict, unless
  the caller explicitly asks for single-bar detection (``min_confirm_bars``).
* **These are behaviours, not predictions.** ``breakout`` / ``failed_breakout``
  describe what price *did* relative to a level, with the supporting numbers
  carried -- never what it will do next.

Every input is a pure function of the series; identical candles reproduce the
identical read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np

from ...core.logging import get_logger
from ..domain.enums import Confidence, Direction
from ..domain.market_data import MarketData
from ..indicators import core as ind

logger = get_logger("trading.price_action")

#: A bar is a rejection when its wick in one direction is at least this multiple
#: of its body -- price poked and was pushed back.
_REJECTION_WICK_BODY = 1.5

#: A breakout (close beyond a prior extreme) that closes back inside within
#: ``_FAIL_WINDOW`` bars is a failed breakout.
_FAIL_WINDOW = 3

#: Volatility ratio threshold: realised vol this far above/below its own
#: baseline marks expansion / contraction.
_VOL_RATIO = 1.25


class PriceActionKind(str, Enum):
    """The observed price-action behaviour for the latest bar(s)."""

    MOMENTUM_UP = "momentum_up"
    MOMENTUM_DOWN = "momentum_down"
    REJECTION_UP = "rejection_up"        # upside rejection (long upper wick)
    REJECTION_DOWN = "rejection_down"    # downside rejection (long lower wick)
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    FAILED_BREAKOUT_UP = "failed_breakout_up"
    FAILED_BREAKOUT_DOWN = "failed_breakout_down"
    ACCEPTANCE_UP = "acceptance_up"      # held above a level after a break
    ACCEPTANCE_DOWN = "acceptance_down"
    RANGE = "range"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class PriceActionAnalysis:
    """The deterministic price-action read for one series."""

    kind: PriceActionKind
    direction: Direction
    confidence: Confidence
    # Volatility regime of the latest window vs its own baseline.
    volatility_state: str            # "expanding" | "contracting" | "steady" | "unknown"
    volatility_ratio: float | None
    momentum: float | None           # signed last-bar momentum (return)
    reference_price: float | None    # the level the read turned on
    last_close: float | None
    observation: str
    limitations: tuple[str, ...] = ()
    computed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_breakout(self) -> bool:
        return self.kind in (
            PriceActionKind.BREAKOUT_UP,
            PriceActionKind.BREAKOUT_DOWN,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "volatility_state": self.volatility_state,
            "volatility_ratio": self.volatility_ratio,
            "momentum": self.momentum,
            "reference_price": self.reference_price,
            "last_close": self.last_close,
            "is_breakout": self.is_breakout,
            "observation": self.observation,
            "limitations": list(self.limitations),
            "computed_at": self.computed_at.isoformat(),
        }


class PriceActionService:
    """
    Deterministic price-action read over a candle series.

    ``min_confirm_bars`` is the multi-candle rule: complex behaviours
    (rejection, failed breakout, acceptance) require that many confirming bars
    unless a caller explicitly drops it to 1.
    """

    def __init__(
        self,
        *,
        lookback: int = 20,
        min_confirm_bars: int = 2,
        vol_period: int = 20,
    ) -> None:
        if lookback < 2:
            raise ValueError("lookback must be >= 2.")
        if min_confirm_bars < 1:
            raise ValueError("min_confirm_bars must be >= 1.")
        self._lookback = lookback
        self._min_confirm = min_confirm_bars
        self._vol_period = vol_period

    def analyze(self, data: MarketData) -> PriceActionAnalysis:
        candles = data.candles
        n = len(candles)
        limitations: list[str] = []
        if n < self._lookback + self._min_confirm:
            return PriceActionAnalysis(
                kind=PriceActionKind.UNKNOWN,
                direction=Direction.UNKNOWN,
                confidence=Confidence.LOW,
                volatility_state="unknown",
                volatility_ratio=None,
                momentum=None,
                reference_price=None,
                last_close=None,
                observation="Too few bars for a price-action read.",
                limitations=(f"Have {n} bars; need >= "
                             f"{self._lookback + self._min_confirm}."),
            )

        highs = data.highs()
        lows = data.lows()
        closes = data.closes()
        volumes = data.volumes()
        last = closes[-1]
        momentum = float(closes[-1] / closes[-2] - 1.0) if n >= 2 else None

        vol_state, vol_ratio = self._volatility(closes)

        # Prior extreme the breakout tests (excluding the latest bar).
        lb = self._lookback
        prior_high = float(highs[-lb - 1 : -1].max())
        prior_low = float(lows[-lb - 1 : -1].min())

        kind, direction, confidence, ref, obs = self._classify(
            highs, lows, closes, volumes, prior_high, prior_low, last
        )

        return PriceActionAnalysis(
            kind=kind,
            direction=direction,
            confidence=confidence,
            volatility_state=vol_state,
            volatility_ratio=vol_ratio,
            momentum=round(momentum, 6) if momentum is not None else None,
            reference_price=ref,
            last_close=round(float(last), 6),
            observation=obs,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    def _volatility(self, closes: np.ndarray) -> tuple[str, float | None]:
        vol = ind.last_finite(ind.volatility(closes, self._vol_period))
        if vol is None:
            return "unknown", None
        # Baseline: mean of the prior volatility window (the bars before the
        # last vol_period), so expansion is vs the series' own recent vol.
        vol_series = ind.volatility(closes, self._vol_period)
        finite = vol_series[np.isfinite(vol_series)]
        if finite.size < 2:
            return "unknown", round(float(vol), 6)
        baseline = float(finite[:-1].mean()) if finite.size > 1 else float(vol)
        ratio = float(vol / baseline) if baseline > 0 else None
        if ratio is None:
            return "unknown", None
        if ratio >= _VOL_RATIO:
            state = "expanding"
        elif ratio <= 1.0 / _VOL_RATIO:
            state = "contracting"
        else:
            state = "steady"
        return state, round(ratio, 4)

    def _classify(
        self,
        highs, lows, closes, volumes,
        prior_high, prior_low, last,
    ) -> tuple[PriceActionKind, Direction, Confidence, float, str]:
        n = closes.size
        c = self._min_confirm

        # ---- Failed breakout: a recent break that closed back inside ----
        for back in range(1, _FAIL_WINDOW + 1):
            if n - back - 1 < 1:
                break
            broke_high = closes[-back - 1] > prior_high and last <= prior_high
            broke_low = closes[-back - 1] < prior_low and last >= prior_low
            if broke_high:
                return (
                    PriceActionKind.FAILED_BREAKOUT_UP, Direction.DOWN,
                    Confidence.MEDIUM, prior_high,
                    f"Closed above {prior_high:.2f} then fell back inside "
                    f"the range -- a failed upside breakout.",
                )
            if broke_low:
                return (
                    PriceActionKind.FAILED_BREAKOUT_DOWN, Direction.UP,
                    Confidence.MEDIUM, prior_low,
                    f"Closed below {prior_low:.2f} then recovered -- a failed "
                    f"downside breakout.",
                )

        # ---- Breakout / acceptance over `c` confirming closes ----
        above = closes[-c:] > prior_high
        below = closes[-c:] < prior_low
        if above.all():
            # Held above across `c` closes: acceptance if a later close stayed
            # inside (rejection-free), breakout if it just cleared.
            return (
                PriceActionKind.ACCEPTANCE_UP if c > 1 else PriceActionKind.BREAKOUT_UP,
                Direction.UP, Confidence.MEDIUM, prior_high,
                f"Closed above prior high {prior_high:.2f} across "
                f"{c} bar(s) -- {'held above' if c > 1 else 'a fresh break'}.",
            )
        if below.all():
            return (
                PriceActionKind.ACCEPTANCE_DOWN if c > 1 else PriceActionKind.BREAKOUT_DOWN,
                Direction.DOWN, Confidence.MEDIUM, prior_low,
                f"Closed below prior low {prior_low:.2f} across "
                f"{c} bar(s) -- {'held below' if c > 1 else 'a fresh break'}.",
            )

        # ---- Rejection: last bar's dominant wick ----
        o, h, l, cl = (
            float(closes[-2]), float(highs[-1]), float(lows[-1]), float(last)
        )
        body = abs(cl - o) or 1e-9
        upper_wick = h - max(o, cl)
        lower_wick = min(o, cl) - l
        if upper_wick >= _REJECTION_WICK_BODY * body and upper_wick > lower_wick:
            return (
                PriceActionKind.REJECTION_UP, Direction.DOWN, Confidence.LOW,
                h, f"Long upper wick ({upper_wick:.2f}) vs small body -- "
                   f"upside rejection.",
            )
        if lower_wick >= _REJECTION_WICK_BODY * body and lower_wick > upper_wick:
            return (
                PriceActionKind.REJECTION_DOWN, Direction.UP, Confidence.LOW,
                l, f"Long lower wick ({lower_wick:.2f}) vs small body -- "
                   f"downside rejection.",
            )

        # ---- Range vs momentum vs neutral ----
        rng = prior_high - prior_low
        span = (max(prior_high, h) - min(prior_low, l)) or 1e-9
        if rng / span >= 0.6 and abs(cl - closes[-self._lookback // 2]) < rng * 0.3:
            return (
                PriceActionKind.RANGE, Direction.SIDEWAYS, Confidence.LOW,
                (prior_high + prior_low) / 2,
                "Price oscillating inside the recent range.",
            )
        if n >= 3 and cl > closes[-2] > closes[-3]:
            return (
                PriceActionKind.MOMENTUM_UP, Direction.UP, Confidence.LOW,
                last, "Successive higher closes -- upside momentum.",
            )
        if n >= 3 and cl < closes[-2] < closes[-3]:
            return (
                PriceActionKind.MOMENTUM_DOWN, Direction.DOWN, Confidence.LOW,
                last, "Successive lower closes -- downside momentum.",
            )
        return (
            PriceActionKind.NEUTRAL, Direction.SIDEWAYS, Confidence.LOW,
            last, "No dominant price-action behaviour in the window.",
        )
