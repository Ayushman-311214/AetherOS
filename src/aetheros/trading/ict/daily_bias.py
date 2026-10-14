"""
Daily bias (spec Phase 6).

The directional read for the trading day, taken from the **previous completed
day** rather than from the current one: where price is trading relative to the
prior day's range is what ICT treats as the day's bias, and the prior day's high
and low are the liquidity that bias is measured against.

The rule is deliberately blunt, because a bias that needs a paragraph of
conditions is not a bias:

- price trading **above** the prior day's high -> bullish (the prior high was
  taken, and the day is expanding upward);
- price trading **below** the prior day's low -> bearish;
- price back **inside** the prior day's range -> the daily trend decides, and
  with no trend there is no bias (``SIDEWAYS``) rather than a coin flip.

Premium/discount is reported alongside as *location* context -- where inside the
prior range price sits -- not as the direction. Direction and location are
separate facts, and conflating them is how a "bias" quietly becomes a
prediction.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.enums import Confidence, Direction, TrendState
from ..domain.ict import DailyBias
from .sessions import DayBucket

#: Ratio band around the midpoint that counts as equilibrium rather than a
#: premium or discount read.
_EQUILIBRIUM_BAND = 0.05


def _position_of(ratio: float) -> str:
    if ratio > 0.5 + _EQUILIBRIUM_BAND:
        return "premium"
    if ratio < 0.5 - _EQUILIBRIUM_BAND:
        return "discount"
    return "equilibrium"


def detect_daily_bias(
    buckets: Sequence[DayBucket],
    *,
    last_price: float,
    timeframe: str,
    trend: TrendState = TrendState.UNKNOWN,
) -> tuple[DailyBias | None, tuple[str, ...]]:
    """
    Read the daily bias from the prior completed day.

    ``buckets`` must be chronological and exchange-local (see
    :meth:`SessionCatalogue.bucket_by_local_date`); the **last** bucket is the
    day in progress and the one before it is the prior completed day. Returns
    ``(bias, limitations)`` -- ``bias`` is None when there is no prior day to
    read, and the limitation says so rather than substituting a fabricated one.
    """
    if len(buckets) < 2:
        return None, (
            "Fewer than two exchange-local days of data; there is no completed "
            "prior day to read a daily bias from.",
        )

    prior = buckets[-2]
    if prior.high <= prior.low:
        return None, (
            "The prior day has no range (its high equals its low); premium, "
            "discount and bias are all undefined.",
        )

    span = prior.range
    ratio = (last_price - prior.low) / span
    position = _position_of(ratio)

    evidence: list[str] = [
        f"Prior day ({prior.local_date.isoformat()}) ranged "
        f"{prior.low:.4f}-{prior.high:.4f} and closed at {prior.close:.4f}.",
        f"Price at {last_price:.4f} is {ratio:.4f} of the prior day's range "
        f"({position}).",
    ]

    if last_price > prior.high:
        direction = Direction.UP
        confidence = Confidence.HIGH
        evidence.append("Price is trading above the prior day's high.")
    elif last_price < prior.low:
        direction = Direction.DOWN
        confidence = Confidence.HIGH
        evidence.append("Price is trading below the prior day's low.")
    else:
        evidence.append("Price is trading back inside the prior day's range.")
        if trend is TrendState.UPTREND:
            direction = Direction.UP
            confidence = Confidence.MEDIUM
            evidence.append("The daily structure trend is up, so the bias follows it.")
        elif trend is TrendState.DOWNTREND:
            direction = Direction.DOWN
            confidence = Confidence.MEDIUM
            evidence.append(
                "The daily structure trend is down, so the bias follows it."
            )
        else:
            direction = Direction.SIDEWAYS
            confidence = Confidence.LOW
            evidence.append(
                "Inside the prior range with no daily trend; no directional bias."
            )

    bias = DailyBias(
        direction=direction,
        prior_day_date=prior.local_date,
        prior_day_high=prior.high,
        prior_day_low=prior.low,
        prior_day_close=prior.close,
        last_price=last_price,
        price_ratio=ratio,
        position=position,
        timeframe=timeframe,
        trend=trend,
        confidence=confidence,
        evidence=tuple(evidence),
    )
    return bias, ()
