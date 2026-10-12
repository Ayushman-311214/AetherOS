"""
Optimal trade entry (spec Phase 6).

The OTE is the retracement band inside an impulse leg where ICT looks to enter:
the 0.618-0.79 Fibonacci window, measured *from the leg*, not drawn freehand.

The leg is reused rather than re-derived. :class:`SMCService` already computes
the active dealing range -- the most recent confirmed swing high and low -- and
records which of the two came first, which is exactly the information that says
whether the leg is an advance or a decline:

- swing **low before** swing high -> the leg went up, so the OTE is the band
  price retraces *down* into (a bullish entry);
- swing **high before** swing low -> the leg went down, so the OTE is the band
  price retraces *up* into (a bearish entry).

Two facts are reported separately because they answer different questions:
``retracement_ratio`` is the deepest retracement reached since the leg ended
(did price come back at all, and how far), while ``in_zone`` is whether price
sits in the band *now*.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..domain.enums import Confidence, Direction
from ..domain.ict import OTEZone
from ..domain.market_data import Candle
from ..domain.smc import DealingRange

#: The classic Fibonacci pair ICT quotes for the optimal trade entry window.
DEFAULT_OTE_LOW_RATIO = 0.618
DEFAULT_OTE_HIGH_RATIO = 0.79


def detect_ote(
    dealing_range: DealingRange | None,
    candles: Sequence[Candle],
    *,
    last_price: float,
    timeframe: str,
    low_ratio: float = DEFAULT_OTE_LOW_RATIO,
    high_ratio: float = DEFAULT_OTE_HIGH_RATIO,
) -> tuple[OTEZone | None, tuple[str, ...]]:
    """
    The OTE band of the active dealing range, if one can be defined.

    Returns ``(zone, limitations)``; without a dealing range there is no leg to
    measure a retracement of, and ``zone`` is None rather than a band drawn from
    nothing.
    """
    if not 0.0 < low_ratio < high_ratio < 1.0:
        raise ValueError("OTE ratios must satisfy 0 < low_ratio < high_ratio < 1.")

    if dealing_range is None:
        return None, (
            "No dealing range (needs both a confirmed swing high and swing low); "
            "an optimal trade entry band cannot be defined.",
        )

    leg_high = dealing_range.high
    leg_low = dealing_range.low
    span = leg_high - leg_low
    if span <= 0:
        return None, ("The dealing range has no height; no OTE band is defined.",)

    # The later swing is the leg's terminus; whether the low or the high came
    # first is what makes the leg bullish or bearish.
    bullish = dealing_range.low_index < dealing_range.high_index
    direction = Direction.UP if bullish else Direction.DOWN
    terminus = max(dealing_range.high_index, dealing_range.low_index)

    if bullish:
        band_bottom = leg_low + low_ratio * span
        band_top = leg_low + high_ratio * span
    else:
        band_bottom = leg_high - high_ratio * span
        band_top = leg_high - low_ratio * span

    # How deep price retraced from the leg's terminus, measured over every bar
    # since -- the current bar alone would forget a band that was tapped earlier.
    deepest = 0.0
    for bar in candles[terminus:]:
        retracement = (
            (leg_high - bar.low) / span if bullish else (bar.high - leg_low) / span
        )
        deepest = max(deepest, retracement)

    in_zone = band_bottom <= last_price <= band_top
    bar = candles[terminus]

    evidence = [
        f"The dealing range spans {leg_low:.4f}-{leg_high:.4f} "
        f"({'advance' if bullish else 'decline'} leg).",
        f"The {low_ratio:.3f}-{high_ratio:.3f} retracement band is "
        f"{band_bottom:.4f}-{band_top:.4f}.",
        f"Price has retraced {deepest:.4f} of the leg since it ended.",
    ]
    if in_zone:
        evidence.append("Price is currently inside the band.")

    zone = OTEZone(
        direction=direction,
        leg_high=leg_high,
        leg_low=leg_low,
        band_top=band_top,
        band_bottom=band_bottom,
        low_ratio=low_ratio,
        high_ratio=high_ratio,
        retracement_ratio=deepest,
        in_zone=in_zone,
        index=terminus,
        timestamp=bar.timestamp,
        timeframe=timeframe,
        confidence=Confidence.HIGH if in_zone else Confidence.MEDIUM,
        evidence=tuple(evidence),
    )
    return zone, ()
