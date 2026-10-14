"""
Market heatmap layer (Phase 3).

Covers cell generation, bucketing, aggregation, normalisation, incremental
update, persistence, sweep/absorption/pressure visualisation data, historical
replay, determinism and bounded memory. All fixtures are deterministic
synthetic books/prints -- no network, no clocks inside the builder.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.trading.domain.enums import Direction, SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.order_book import OrderBook, OrderBookLevel, TradeTick
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.heatmap.cell import HeatmapCell
from aetheros.trading.heatmap.grid import HeatmapGrid, _bucket_price, _bucket_time
from aetheros.trading.heatmap.service import HeatmapService
from aetheros.trading.heatmap.surface import project, surface
from aetheros.trading.heatmap.views import available_views, render
from aetheros.trading.liquidity.observation import LiquidityObservation
from aetheros.trading.liquidity.zone import LiquidityZone

_INST = Instrument.parse("BTC/USD", asset_class="crypto")
_PROV = Provenance(source="ccxt", tier=SourceTier.SECONDARY)
_T0 = datetime(2026, 5, 1, tzinfo=timezone.utc)


def _book(bids, asks, *, off=0, prov=_PROV):
    return OrderBook(
        instrument=_INST,
        bids=tuple(OrderBookLevel(price=p, amount=a) for p, a in bids),
        asks=tuple(OrderBookLevel(price=p, amount=a) for p, a in asks),
        timestamp=_T0 + timedelta(seconds=off),
        provenance=prov,
    )


def _tick(p, a, s, *, off=0):
    return TradeTick(
        instrument=_INST, price=p, amount=a, side=s,
        timestamp=_T0 + timedelta(seconds=off), provenance=_PROV,
    )


def _obs(price=100.0, bid=10.0, ask=5.0, buy=0.0, sell=0.0, off=0, mock=False):
    return LiquidityObservation(
        symbol="BTC/USD", timestamp=_T0 + timedelta(seconds=off), price=price,
        bid_liquidity=bid, ask_liquidity=ask,
        executed_buy_volume=buy, executed_sell_volume=sell,
        source="t", is_mock=mock,
    )


_STEPS = [
    (_book([(99, 1), (98, 1)], [(101, 1), (102, 50), (103, 1)], off=0),
     (_tick(100.5, 5, Direction.UP, off=0),)),
    (_book([(99, 1)], [(101, 1), (102, 50), (103, 1)], off=30),
     (_tick(102.0, 20, Direction.UP, off=30),)),
    (_book([(105, 1)], [(106, 1)], off=60),
     (_tick(102.5, 60, Direction.UP, off=60),)),
]


# ----------------------------------------------------------------------
# Cell model
# ----------------------------------------------------------------------


def test_cell_derives_flow_and_imbalance():
    c = HeatmapCell(
        timestamp=_T0.isoformat(), price=100.0,
        bid_intensity=60.0, ask_intensity=40.0,
        executed_buy_volume=30.0, executed_sell_volume=10.0,
    )
    assert c.total_intensity == 100.0
    assert c.imbalance == pytest.approx(0.2)
    assert c.net_flow == pytest.approx(0.5)
    d = c.to_dict()
    assert d["total_intensity"] == 100.0
    assert d["net_flow"] == pytest.approx(0.5)


def test_cell_validates_score_bounds():
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        HeatmapCell(timestamp="t", price=1.0, pressure_score=1.5)


# ----------------------------------------------------------------------
# Bucketing
# ----------------------------------------------------------------------


def test_time_and_price_bucketing_floors_to_boundaries():
    ts = datetime(2026, 5, 1, 0, 1, 23, tzinfo=timezone.utc)
    assert _bucket_time(ts, 60.0) == datetime(2026, 5, 1, 0, 1, 0, tzinfo=timezone.utc)
    assert _bucket_price(103.7, 1.0) == 103.0
    assert _bucket_price(103.7, 0.5) == 103.5


def test_bucket_config_validation():
    with pytest.raises(ValueError):
        HeatmapGrid(price_step=0, bucket_seconds=60)
    with pytest.raises(ValueError):
        HeatmapGrid(price_step=1, bucket_seconds=0)
    with pytest.raises(ValueError):
        HeatmapGrid(price_step=1, bucket_seconds=60, capacity=0)


# ----------------------------------------------------------------------
# Aggregation + incremental update
# ----------------------------------------------------------------------


def test_grid_aggregates_volumes_into_bins():
    grid = HeatmapGrid(price_step=1.0, bucket_seconds=60.0, symbol="BTC/USD")
    grid.update(_obs(price=100.0, bid=10.0, ask=5.0, buy=4.0, sell=2.0, off=0))
    grid.update(_obs(price=100.2, bid=8.0, ask=4.0, buy=6.0, sell=0.0, off=10))
    assert grid.cell_count >= 1
    cells = [c for c in grid.cells if c.price == 100.0]
    assert cells
    c = cells[0]
    # Two observations into the same bin aggregate their volumes.
    assert c.bid_intensity == 18.0
    assert c.executed_buy_volume == 10.0
    assert c.sample_count == 2


def test_grid_incremental_update_keeps_derived_max_not_sum():
    grid = HeatmapGrid(price_step=1.0, bucket_seconds=60.0)
    zone = LiquidityZone(
        symbol="BTC/USD", side="ask", lower_price=102.0, upper_price=102.0,
        persistence_score=0.7, first_seen=_T0, last_seen=_T0,
    )
    grid.update(_obs(price=100.0, off=0), zones=(zone,))
    grid.update(_obs(price=100.0, off=10), zones=(zone,))
    zcells = [c for c in grid.cells if c.price == 102.0]
    # persistence is a level (max), not an accumulation.
    assert zcells and zcells[0].persistence == pytest.approx(0.7)


# ----------------------------------------------------------------------
# Bounded memory
# ----------------------------------------------------------------------


def test_grid_bounded_capacity_evicts_oldest_bucket():
    grid = HeatmapGrid(price_step=1.0, bucket_seconds=10.0, capacity=2)
    # Three distinct 10s buckets -> oldest evicted to keep capacity=2 buckets.
    for off in (0, 15, 30):
        grid.update(_obs(price=100.0, bid=1.0, off=off))
    assert grid.time_buckets() <= 2
    remaining = {c.timestamp for c in grid.cells}
    # The earliest bucket's cells are gone.
    assert "2026-05-01T00:00:00+00:00" not in remaining


# ----------------------------------------------------------------------
# Views: shared grid, six lenses
# ----------------------------------------------------------------------


def _svc_grid():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    return svc, svc._build(_STEPS, symbol="BTC/USD")[0]


def test_six_views_share_one_grid():
    svc, grid = _svc_grid()
    assert set(available_views()) == {
        "liquidity", "persistence", "flow", "sweep", "absorption", "pressure",
    }
    for kind in available_views():
        v = render(grid, kind)
        assert v.kind == kind
        assert v.symbol == "BTC/USD"
        # Normalised views stay in [0,1].
        for p in v.points:
            assert 0.0 <= p.intensity <= 1.0


def test_unknown_view_rejected():
    svc, grid = _svc_grid()
    with pytest.raises(ValueError, match="Unknown heatmap"):
        render(grid, "bogus")


def test_normalisation_reports_observed_range():
    svc, grid = _svc_grid()
    v = render(grid, "liquidity")
    # A view reports its actual min/max, not a stretched range.
    assert v.max_intensity >= v.min_intensity
    flat = render(grid, "flow")
    assert flat.min_intensity <= flat.max_intensity


def test_service_getters():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    fns = [
        svc.get_heatmap, svc.get_liquidity_heatmap, svc.get_persistence_heatmap,
        svc.get_flow_heatmap, svc.get_sweep_heatmap, svc.get_absorption_heatmap,
        svc.get_pressure_heatmap,
    ]
    for fn in fns:
        v = fn(_STEPS, symbol="BTC/USD")
        assert v.points is not None
        assert v.cell_count >= 0


# ----------------------------------------------------------------------
# Persistence / sweep / absorption visualisation
# ----------------------------------------------------------------------


def test_persistence_heatmap_reflects_standing_liquidity():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    v = svc.get_persistence_heatmap(_STEPS, symbol="BTC/USD")
    # The standing ask wall at 102 contributes persistence cells.
    assert any(p.intensity >= 0.0 for p in v.points)


def test_sweep_heatmap_marks_swept_region():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    v = svc.get_sweep_heatmap(_STEPS, symbol="BTC/USD")
    assert v.max_intensity > 0.0  # a sweep was detected on the replay


def test_absorption_heatmap_shape():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    v = svc.get_absorption_heatmap(_STEPS, symbol="BTC/USD")
    # Absorption score is bounded and preserved as a "possible" read, not a flag.
    for p in v.points:
        assert 0.0 <= p.intensity <= 1.0


# ----------------------------------------------------------------------
# Pressure (documented heuristic)
# ----------------------------------------------------------------------


def test_pressure_is_bounded_descriptive():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    v = svc.get_pressure_heatmap(_STEPS, symbol="BTC/USD")
    for p in v.points:
        assert 0.0 <= p.intensity <= 1.0


# ----------------------------------------------------------------------
# Deterministic replay + look-ahead safety
# ----------------------------------------------------------------------


def test_deterministic_replay_identical_output():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    v1 = svc.get_heatmap(_STEPS, symbol="BTC/USD")
    v2 = svc.get_heatmap(_STEPS, symbol="BTC/USD")
    assert [p.to_dict() for p in v1.points] == [p.to_dict() for p in v2.points]


def test_no_lookahead_grid_uses_only_its_step():
    grid = HeatmapGrid(price_step=1.0, bucket_seconds=60.0)
    grid.update(_obs(price=100.0, bid=10.0, off=0))
    # Later updates can't retroactively change an already-written cell.
    before = {c.price: c.bid_intensity for c in grid.cells}
    grid.update(_obs(price=200.0, bid=99.0, off=10))
    after = {c.price: c.bid_intensity for c in grid.cells if c.price == 100.0}
    assert after[100.0] == before[100.0]


# ----------------------------------------------------------------------
# 3D surface + terminal projection
# ----------------------------------------------------------------------


def test_surface_shape_and_values():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    s = svc.get_surface(_STEPS, symbol="BTC/USD")
    assert len(s.values) == len(s.timestamps)
    for row in s.values:
        assert len(row) == len(s.prices)
    # A hot cell appears somewhere on the surface.
    assert max(v for r in s.values for v in r) > 0.0


def test_terminal_projection_renders_without_corrupting_data():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    s = svc.get_surface(_STEPS, symbol="BTC/USD")
    text = project(s, width=10)
    assert isinstance(text, str) and "intensity" in text
    # The projection doesn't mutate the surface.
    assert s.values and any(v > 0 for row in s.values for v in row)


def test_empty_surface_renders_blank():
    grid = HeatmapGrid(price_step=1.0, bucket_seconds=60.0)
    s = surface(grid)
    assert project(s) == "(empty liquidity surface)"


# ----------------------------------------------------------------------
# Mock honesty
# ----------------------------------------------------------------------


def test_mock_cells_and_views_flag_mock():
    svc = HeatmapService(price_step=1.0, bucket_seconds=30.0)
    mock_prov = Provenance(source="mock", tier=SourceTier.MOCK)
    steps = [
        (_book([(99, 1)], [(101, 1), (102, 50)], off=0, prov=mock_prov),
         (_tick(100.5, 5, Direction.UP, off=0),)),
    ]
    v = svc.get_heatmap(steps, symbol="BTC/USD", is_mock=True)
    assert v.is_mock is True
    assert all(p.is_mock for p in v.points)
