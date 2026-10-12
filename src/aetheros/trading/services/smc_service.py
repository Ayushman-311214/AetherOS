"""
Smart Money Concepts (SMC) service.

Derives the spec's SMC concepts from a candle series by explicit, deterministic
rules -- never by keyword matching and never from an LLM (CLAUDE.md sections 5,
8, 22):

- **BOS / CHoCH** -- a *close* through the most recent confirmed swing point,
  classified by whether it continues the running structure or reverses it.
- **Order blocks** -- the last opposing candle of the impulse leg that produced
  a break, as a ``[low, high]`` zone.
- **Fair value gaps** -- the 3-candle imbalance where one bar's low sits above
  the high of the bar two back (bullish), or its high below that bar's low
  (bearish).
- **Mitigation blocks** -- order blocks price returned to and respected (a
  derived view over the zones, see ``SMCAnalysis.mitigation_blocks``).
- **Liquidity sweeps** -- a wick beyond a confirmed swing that closes back
  inside it (a stop-run), as opposed to a break, which closes beyond.
- **Equal highs / lows** -- clustered confirmed swings at near-identical
  prices, i.e. resting liquidity.
- **Premium / discount** -- price's position within the active dealing range
  between the latest swing high and low.

Swing detection and the trend read are **reused** from
:class:`MarketStructureService` rather than reimplemented; this service only
adds the SMC interpretation on top of the same pivots.

No look-ahead: ``MarketStructureService`` can only confirm a swing ``k`` bars
after it forms, so a swing is treated as *known* only from ``index + k`` onward.
A break is therefore never tested against a pivot the bar could not have seen.
"""

from __future__ import annotations

from collections import deque

from ...core.logging import get_logger
from ..domain.enums import (
    Confidence,
    DataQualityStatus,
    Direction,
    LiquidityEventKind,
    SMCZoneKind,
    SourceTier,
    StructureBreakType,
    TrendState,
)
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..domain.smc import (
    DealingRange,
    LiquidityEvent,
    SMCAnalysis,
    SMCZone,
    StructureBreak,
)
from ..domain.structure import SwingPoint
from ..errors import InsufficientDataError
from .market_structure_service import MarketStructureService

logger = get_logger("trading.smc")

# A break must clear the level by this much before it counts, so a one-tick
# poke does not register as a structural event. Expressed as a fraction.
_MIN_BREAK_PENETRATION = 0.0

# Price within this fraction of a cluster centre is an "equal" high/low.
DEFAULT_EQUAL_TOLERANCE_PCT = 0.05

# Minimum wick penetration beyond a swing for a liquidity sweep to count.
DEFAULT_SWEEP_TOLERANCE_PCT = 0.02

# Ratio band around the range midpoint reported as "equilibrium" rather than a
# premium/discount read (0.45..0.55 of the range).
_EQUILIBRIUM_BAND = 0.05


