"""
Liquidity-intelligence layer (Phase 2).

Covers the brief's test list: order-book normalization, imbalance, zone
detection/clustering/persistence, replenishment, consumption, sweep detection
and rejection-vs-acceptance, absorption, deterministic replay, look-ahead
safety, event emission and serialization/persistence.

All fixtures are deterministic synthetic books/prints -- no network, no clocks
inside the analyzers, so a replayed stream is fully reproducible.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.runtime.events.event_bus import EventBus
from aetheros.runtime.events.events import Event
from aetheros.trading.domain.enums import Direction, SourceTier
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.order_book import OrderBook, OrderBookLevel, TradeTick
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.errors import ProviderError
from aetheros.trading.events import (
    LiquidityAbsorbed,
    LiquidityConsumed,
    LiquidityImbalanceChanged,
    LiquiditySwept,
    LiquidityZoneCreated,
    LiquidityZoneInvalidated,
    LiquidityZoneWeakened,
)
from aetheros.trading.liquidity.analyzers import (
    SWEEP_ACCEPTANCE,
    SWEEP_NONE,
    SWEEP_REJECTION,
    analyze_absorption,
    analyze_consumption,
    analyze_imbalance,
    analyze_replenishment,
    classify_sweep,
    detect_zones,
)
from aetheros.trading.liquidity.engine import LiquidityEngine
from aetheros.trading.liquidity.features import extract_features
from aetheros.trading.liquidity.observation import LiquidityObservation
from aetheros.trading.liquidity.persistence import (
    FileObservationStore,
    FileZoneStore,
    InMemoryObservationStore,
    InMemoryZoneStore,
)
from aetheros.trading.liquidity.service import LiquidityIntelligenceService
from aetheros.trading.liquidity.sources import ProviderSource
from aetheros.trading.liquidity.zone import LiquidityZone
from aetheros.trading.liquidity.tracker import ZoneTracker

_INST = Instrument.parse("BTC/USD", asset_class="crypto")
_PROV = Provenance(source="ccxt", tier=SourceTier.SECONDARY)
_MOCK = Provenance(source="mock", tier=SourceTier.MOCK)
_T0 = datetime(2026, 5, 1, tzinfo=timezone.utc)


def _book(bids, asks, *, off=0, inst=_INST, prov=_PROV) -> OrderBook:
    return OrderBook(
        instrument=inst,
        bids=tuple(OrderBookLevel(price=p, amount=a) for p, a in bids),
        asks=tuple(OrderBookLevel(price=p, amount=a) for p, a in asks),
        timestamp=_T0 + timedelta(seconds=off),
        provenance=prov,
    )


def _tick(price, amount, side, *, off=0, inst=_INST, prov=_PROV) -> TradeTick:
    return TradeTick(
        instrument=inst,
        price=price,
        amount=amount,
        side=side,
        timestamp=_T0 + timedelta(seconds=off),
        provenance=prov,
    )


def _obs(bid, ask, *, buy=0.0, sell=0.0, price=100.0, mock=False, off=0):
    return LiquidityObservation(
        symbol="BTC/USD",
        timestamp=_T0 + timedelta(seconds=off),
        price=price,
        bid_liquidity=bid,
        ask_liquidity=ask,
        executed_buy_volume=buy,
        executed_sell_volume=sell,
        source="test",
        is_mock=mock,
    )


def _zone(side="ask", lo=102.0, hi=103.0, **kw) -> LiquidityZone:
    return LiquidityZone(
        symbol="BTC/USD", side=side, lower_price=lo, upper_price=hi,
        first_seen=_T0, last_seen=_T0, **kw,
    )


# ----------------------------------------------------------------------
# Canonical observation model
# ----------------------------------------------------------------------


def test_observation_derives_imbalance_and_flow():
    obs = _obs(bid=70.0, ask=30.0, buy=80.0, sell=20.0)
    assert obs.imbalance == pytest.approx(0.4)
    assert obs.net_flow == pytest.approx(0.6)
    assert obs.total_liquidity == 100.0
    d = obs.to_dict()
    assert d["imbalance"] == pytest.approx(0.4)
    back = LiquidityObservation.from_dict(d)
    assert back.imbalance == pytest.approx(obs.imbalance)


def test_observation_empty_book_is_balanced():
    obs = _obs(bid=0.0, ask=0.0)
    assert obs.imbalance == 0.0
    assert obs.net_flow == 0.0


def test_observation_validates():
    with pytest.raises(ValueError, match="tz-aware"):
        _obs(1, 1, price=1.0).__class__(
            symbol="X", timestamp=datetime(2026, 1, 1), price=1.0
        )
    with pytest.raises(ValueError):
        LiquidityObservation(symbol="X", timestamp=_T0, price=-1.0)


# ----------------------------------------------------------------------
# Order-book normalization (cluster detection)
# ----------------------------------------------------------------------


def test_zone_detection_finds_a_fat_wall():
    # A 50-size ask level dwarfs the surrounding 1-size levels.
    book = _book(bids=[(99, 1), (98, 1)], asks=[(101, 1), (102, 50), (103, 1)])
    clusters = detect_zones(book)
    ask = [c for c in clusters if c.side == "ask"]
    assert len(ask) == 1
    assert ask[0].lower_price == 102.0
    assert ask[0].liquidity == 50.0


def test_zone_clustering_merges_adjacent_levels():
    # Two adjacent fat levels (each >= 1.5x the book's median level) merge into
    # one wall. Median here is 1, so the 30-size 101/102 levels qualify and the
    # thin 103 does not extend the cluster.
    book = _book(
        bids=[(99, 1), (98, 1), (97, 1)],
        asks=[(101, 30), (102, 30), (103, 1), (104, 1)],
    )
    clusters = detect_zones(book)
    ask = [c for c in clusters if c.side == "ask"]
    assert len(ask) == 1
    assert ask[0].lower_price == 101.0 and ask[0].upper_price == 102.0
    assert ask[0].liquidity == 60.0


def test_zone_detection_ignores_a_largest_but_isolated_level():
    # Spec: the single largest order is not automatically a zone if it does not
    # clear the book-relative threshold alongside its neighbours. A book of all
    # 1-size levels yields no cluster (nothing is "large" relative to the median).
    book = _book(bids=[(99, 1), (98, 1)], asks=[(101, 1), (102, 1)])
    assert detect_zones(book) == ()


def test_zone_geometry_and_id():
    z1 = _zone()
    z2 = _zone()
    assert z1.id == z2.id  # same band+side -> same content-addressed id
    assert z1.contains(102.5)
    assert not z1.contains(105.0)
    assert z1.is_active


# ----------------------------------------------------------------------
# Imbalance analyzer
# ----------------------------------------------------------------------


def test_imbalance_flags_a_lopsided_book():
    res = analyze_imbalance(_obs(bid=80.0, ask=20.0))
    assert res.dominant_side == "bid"
    assert res.is_significant
    assert res.imbalance == pytest.approx(0.6)


def test_imbalance_balanced_book():
    res = analyze_imbalance(_obs(bid=50.0, ask=50.0))
    assert res.dominant_side == "balanced"
    assert not res.is_significant


# ----------------------------------------------------------------------
# Consumption analyzer
# ----------------------------------------------------------------------


def test_consumption_ratio_and_full_consumption():
    z = _zone()
    partial = analyze_consumption(z, executed_volume_into_zone=10.0, zone_liquidity=50.0)
    assert partial.consumption_ratio == pytest.approx(0.2)
    assert not partial.fully_consumed
    full = analyze_consumption(z, executed_volume_into_zone=60.0, zone_liquidity=50.0)
    assert full.fully_consumed


# ----------------------------------------------------------------------
# Sweep classification: rejection vs acceptance
# ----------------------------------------------------------------------


def test_sweep_acceptance_clears_through_the_wall():
    z = _zone(side="ask", lo=102.0, hi=103.0)
    res = classify_sweep(
        z, intrazone_low=101.0, intrazone_high=104.0, close_price=104.0,
        consumed_volume=60.0,
    )
    assert res.kind == SWEEP_ACCEPTANCE
    assert res.direction == "up"


def test_sweep_rejection_settles_back_inside():
    z = _zone(side="ask", lo=102.0, hi=103.0)
    res = classify_sweep(
        z, intrazone_low=101.0, intrazone_high=102.8, close_price=102.5,
        consumed_volume=20.0,
    )
    assert res.kind == SWEEP_REJECTION


def test_no_sweep_without_consumption():
    z = _zone(side="ask", lo=102.0, hi=103.0)
    res = classify_sweep(
        z, intrazone_low=101.0, intrazone_high=104.0, close_price=104.0,
        consumed_volume=0.0,
    )
    assert res.kind == SWEEP_NONE


# ----------------------------------------------------------------------
# Absorption analyzer
# ----------------------------------------------------------------------


def test_absorption_buy_side_quiet():
    # Heavy buying, tiny price move -> sellers absorbed (ask side).
    obs = _obs(bid=50, ask=50, buy=90.0, sell=10.0, price=100.0)
    res = analyze_absorption(obs, price_change=0.02, typical_price_move=0.5)
    assert res.side == "ask"
    assert res.score > 0.0


def test_absorption_sell_side_quiet():
    obs = _obs(bid=50, ask=50, buy=10.0, sell=90.0, price=100.0)
    res = analyze_absorption(obs, price_change=0.02, typical_price_move=0.5)
    assert res.side == "bid"


def test_absorption_none_when_price_moves_with_flow():
    obs = _obs(bid=50, ask=50, buy=90.0, sell=10.0, price=100.0)
    res = analyze_absorption(obs, price_change=0.6, typical_price_move=0.5)
    assert res.side == "none"


# ----------------------------------------------------------------------
# Replenishment analyzer
# ----------------------------------------------------------------------


def test_replenishment_scores_refill():
    z = _zone(replenishment_count=2)
    res = analyze_replenishment(z, consumed_volume=40.0, reappeared_volume=40.0)
    assert res.score > 0.0


def test_replenishment_zero_without_consumption():
    res = analyze_replenishment(_zone(), consumed_volume=0.0, reappeared_volume=10.0)
    assert res.score == 0.0


# ----------------------------------------------------------------------
# Tracker lifecycle over a stream
# ----------------------------------------------------------------------


def test_tracker_creates_persists_and_weakens():
    tracker = ZoneTracker()
    wall = _book(bids=[(99, 1)], asks=[(101, 1), (102, 50), (103, 1)])
    ev1 = tracker.update(wall, [])
    assert any(e.kind == "LiquidityZoneCreated" for e in ev1)
    z = tracker.active_zones[0]
    assert z.side == "ask" and z.persistence_score > 0.0

    # Same wall re-detected -> persistence grows.
    tracker.update(wall, [], reference_price=102.0)
    assert tracker.active_zones[0].persistence_score > z.persistence_score

    # Wall gone from the book -> weakened.
    empty = _book(bids=[(99, 1)], asks=[(104, 1)], off=10)
    ev3 = tracker.update(empty, [], reference_price=103.0)
    assert any(e.kind in ("LiquidityZoneWeakened", "LiquidityZoneInvalidated")
               for e in ev3)


def test_tracker_sweeps_through_a_wall():
    engine = LiquidityEngine(source="ccxt")
    engine.step(_book(bids=[(99, 1)], asks=[(101, 1), (102, 50), (103, 1)]), [])
    # Price clears up through 102 and holds at 105.
    b2 = _book(bids=[(105, 1)], asks=[(106, 1)], off=5)
    trades = (_tick(102.5, 60, Direction.UP, off=5),)
    r = engine.step(b2, trades)
    kinds = [e.kind for e in r.events]
    assert "LiquiditySwept" in kinds
    swept = [z for z in r.zones if z.status == "swept"]
    assert swept and swept[0].sweep_count == 1


# ----------------------------------------------------------------------
# Engine end-to-end + deterministic replay
# ----------------------------------------------------------------------


def test_engine_deterministic_replay():
    steps = [
        (_book(bids=[(99, 1)], asks=[(101, 1), (102, 50), (103, 1)]),
         (_tick(100.5, 5, Direction.UP, off=0),)),
        (_book(bids=[(99, 1)], asks=[(101, 1), (102, 50), (103, 1)], off=1),
         (_tick(102.0, 10, Direction.UP, off=1),)),
        (_book(bids=[(105, 1)], asks=[(106, 1)], off=2),
         (_tick(102.5, 60, Direction.UP, off=2),)),
    ]
    eng1 = LiquidityEngine(source="t")
    out1 = [eng1.step(b, t) for b, t in steps]
    eng2 = LiquidityEngine(source="t")
    out2 = [eng2.step(b, t) for b, t in steps]
    # Same stream -> identical zone lifecycle and event sequence.
    assert [e.kind for r in out1 for e in r.events] == [
        e.kind for r in out2 for e in r.events
    ]
    for r1, r2 in zip(out1, out2):
        assert r1.observation.to_dict() == r2.observation.to_dict()
        assert [z.id for z in r1.zones] == [z.id for z in r2.zones]


def test_engine_no_lookahead_each_step_only_sees_its_inputs():
    # A step's observation must not depend on a later book.
    b1 = _book(bids=[(99, 1)], asks=[(101, 1)])
    b2 = _book(bids=[(50, 1)], asks=[(200, 1)], off=5)
    e = LiquidityEngine(source="t")
    first = e.step(b1, [])
    # The first observation cannot "know" the second book's spread.
    assert first.observation.bid_liquidity == _half_depth([(99, 1)])
    assert first.observation.price == pytest.approx(100.0)


def _half_depth(levels):
    return sum(a for _, a in levels)


# ----------------------------------------------------------------------
# Features
# ----------------------------------------------------------------------


def test_features_shape_and_bounds():
    obs = _obs(bid=20, ask=80, buy=10, sell=0, price=101.5)
    zones = (
        _zone(side="ask", lo=102.0, hi=103.0, liquidity_score=0.9,
              persistence_score=0.7),
        _zone(side="bid", lo=99.0, hi=99.5, liquidity_score=0.3),
    )
    f = extract_features(
        obs, zones, observations_seen=5,
        sweep_up_count=2, sweep_down_count=0,
        absorption_ask=0.4, replenishment_score=0.5,
        consumed_volume=30.0,
    )
    d = f.to_dict()
    assert set(d) >= {
        "nearest_bid_zone_distance", "nearest_ask_zone_distance",
        "bid_liquidity_score", "ask_liquidity_score", "liquidity_imbalance",
        "sweep_up_score", "sweep_down_score", "absorption_bid_score",
        "absorption_ask_score", "replenishment_score", "liquidity_velocity",
        "persistence_score",
    }
    assert 0.0 <= d["sweep_up_score"] <= 1.0
    assert d["ask_liquidity_score"] == 0.9
    assert d["persistence_score"] == 0.7
    assert d["nearest_ask_zone_distance"] is not None


# ----------------------------------------------------------------------
# Service: event emission + persistence + mock honesty
# ----------------------------------------------------------------------


class _StaticBookSource:
    name = "test-book"
    is_mock = False

    def __init__(self, book): self._book = book
    async def order_book(self, instrument, *, depth=10): return self._book


class _StaticTradeSource:
    name = "test-trade"
    is_mock = False

    def __init__(self, ticks): self._ticks = ticks
    async def recent_trades(self, instrument, *, limit=50): return self._ticks


class _NoBookSource:
    name = "no-book"
    is_mock = False
    supports_order_book = False
    async def order_book(self, instrument, *, depth=10):
        raise ProviderError("no books")


@pytest.mark.asyncio
async def test_service_emits_canonical_events_and_persists(tmp_path):
    bus = EventBus()
    seen = []
    async def handler(ev): seen.append(ev)
    for cls in (LiquidityZoneCreated, LiquidityImbalanceChanged):
        await bus.subscribe(cls, handler)

    obs_store = InMemoryObservationStore()
    zone_store = InMemoryZoneStore()
    svc = LiquidityIntelligenceService(
        _StaticBookSource(_book(bids=[(99, 1)], asks=[(101, 1), (102, 50), (103, 1)])),
        _StaticTradeSource((_tick(100.0, 5, Direction.UP),)),
        event_bus=bus, observation_store=obs_store, zone_store=zone_store,
    )
    report = await svc.analyze("BTC/USD")

    assert report.observation is not None
    assert any(isinstance(e, LiquidityZoneCreated) for e in seen)
    assert len(obs_store) == 1
    assert len(zone_store) >= 1
    assert report.features is not None


@pytest.mark.asyncio
async def test_service_replay_emits_events():
    bus = EventBus()
    seen = []
    async def handler(ev): seen.append(ev)
    for cls in (LiquidityZoneCreated, LiquiditySwept, LiquidityConsumed):
        await bus.subscribe(cls, handler)

    svc = LiquidityIntelligenceService(_StaticBookSource(None), event_bus=bus)
    steps = [
        (_book(bids=[(99, 1)], asks=[(101, 1), (102, 50), (103, 1)]),
         (_tick(100.5, 5, Direction.UP),)),
        (_book(bids=[(105, 1)], asks=[(106, 1)], off=5),
         (_tick(102.5, 60, Direction.UP, off=5),)),
    ]
    report = await svc.replay(steps)
    names = {type(e).__name__ for e in seen}
    assert "LiquidityZoneCreated" in names
    assert "LiquiditySwept" in names


@pytest.mark.asyncio
async def test_service_unsupported_book_is_typed_refusal():
    svc = LiquidityIntelligenceService(_NoBookSource())
    with pytest.raises(ProviderError):
        await svc.analyze("BTC/USD")


# ----------------------------------------------------------------------
# Persistence round-trip
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_file_stores_round_trip(tmp_path):
    obs_path = tmp_path / "liquidity" / "observations.jsonl"
    zone_path = tmp_path / "liquidity" / "zones.jsonl"

    obs_store = FileObservationStore(obs_path)
    obs = _obs(bid=60, ask=40)
    await obs_store.record(obs)
    back = await obs_store.list_observations()
    assert len(back) == 1
    assert back[0].imbalance == pytest.approx(obs.imbalance)

    zone_store = FileZoneStore(zone_path)
    z = _zone()
    await zone_store.record(z)
    # Update the same zone id (matured status) -> last line wins.
    matured = LiquidityZone(
        symbol=z.symbol, side=z.side, lower_price=z.lower_price,
        upper_price=z.upper_price, first_seen=z.first_seen,
        last_seen=z.last_seen + timedelta(seconds=5), status="swept",
        sweep_count=1,
    )
    await zone_store.record(matured)
    got = await zone_store.get(z.id)
    assert got.status == "swept"


def test_observation_serialization_round_trip():
    obs = _obs(bid=70.0, ask=30.0, buy=10.0, sell=5.0, mock=True)
    d = obs.to_dict()
    assert d["is_mock"] is True
    back = LiquidityObservation.from_dict(d)
    assert back.executed_buy_volume == 10.0
    assert back.is_mock is True


# ----------------------------------------------------------------------
# ProviderSource adapter honesty
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_source_refuses_unsupported_book():
    class _Prov:
        name = "x"
        is_mock = False
        supports_order_book = False
        supports_trades = False
    src = ProviderSource(_Prov())
    with pytest.raises(ProviderError):
        await src.order_book(_INST, depth=10)
    with pytest.raises(ProviderError):
        await src.recent_trades(_INST, limit=10)
