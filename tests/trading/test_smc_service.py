"""
SMCService: deterministic Smart Money Concepts detection.

Every case here is a hand-built candle sequence whose swings, breaks and zones
are traced by hand, so the assertions are known-answer rather than smoke tests.
The service holds no I/O and no LLM -- all detection is candle geometry.

The fixtures use explicit OHLC (``make_ohlc_market_data``) because SMC turns on
precise wicks and closes: a sweep needs a wick *beyond* a level with a close
back inside it, which the close-series helper's fixed wicks cannot express.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import (
    Direction,
    LiquidityEventKind,
    SMCZoneKind,
    SourceTier,
    StructureBreakType,
    TrendState,
)
from aetheros.trading.errors import InsufficientDataError
from aetheros.trading.services.market_structure_service import MarketStructureService
from aetheros.trading.services.smc_service import SMCService

from .conftest import make_market_data, make_ohlc_market_data

WICK = 0.5


def _path(prices: list[float], *, wick: float = WICK) -> list[tuple[float, float, float, float]]:
    """
    A continuous price path as explicit OHLC bars.

    Each bar opens at the previous close and closes at this price, with a fixed
    wick either side. Turning points in the path therefore become the swing
    highs/lows that ``MarketStructureService`` (pivot window 3) will confirm.
    """
    bars: list[tuple[float, float, float, float]] = []
    prev = prices[0]
    for price in prices:
        bars.append((prev, max(prev, price) + wick, min(prev, price) - wick, price))
        prev = price
    return bars


# Rise to a swing high at bar 6 (106.5), fall to a swing low at bar 12 (99.5),
# then rally through the high at bar 19 -- one clean BOS, and the last down
# candle of the breaking leg (bar 12) is the order block.
_BOS_PATH = [
    100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0,
    105.0, 104.0, 103.0, 102.0, 101.0, 100.0,
    101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0,
    106.0, 105.0, 104.0, 103.0,
]


def _stable(analysis) -> dict:
    payload = analysis.to_dict()
    payload.pop("computed_at", None)
    provenance = dict(payload.get("provenance") or {})
    provenance.pop("retrieved_at", None)
    payload["provenance"] = provenance
    return payload


def test_bullish_bos_with_order_block():
    data = make_ohlc_market_data(_path(_BOS_PATH))
    analysis = SMCService().analyze(data)

    assert len(analysis.breaks) == 1
    bos = analysis.breaks[0]
    assert bos.kind is StructureBreakType.BOS
    assert bos.direction is Direction.UP
    assert bos.broken_level == pytest.approx(106.5)  # the swing high at bar 6
    assert bos.broken_index == 6
    assert bos.break_price == pytest.approx(107.0)  # the close at bar 19
    assert bos.index == 19
    assert bos.trend_before is TrendState.UNKNOWN  # first break defines structure
    assert bos.evidence  # every detection carries its reasons
    assert analysis.trend is TrendState.UPTREND

    # The order block is the last down candle before the break: bar 12, which
    # ran from 101 down to 100 and so spans [99.5, 101.5].
    blocks = analysis.order_blocks
    assert len(blocks) == 1
    assert blocks[0].kind is SMCZoneKind.ORDER_BLOCK
    assert blocks[0].direction is Direction.UP
    assert blocks[0].index == 12
    assert blocks[0].bottom == pytest.approx(99.5)
    assert blocks[0].top == pytest.approx(101.5)
    # Price never returned to it *after* the break, so it stays fresh -- the
    # bars between the block and the break are price leaving the zone.
    assert blocks[0].mitigated is False

    # A steady 1-per-bar path leaves no three-candle imbalance.
    assert analysis.fair_value_gaps == ()
    assert analysis.liquidity == ()
    assert analysis.mitigation_blocks == ()


def test_bearish_choch_after_uptrend():
    # The BOS series extended by a decline that closes below the swing low the
    # uptrend was built on (99.5 at bar 12).
    prices = _BOS_PATH + [102.0, 101.0, 100.0, 99.0, 98.0, 97.0]
    data = make_ohlc_market_data(_path(prices))
    analysis = SMCService().analyze(data)

    assert len(analysis.breaks) == 2
    assert analysis.breaks[0].kind is StructureBreakType.BOS

    choch = analysis.breaks[1]
    assert choch.kind is StructureBreakType.CHOCH
    assert choch.direction is Direction.DOWN
    assert choch.broken_level == pytest.approx(99.5)  # the swing low at bar 12
    assert choch.broken_index == 12
    assert choch.break_price == pytest.approx(99.0)
    assert choch.trend_before is TrendState.UPTREND  # what it changed *from*
    assert analysis.trend is TrendState.DOWNTREND

    # The breaking leg's last up candle was bar 19.
    down_blocks = [b for b in analysis.order_blocks if b.direction is Direction.DOWN]
    assert len(down_blocks) == 1
    assert down_blocks[0].index == 19


def test_liquidity_sweep_closes_back_inside():
    # A wick to 107.5 punches through the 106.5 swing high at bar 6, but the
    # bar closes at 103 -- liquidity taken, structure not broken.
    bars = _path(
        [
            100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0,
            105.0, 104.0, 104.0, 103.0, 102.0, 101.0, 100.0,
            100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0,
            105.0, 104.0, 103.0,
        ]
    )
    # Override bar 10's wick: high well above the swing, close unchanged.
    open_, _high, low, close = bars[10]
    bars[10] = (open_, 107.5, low, close)
    analysis = SMCService().analyze(make_ohlc_market_data(bars))

    assert analysis.breaks == ()  # a sweep is not a break
    sweeps = [e for e in analysis.liquidity if e.kind is LiquidityEventKind.SWEEP]
    assert len(sweeps) == 1
    sweep = sweeps[0]
    assert sweep.direction is Direction.DOWN  # buy-side liquidity taken
    assert sweep.level == pytest.approx(106.5)
    assert sweep.extreme == pytest.approx(107.5)
    assert sweep.index == 10


def test_bullish_fair_value_gap_bounds():
    flat = [(100.0, 100.5, 99.5, 100.0)] * 21
    gap = [
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 106.5, 100.0, 106.0),   # impulse: leaves bar 21's high behind
        (106.0, 107.0, 105.5, 106.5),
    ]
    analysis = SMCService().analyze(make_ohlc_market_data(flat + gap))

    gaps = analysis.fair_value_gaps
    assert len(gaps) == 1
    assert gaps[0].kind is SMCZoneKind.FAIR_VALUE_GAP
    assert gaps[0].direction is Direction.UP
    assert gaps[0].bottom == pytest.approx(100.5)  # high of bar 21
    assert gaps[0].top == pytest.approx(105.5)     # low of bar 23
    assert gaps[0].index == 23


def test_mitigation_block_is_a_held_order_block():
    # The BOS series extended so the decline back into the bar-12 order block
    # ([99.5, 101.5]) stops there -- mitigated, not invalidated. Bar 24 is the
    # first bar whose range reaches the zone (its low is exactly the top).
    prices = _BOS_PATH + [102.0, 101.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    analysis = SMCService().analyze(make_ohlc_market_data(_path(prices)))

    blocks = analysis.order_blocks
    assert len(blocks) == 1
    assert blocks[0].mitigated is True
    assert blocks[0].invalidated is False
    assert blocks[0].mitigation_index == 24  # first bar back inside the zone

    mitigated = analysis.mitigation_blocks
    assert len(mitigated) == 1
    assert mitigated[0].index == 12
    assert "returned into the zone" in " ".join(mitigated[0].evidence)


def test_equal_lows_pool_from_two_swings_at_the_same_price():
    # The extended series has swing lows at bar 12 and bar 26, both 99.5.
    prices = _BOS_PATH + [102.0, 101.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    analysis = SMCService().analyze(make_ohlc_market_data(_path(prices)))

    pools = [e for e in analysis.liquidity if e.kind is LiquidityEventKind.EQUAL_LOWS]
    assert len(pools) == 1
    assert pools[0].direction is Direction.UP
    assert pools[0].level == pytest.approx(99.5)
    assert pools[0].index == 26  # the most recent swing in the cluster


def test_premium_read_from_dealing_range():
    # Swing high 106.5 (bar 6), swing low 98.5 (bar 13), closing at 107 --
    # above the range, so the ratio exceeds 1 rather than being clamped.
    prices = [
        100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0,
        105.0, 104.0, 103.0, 102.0, 101.0, 100.0, 99.0,
        100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0,
    ]
    analysis = SMCService().analyze(make_ohlc_market_data(_path(prices)))

    dealing_range = analysis.dealing_range
    assert dealing_range is not None
    assert dealing_range.high == pytest.approx(106.5)
    assert dealing_range.low == pytest.approx(98.5)
    assert dealing_range.equilibrium == pytest.approx(102.5)
    assert dealing_range.position == "premium"
    assert dealing_range.price_ratio == pytest.approx((107.0 - 98.5) / 8.0)
    assert dealing_range.price_ratio > 1.0  # honestly unclamped


def test_discount_read_from_dealing_range():
    analysis = SMCService().analyze(make_ohlc_market_data(_path(_BOS_PATH)))

    dealing_range = analysis.dealing_range
    assert dealing_range is not None
    assert dealing_range.high == pytest.approx(107.5)
    assert dealing_range.low == pytest.approx(99.5)
    assert dealing_range.position == "discount"
    assert dealing_range.price_ratio < 0.5


def test_no_break_is_attributed_before_its_swing_could_be_confirmed():
    """
    The no-look-ahead invariant: a swing at index ``i`` is only knowable from
    ``i + pivot_window``, so no break may be attributed to a pivot the bar
    could not yet have seen.

    A close beyond a pivot *inside* its confirmation window is arithmetically
    impossible under this pivot rule -- a pivot is the extreme of a window
    spanning the following ``k`` bars, so until that window has passed no later
    close can exceed it. The invariant is therefore the property worth pinning,
    and it is checked across every structure-breaking fixture.
    """
    pivot_window = MarketStructureService().pivot_window
    service = SMCService()

    for prices in (
        _BOS_PATH,
        _BOS_PATH + [102.0, 101.0, 100.0, 99.0, 98.0, 97.0],
        _BOS_PATH + [102.0, 101.0, 100.0, 100.0, 100.0, 100.0, 100.0],
    ):
        analysis = service.analyze(make_ohlc_market_data(_path(prices)))
        assert analysis.breaks, "fixture is meant to break structure"
        for structure_break in analysis.breaks:
            assert (
                structure_break.broken_index + pivot_window <= structure_break.index
            )


def test_flat_series_reports_no_structure_honestly():
    data = make_ohlc_market_data([(100.0, 100.5, 99.5, 100.0)] * 24)
    analysis = SMCService().analyze(data)

    assert analysis.breaks == ()
    assert analysis.zones == ()
    assert analysis.liquidity == ()
    assert analysis.dealing_range is None
    assert analysis.trend is TrendState.UNKNOWN
    assert any("No confirmed swing points" in lim for lim in analysis.limitations)
    assert any(
        "never closed through a confirmed swing" in lim
        for lim in analysis.limitations
    )
    assert any("dealing range" in lim for lim in analysis.limitations)


def test_thin_series_raises_insufficient_data():
    data = make_market_data([100.0 + i for i in range(10)])
    with pytest.raises(InsufficientDataError):
        SMCService().analyze(data)


def test_mock_and_bad_data_record_limitations():
    analysis = SMCService().analyze(
        make_ohlc_market_data(_path(_BOS_PATH), tier=SourceTier.MOCK)
    )
    assert analysis.provenance is not None
    assert analysis.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in lim for lim in analysis.limitations)
    # Detections are still derived from the candles, not suppressed by the tier.
    assert len(analysis.breaks) == 1


def test_determinism():
    service = SMCService()
    data = make_ohlc_market_data(_path(_BOS_PATH))
    assert _stable(service.analyze(data)) == _stable(service.analyze(data))


def test_invalid_arguments_rejected():
    with pytest.raises(ValueError):
        SMCService(equal_tolerance_pct=0.0)
    with pytest.raises(ValueError):
        SMCService(sweep_tolerance_pct=-1.0)
    with pytest.raises(ValueError):
        SMCService(min_bars=1)