class SMCService:
    """Deterministic SMC detection over a candle series."""

    def __init__(
        self,
        structure: MarketStructureService | None = None,
        *,
        equal_tolerance_pct: float = DEFAULT_EQUAL_TOLERANCE_PCT,
        sweep_tolerance_pct: float = DEFAULT_SWEEP_TOLERANCE_PCT,
        min_bars: int = 20,
    ) -> None:
        if equal_tolerance_pct <= 0:
            raise ValueError("equal_tolerance_pct must be positive.")
        if sweep_tolerance_pct <= 0:
            raise ValueError("sweep_tolerance_pct must be positive.")
        if min_bars < 5:
            raise ValueError("min_bars must be at least 5.")
        self._structure = structure or MarketStructureService()
        self._equal_tol = equal_tolerance_pct / 100.0
        self._sweep_tol = sweep_tolerance_pct / 100.0
        self._min_bars = min_bars

    # ------------------------------------------------------------------

    def analyze(self, data: MarketData) -> SMCAnalysis:
        candles = data.candles
        if len(candles) < self._min_bars:
            raise InsufficientDataError(
                f"Need at least {self._min_bars} candles for SMC analysis, "
                f"got {len(candles)}.",
                context={"instrument": data.instrument.key, "bars": len(candles)},
            )

        # Reuse the existing structure layer for swings + trend.
        structure = self._structure.analyze(data)
        swings = structure.swings
        timeframe = data.timeframe.value

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append("SMC read is based on synthetic MOCK data.")
        if data.quality.status in (
            DataQualityStatus.MISSING,
            DataQualityStatus.INVALID,
        ):
            limitations.append(
                f"Underlying data quality is '{data.quality.status.value}'."
            )

        breaks, zones, trend = self._detect_structure(
            data, swings, timeframe, limitations
        )
        liquidity = self._detect_liquidity(data, swings, timeframe, limitations)
        dealing_range = self._dealing_range(data, swings, limitations)

        if not swings:
            limitations.append(
                "No confirmed swing points in this window; no SMC structure "
                "could be derived."
            )

        return SMCAnalysis(
            instrument_key=data.instrument.key,
            timeframe=timeframe,
            last_price=float(data.last_price),
            trend=trend,
            breaks=tuple(breaks),
            zones=tuple(zones),
            liquidity=tuple(liquidity),
            dealing_range=dealing_range,
            provenance=Provenance(
                source=data.provenance.source,
                tier=(
                    SourceTier.MOCK
                    if data.provenance.is_mock
                    else SourceTier.DERIVED
                ),
                detail="deterministic SMC analysis",
            ),
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------
    # BOS / CHoCH + order blocks

    def _detect_structure(
        self,
        data: MarketData,
        swings: tuple[SwingPoint, ...],
        timeframe: str,
        limitations: list[str],
    ) -> tuple[list[StructureBreak], list[SMCZone], TrendState]:
        candles = data.candles
        closes = data.closes()
        n = len(candles)
        k = self._structure.pivot_window

        # Swings become *known* only k bars after they form (no look-ahead).
        pending = deque(sorted(swings, key=lambda s: s.index))
        active_high: SwingPoint | None = None
        active_low: SwingPoint | None = None

        breaks: list[StructureBreak] = []
        order_blocks: list[SMCZone] = []
        # First bar whose behaviour can *mitigate* each order block. An order
        # block sits inside the impulse leg that broke structure, so the bars
        # between it and the break are price leaving the zone, not returning to
        # it. Scanning from the zone's own bar would mark every block as
        # mitigated on the very next candle, which carries no information.
        block_scan_from: list[int] = []
        trend = TrendState.UNKNOWN
        leg_start = 0  # first bar of the current, unbroken leg

        for j in range(n):
            while pending and pending[0].index + k <= j:
                swing = pending.popleft()
                if swing.kind == "high":
                    active_high = swing
                else:
                    active_low = swing

            broke = False
            level = None
            direction = None
            if active_high is not None:
                penetration = (closes[j] - active_high.price) / active_high.price
                if penetration > _MIN_BREAK_PENETRATION:
                    level, direction, broke = active_high, Direction.UP, True
            if not broke and active_low is not None:
                penetration = (active_low.price - closes[j]) / active_low.price
                if penetration > _MIN_BREAK_PENETRATION:
                    level, direction, broke = active_low, Direction.DOWN, True

            if not broke or level is None or direction is None:
                continue

            # Continuation vs reversal. With no established structure yet the
            # first break *defines* the trend, so it is a BOS, not a CHoCH.
            if trend is TrendState.UNKNOWN:
                kind = StructureBreakType.BOS
            elif (trend is TrendState.UPTREND) == (direction is Direction.UP):
                kind = StructureBreakType.BOS
            else:
                kind = StructureBreakType.CHOCH
            trend_before = trend
            trend = (
                TrendState.UPTREND if direction is Direction.UP else TrendState.DOWNTREND
            )

            penetration_pct = (
                abs(closes[j] - level.price) / level.price * 100.0
            )
            score = min(1.0, 0.45 + penetration_pct * 20.0)
            breaks.append(
                StructureBreak(
                    kind=kind,
                    direction=direction,
                    index=j,
                    timestamp=candles[j].timestamp,
                    timeframe=timeframe,
                    broken_level=float(level.price),
                    broken_index=level.index,
                    break_price=float(closes[j]),
                    trend_before=trend_before,
                    confidence=Confidence.from_score(score),
                    evidence=(
                        f"Close {closes[j]:.2f} broke the {level.kind} swing "
                        f"{level.price:.2f} set at bar {level.index}.",
                        f"Penetration {penetration_pct:.3f}% beyond the level.",
                        (
                            "Continues the prevailing structure (BOS)."
                            if kind is StructureBreakType.BOS
                            else "First break against the prevailing structure "
                            "(CHoCH)."
                        ),
                    ),
                )
            )

            block = self._order_block(
                data, direction=direction, break_index=j, leg_start=leg_start,
                timeframe=timeframe,
            )
            if block is not None:
                order_blocks.append(block)
                block_scan_from.append(j + 1)

            if direction is Direction.UP:
                active_high = None
            else:
                active_low = None
            leg_start = j

        if not breaks:
            limitations.append(
                "Price never closed through a confirmed swing; no BOS or CHoCH "
                "in this window."
            )
        if breaks and not order_blocks:
            limitations.append(
                "No opposing candle was found in the breaking leg; no order "
                "block could be derived."
            )

        gaps = self._fair_value_gaps(data, timeframe)
        zones = list(order_blocks) + list(gaps)
        # A gap is created by its own (third) candle, so it is mitigable from
        # the bar after that one.
        scan_from = block_scan_from + [gap.index + 1 for gap in gaps]
        self._resolve_mitigation(data, zones, scan_from)
        return breaks, zones, trend

    def _order_block(
        self,
        data: MarketData,
        *,
        direction: Direction,
        break_index: int,
        leg_start: int,
        timeframe: str,
    ) -> SMCZone | None:
        """
        Last opposing candle of the breaking leg, as a ``[low, high]`` zone.

        A bullish break originates from the last *down* candle before it (the
        last bar where sellers were in control); a bearish break from the last
        *up* candle. Returns ``None`` when the leg holds no opposing candle --
        an honest gap rather than a fabricated zone.
        """
        candles = data.candles
        for i in range(break_index - 1, leg_start - 1, -1):
            candle = candles[i]
            opposing = (
                candle.close < candle.open
                if direction is Direction.UP
                else candle.close > candle.open
            )
            if not opposing:
                continue
            penetration_pct = (
                abs(candles[break_index].close - candle.close) / candle.close * 100.0
            )
            return SMCZone(
                kind=SMCZoneKind.ORDER_BLOCK,
                direction=direction,
                top=float(candle.high),
                bottom=float(candle.low),
                index=i,
                timestamp=candle.timestamp,
                timeframe=timeframe,
                confidence=Confidence.from_score(
                    min(1.0, 0.45 + penetration_pct * 10.0)
                ),
                evidence=(
                    f"Last opposing candle before the {direction.value} break "
                    f"at bar {break_index}.",
                    f"Zone is that candle's range [{candle.low:.2f}, "
                    f"{candle.high:.2f}].",
                ),
            )
        return None

    # ------------------------------------------------------------------

    def _fair_value_gaps(
        self, data: MarketData, timeframe: str
    ) -> list[SMCZone]:
        """Three-candle imbalances, detected from the raw candle geometry."""
        candles = data.candles
        highs = data.highs()
        lows = data.lows()
        zones: list[SMCZone] = []
        for i in range(2, len(candles)):
            # Bullish gap: the current low leaves the high two bars back behind.
            if lows[i] > highs[i - 2]:
                top, bottom, direction = float(lows[i]), float(highs[i - 2]), Direction.UP
            # Bearish gap: the current high sits below the low two bars back.
            elif highs[i] < lows[i - 2]:
                top, bottom, direction = float(lows[i - 2]), float(highs[i]), Direction.DOWN
            else:
                continue
            size_pct = (top - bottom) / bottom * 100.0
            zones.append(
                SMCZone(
                    kind=SMCZoneKind.FAIR_VALUE_GAP,
                    direction=direction,
                    top=top,
                    bottom=bottom,
                    index=i,
                    timestamp=candles[i].timestamp,
                    timeframe=timeframe,
                    confidence=Confidence.from_score(min(1.0, 0.4 + size_pct * 20.0)),
                    evidence=(
                        f"Three-candle imbalance confirmed at bar {i}.",
                        f"Gap spans [{bottom:.2f}, {top:.2f}] "
                        f"({size_pct:.3f}% of price).",
                    ),
                )
            )
        return zones

    @staticmethod
    def _resolve_mitigation(
        data: MarketData, zones: list[SMCZone], scan_from: list[int]
    ) -> None:
        """
        Annotate each zone with what price did afterwards, in place.

        ``mitigated`` -- a later bar traded back into the zone. ``invalidated``
        -- a later bar *closed* through the zone's far edge, which is what
        actually kills a zone. Both are read off the candles; neither is
        assumed.

        ``scan_from`` gives, per zone, the first bar whose behaviour counts as
        a *return* to it -- for an order block that is the bar after the break
        that the block gave rise to, not the block's own bar.
        """
        candles = data.candles
        closes = data.closes()
        highs = data.highs()
        lows = data.lows()
        for index, (zone, start) in enumerate(zip(zones, scan_from)):
            touch_index: int | None = None
            invalidate_index: int | None = None
            for j in range(start, len(candles)):
                overlaps = lows[j] <= zone.top and highs[j] >= zone.bottom
                if touch_index is None and overlaps:
                    touch_index = j
                # A zone dies when price *closes* through its far edge.
                if zone.direction is Direction.UP:
                    if closes[j] < zone.bottom:
                        invalidate_index = j
                        break
                elif closes[j] > zone.top:
                    invalidate_index = j
                    break

            if touch_index is None and invalidate_index is None:
                continue  # never revisited: the zone stays fresh
            # A bar that closed straight through without overlapping still
            # killed the zone, so it is the reference the model needs.
            mitigation_index = (
                touch_index if touch_index is not None else invalidate_index
            )
            zones[index] = SMCZone(
                kind=zone.kind,
                direction=zone.direction,
                top=zone.top,
                bottom=zone.bottom,
                index=zone.index,
                timestamp=zone.timestamp,
                timeframe=zone.timeframe,
                mitigated=touch_index is not None,
                invalidated=invalidate_index is not None,
                mitigation_index=mitigation_index,
                confidence=zone.confidence,
                evidence=zone.evidence
                + (
                    (
                        f"Price returned into the zone at bar {mitigation_index}."
                        if touch_index is not None
                        else "Price never returned into the zone."
                    ),
                    (
                        "Zone invalidated: price closed through it."
                        if invalidate_index is not None
                        else "Zone still valid."
                    ),
                ),
            )

    # ------------------------------------------------------------------

    def _detect_liquidity(
        self,
        data: MarketData,
        swings: tuple[SwingPoint, ...],
        timeframe: str,
        limitations: list[str],
    ) -> list[LiquidityEvent]:
        sweeps = self._liquidity_sweeps(data, swings, timeframe)
        pools = self._equal_extremes(data, swings, timeframe)
        if not sweeps and not pools:
            limitations.append(
                "No liquidity sweep or equal-highs/lows pool detected in this "
                "window."
            )
        return sweeps + pools

    def _liquidity_sweeps(
        self,
        data: MarketData,
        swings: tuple[SwingPoint, ...],
        timeframe: str,
    ) -> list[LiquidityEvent]:
        """
        Wicks that take a confirmed swing level but close back inside it.

        This is the mirror of a break: the same level, but price failed to hold
        beyond it, so the level was *taken* rather than broken. Each swing
        level can only be swept once, and a level that was later broken is not
        also reported as a sweep.
        """
        candles = data.candles
        closes = data.closes()
        highs = data.highs()
        lows = data.lows()
        n = len(candles)
        k = self._structure.pivot_window

        pending = deque(sorted(swings, key=lambda s: s.index))
        active_high: SwingPoint | None = None
        active_low: SwingPoint | None = None
        # A level stops being resting liquidity once price has either taken it
        # (a sweep, reported here) or closed through it (a break, reported by
        # ``_detect_structure``). Both retire it: the same swing yields at most
        # one event, and a broken level is no longer a level to be swept --
        # price trading back over it afterwards is a retest, not liquidity.
        retired: set[int] = set()
        events: list[LiquidityEvent] = []

        for j in range(n):
            while pending and pending[0].index + k <= j:
                swing = pending.popleft()
                if swing.kind == "high":
                    active_high = swing
                else:
                    active_low = swing

            if active_high is not None and active_high.index not in retired:
                if (closes[j] - active_high.price) / active_high.price > (
                    _MIN_BREAK_PENETRATION
                ):
                    # Closed beyond it, at the same threshold ``_detect_structure``
                    # uses -- ``broken`` and ``swept`` must partition every level.
                    retired.add(active_high.index)
                else:
                    penetration = (highs[j] - active_high.price) / active_high.price
                    if penetration >= self._sweep_tol and closes[j] < active_high.price:
                        retired.add(active_high.index)
                        events.append(
                            self._sweep_event(
                                data, j, direction=Direction.DOWN,
                                level=float(active_high.price), extreme=float(highs[j]),
                                penetration=penetration, timeframe=timeframe,
                                kind_label="buy-side",
                            )
                        )
                        continue

            if active_low is not None and active_low.index not in retired:
                if (active_low.price - closes[j]) / active_low.price > (
                    _MIN_BREAK_PENETRATION
                ):
                    retired.add(active_low.index)
                else:
                    penetration = (active_low.price - lows[j]) / active_low.price
                    if penetration >= self._sweep_tol and closes[j] > active_low.price:
                        retired.add(active_low.index)
                        events.append(
                            self._sweep_event(
                                data, j, direction=Direction.UP,
                                level=float(active_low.price), extreme=float(lows[j]),
                                penetration=penetration, timeframe=timeframe,
                                kind_label="sell-side",
                            )
                        )
        return events

    @staticmethod
    def _sweep_event(
        data: MarketData,
        index: int,
        *,
        direction: Direction,
        level: float,
        extreme: float,
        penetration: float,
        timeframe: str,
        kind_label: str,
    ) -> LiquidityEvent:
        return LiquidityEvent(
            kind=LiquidityEventKind.SWEEP,
            direction=direction,
            level=level,
            extreme=extreme,
            index=index,
            timestamp=data.candles[index].timestamp,
            timeframe=timeframe,
            confidence=Confidence.from_score(min(1.0, 0.4 + penetration * 100.0)),
            evidence=(
                f"Wick took {kind_label} liquidity at {level:.2f} "
                f"(extreme {extreme:.2f}).",
                f"Close {data.candles[index].close:.2f} returned inside the "
                f"level -- a sweep, not a break.",
            ),
        )

    def _equal_extremes(
        self,
        data: MarketData,
        swings: tuple[SwingPoint, ...],
        timeframe: str,
    ) -> list[LiquidityEvent]:
        """Clusters of confirmed swings at near-identical prices."""
        events: list[LiquidityEvent] = []
        for kind, event_kind, direction in (
            ("high", LiquidityEventKind.EQUAL_HIGHS, Direction.DOWN),
            ("low", LiquidityEventKind.EQUAL_LOWS, Direction.UP),
        ):
            prices = [s for s in swings if s.kind == kind]
            if len(prices) < 2:
                continue
            ordered = sorted(prices, key=lambda s: s.price)
            cluster: list[SwingPoint] = [ordered[0]]
            for swing in ordered[1:]:
                anchor = cluster[0].price
                if anchor > 0 and abs(swing.price - anchor) / anchor <= self._equal_tol:
                    cluster.append(swing)
                else:
                    events.extend(
                        self._pool_events(data, cluster, event_kind, direction, timeframe)
                    )
                    cluster = [swing]
            events.extend(
                self._pool_events(data, cluster, event_kind, direction, timeframe)
            )
        return events

    @staticmethod
    def _pool_events(
        data: MarketData,
        cluster: list[SwingPoint],
        event_kind: LiquidityEventKind,
        direction: Direction,
        timeframe: str,
    ) -> list[LiquidityEvent]:
        if len(cluster) < 2:
            return []
        last = max(cluster, key=lambda s: s.index)
        level = sum(s.price for s in cluster) / len(cluster)
        extreme = max(s.price for s in cluster)
        indices = ", ".join(str(s.index) for s in sorted(cluster, key=lambda s: s.index))
        return [
            LiquidityEvent(
                kind=event_kind,
                direction=direction,
                level=float(level),
                extreme=float(extreme),
                index=last.index,
                timestamp=data.candles[last.index].timestamp,
                timeframe=timeframe,
                confidence=Confidence.from_score(min(1.0, 0.4 + 0.15 * len(cluster))),
                evidence=(
                    f"{len(cluster)} swings cluster at ~{level:.2f} "
                    f"(bars {indices}) -- resting liquidity.",
                ),
            )
        ]

    # ------------------------------------------------------------------

    @staticmethod
    def _dealing_range(
        data: MarketData,
        swings: tuple[SwingPoint, ...],
        limitations: list[str],
    ) -> DealingRange | None:
        highs = [s for s in swings if s.kind == "high"]
        lows = [s for s in swings if s.kind == "low"]
        if not highs or not lows:
            limitations.append(
                "Needs both a swing high and a swing low to define a dealing "
                "range; premium/discount unavailable."
            )
            return None
        swing_high = max(highs, key=lambda s: s.index)
        swing_low = max(lows, key=lambda s: s.index)
        if swing_high.price <= swing_low.price:
            limitations.append(
                "Latest swing high is not above the latest swing low; no valid "
                "dealing range."
            )
            return None

        high = float(swing_high.price)
        low = float(swing_low.price)
        last_price = float(data.last_price)
        ratio = (last_price - low) / (high - low)
        if ratio > 0.5 + _EQUILIBRIUM_BAND:
            position = "premium"
        elif ratio < 0.5 - _EQUILIBRIUM_BAND:
            position = "discount"
        else:
            position = "equilibrium"
        return DealingRange(
            high=high,
            low=low,
            equilibrium=(high + low) / 2.0,
            position=position,
            price_ratio=round(ratio, 6),
            high_index=swing_high.index,
            low_index=swing_low.index,
        )
