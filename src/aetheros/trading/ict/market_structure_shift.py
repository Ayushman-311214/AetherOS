"""
Market structure shift (spec Phase 6).

A market structure shift is ICT's change of character **confirmed by
displacement**: price does not merely close through the swing that was holding
the trend, it leaves with intent. Displacement is the property that separates a
genuine shift from a drift through a level, and it is the whole reason this
detector exists rather than reusing the SMC break directly.

Both halves are measured, never asserted:

- the **structure half** is reused outright -- a break flagged
  ``StructureBreakType.CHOCH`` by :class:`SMCService`, meaning a close through
  the swing *against* the prevailing trend. No pivot logic is re-implemented
  here;
- the **displacement half** is either a three-candle fair value gap left inside
  the breaking leg, or a breaking-candle body of at least
  ``displacement_body_multiple`` average true ranges. Either is sufficient; both
  together is a high-confidence shift.

A CHoCH with neither is a drift through a level and is deliberately **not**
reported as a shift.
"""

from __future__ import annotations

import numpy as np

from ..domain.enums import Confidence, StructureBreakType
from ..domain.ict import MarketStructureShift
from ..domain.market_data import MarketData
from ..domain.smc import SMCAnalysis
from ..indicators.core import atr, last_finite
from .sessions import SessionCatalogue

#: A breaking candle whose body is at least this many average true ranges is
#: treated as displaced on its own.
DEFAULT_DISPLACEMENT_BODY_MULTIPLE = 1.5


def _value_at(series: np.ndarray, index: int) -> float | None:
    """The last finite value of ``series`` at or before ``index``."""
    return last_finite(np.asarray(series, dtype=float)[: index + 1])


def detect_market_structure_shifts(
    analysis: SMCAnalysis,
    data: MarketData,
    *,
    displacement_body_multiple: float = DEFAULT_DISPLACEMENT_BODY_MULTIPLE,
    atr_period: int = 14,
    catalogue: SessionCatalogue | None = None,
) -> tuple[MarketStructureShift, ...]:
    """
    Every displaced change of character in an existing SMC read.

    Takes the SMC analysis rather than recomputing it, so the structure half of
    the judgement is shared with the rest of the engine and cannot drift out of
    step with it.
    """
    if displacement_body_multiple <= 0:
        raise ValueError("displacement_body_multiple must be positive.")

    candles = data.candles
    atr_series = atr(data.highs(), data.lows(), data.closes(), atr_period)
    gaps = analysis.fair_value_gaps

    shifts: list[MarketStructureShift] = []
    for structure_break in analysis.breaks:
        # Only a break against the prevailing trend is a *shift*; a break with
        # it is a continuation (BOS) and is not reported here.
        if structure_break.kind is not StructureBreakType.CHOCH:
            continue

        bar = candles[structure_break.index]
        body = abs(bar.close - bar.open)
        atr_value = _value_at(atr_series, structure_break.index)
        displacement = body / atr_value if atr_value and atr_value > 0 else 0.0

        # A gap left inside the breaking leg -- between the swing that gave way
        # and the close that took it -- is displacement made visible.
        left_gap = any(
            gap.direction is structure_break.direction
            and structure_break.broken_index <= gap.index <= structure_break.index
            for gap in gaps
        )

        displaced = displacement >= displacement_body_multiple
        if not (left_gap or displaced):
            continue

        evidence = [
            f"Price closed {structure_break.break_price:.4f} through the swing "
            f"at {structure_break.broken_level:.4f}, against a "
            f"{structure_break.trend_before.value} structure.",
            f"The breaking candle's body is {displacement:.2f}x ATR"
            f" ({displacement_body_multiple:.2f}x required).",
        ]
        if left_gap:
            evidence.append("The breaking leg left a fair value gap behind it.")

        session = (
            catalogue.session_for(structure_break.timestamp)
            if catalogue is not None
            else None
        )

        shifts.append(
            MarketStructureShift(
                direction=structure_break.direction,
                index=structure_break.index,
                timestamp=structure_break.timestamp,
                timeframe=structure_break.timeframe,
                broken_level=structure_break.broken_level,
                broken_index=structure_break.broken_index,
                break_price=structure_break.break_price,
                prior_trend=structure_break.trend_before,
                displacement=displacement,
                left_fair_value_gap=left_gap,
                session=session.name if session else None,
                confidence=(
                    Confidence.HIGH if (left_gap and displaced) else Confidence.MEDIUM
                ),
                evidence=tuple(evidence),
            )
        )
    return tuple(shifts)
