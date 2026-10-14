"""
The zone tracker: liquidity-zone lifecycle over a replayed stream.

``detect_zones`` is stateless -- it finds resting-liquidity clusters on one
snapshot. :class:`ZoneTracker` is what carries them *across* snapshots: it
reconciles each new detection with the zones it already tracks, ageing them by
what price and the tape actually do -- touches, sweeps, replenishments,
weakening, invalidation. It is the component that turns a flash of big orders
into a *persisting* zone (or exposes one that vanished).

Determinism is structural: the tracker holds state, but that state is a pure
function of the ordered input stream. Feed two trackers the same
``(book, trades)`` steps and they reach identical zones, scores and event
sequences -- there is no wall-clock, no randomness, and every timestamp a zone
records comes from the stream, never from ``datetime.now()``.

The events it emits are value objects (``LiquidityZoneEvent``) describing what
changed; the service layer publishes them onto the shared bus.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..domain.order_book import OrderBook, TradeTick
from .analyzers import (
    SWEEP_ACCEPTANCE,
    SWEEP_REJECTION,
    classify_sweep,
    detect_zones,
)
from .zone import (
    ZONE_ACTIVE,
    ZONE_INVALIDATED,
    ZONE_SWEPT,
    ZONE_TOUCHED,
    LiquidityZone,
)

#: Persistence saturates once a zone has been seen in this many snapshots.
_PERSISTENCE_FULL = 10

#: A zone is invalidated when its resting liquidity drops below this fraction
#: of what it showed at formation (the wall dissolved on its own).
_INVALIDATE_LIQUIDITY_DROP = 0.25

#: A zone's resting liquidity is treated as "replenished" when, after a sweep,
#: it climbs back to at least this fraction of its prior size.
_REPLENISH_FRACTION = 0.5


@dataclass(frozen=True, slots=True)
class LiquidityZoneEvent:
    """
    A lifecycle change to one tracked zone.

    ``kind`` is one of the canonical zone events (created / weakened /
    invalidated, plus appeared / removed / replenished / consumed / swept /
    absorbed for the flow-level changes). ``zone`` is the zone *after* the
    change; ``detail`` carries the supporting numbers so a consumer never has
    to recompute them. ``timestamp`` is the stream time, not the wall clock.
    """

    kind: str
    zone: LiquidityZone
    timestamp: datetime
    instrument_key: str
    side: str
    detail: str = ""
    price: float | None = None
    volume: float | None = None
    liquidity_score: float = 0.0
    persistence_score: float = 0.0
    is_mock: bool = False

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "zone": self.zone.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "instrument_key": self.instrument_key,
            "side": self.side,
            "detail": self.detail,
            "price": self.price,
            "volume": self.volume,
            "liquidity_score": self.liquidity_score,
            "persistence_score": self.persistence_score,
            "is_mock": self.is_mock,
        }


@dataclass(slots=True)
class TrackedZone:
    """
    A zone plus the running liquidity the tracker remembers about it.

    Deliberately *not* frozen: the zone's lifecycle (touches, sweeps, weakening)
    and its running liquidity are mutated as the stream advances. Only the
    ``LiquidityZone`` it wraps stays immutable -- each mutation rebuilds it via
    ``_rebuild`` and swaps the reference, so a zone value a caller holds is
    never silently mutated under them.
    """

    zone: LiquidityZone
    seen_snapshots: int
    reference_liquidity: float   # size at formation (for drop/replenish math)
    current_liquidity: float     # size at the most recent snapshot
    was_swept: bool = False


class ZoneTracker:
    """
    Maintains liquidity zones across an ordered snapshot/trade stream.

    Stateful by necessity (a zone's persistence *is* accumulated state), but a
    pure function of its input: ``update`` is deterministic given the same
    sequence of ``(book, trades)`` steps. No clocks, no randomness.
    """

    def __init__(
        self,
        *,
        merge_gap_ratio: float = None,
        persistence_full: int = _PERSISTENCE_FULL,
    ) -> None:
        self._zones: dict[str, TrackedZone] = {}
        self._persistence_full = max(1, persistence_full)

    @property
    def zones(self) -> tuple[LiquidityZone, ...]:
        """All currently tracked zones (active and resolved)."""
        return tuple(tracked.zone for tracked in self._zones.values())

    @property
    def active_zones(self) -> tuple[LiquidityZone, ...]:
        return tuple(z for z in self.zones if z.is_active)

    def _key(self, zone: LiquidityZone) -> str:
        return zone.id

    def _find_overlap(
        self, side: str, lower: float, upper: float
    ) -> TrackedZone | None:
        """The active tracked zone on this side overlapping a new band."""
        for tracked in self._zones.values():
            z = tracked.zone
            if not z.is_active or z.side != side:
                continue
            if not (z.lower_price > upper or lower > z.upper_price):
                return tracked
        return None

    def update(
        self,
        book: OrderBook,
        trades: tuple[TradeTick, ...] = (),
        *,
        reference_price: float | None = None,
        typical_price_move: float = 0.0,
        prior_price: float | None = None,
        is_mock: bool = False,
    ) -> tuple[LiquidityZoneEvent, ...]:
        """
        Advance the tracker by one observation step.

        ``book`` is the order-book snapshot at this step, ``trades`` the prints
        that arrived since the previous step. ``reference_price`` is the price
        the step is read against (mid price by default). ``prior_price`` is the
        previous step's reference price -- the window's start, needed so a sweep
        *through* a thin zone (price crossing from one side to past its far
        edge) is detected rather than missed by a single in-band point.
        ``typical_price_move`` is the volatility baseline. Returns the zone
        events this step produced, oldest-cause first.
        """
        ts = book.timestamp
        key = book.instrument.key
        price = reference_price if reference_price is not None else (
            book.mid_price or (book.best_bid or book.best_ask or 0.0)
        )

        events: list[LiquidityZoneEvent] = []
        detected = detect_zones(book)

        # ---- 1. Reconcile detected clusters with tracked zones ----
        matched_ids: set[str] = set()
        for cluster in detected:
            existing = self._find_overlap(
                cluster.side, cluster.lower_price, cluster.upper_price
            )
            if existing is not None:
                matched_ids.add(existing.zone.id)
                ev = self._refresh_zone(
                    existing, cluster, ts, key, is_mock
                )
                events.extend(ev)
            else:
                tracked, ev = self._create_zone(
                    cluster, book, ts, key, is_mock
                )
                self._zones[tracked.zone.id] = tracked
                matched_ids.add(tracked.zone.id)  # seen this step -- never weaken
                events.append(ev)

        # ---- 2. Age / weaken zones not seen this step ----
        for zid, tracked in list(self._zones.items()):
            if zid in matched_ids or not tracked.zone.is_active:
                continue
            events.extend(self._weaken_or_expire(tracked, ts, key, is_mock))

        # ---- 3. Price interaction: touches, sweeps ----
        events.extend(
            self._apply_price_interaction(
                book, trades, price, ts, key, is_mock, prior_price=prior_price
            )
        )

        return tuple(events)

    # ------------------------------------------------------------------
    # Zone lifecycle
    # ------------------------------------------------------------------

    def _create_zone(
        self, cluster, book, ts, key, is_mock
    ) -> tuple[TrackedZone, LiquidityZoneEvent]:
        side_total = (
            sum(l.amount for l in book.bids)
            if cluster.side == "bid"
            else sum(l.amount for l in book.asks)
        )
        liquidity_score = (
            cluster.liquidity / side_total if side_total > 0 else 0.0
        )
        zone = LiquidityZone(
            symbol=key,
            side=cluster.side,
            lower_price=cluster.lower_price,
            upper_price=cluster.upper_price,
            liquidity_score=round(min(1.0, liquidity_score), 4),
            persistence_score=round(1.0 / self._persistence_full, 4),
            first_seen=ts,
            last_seen=ts,
            status=ZONE_ACTIVE,
            source=book.provenance.source,
            is_mock=is_mock or book.provenance.is_mock,
        )
        tracked = TrackedZone(
            zone=zone,
            seen_snapshots=1,
            reference_liquidity=cluster.liquidity,
            current_liquidity=cluster.liquidity,
        )
        event = LiquidityZoneEvent(
            kind="LiquidityZoneCreated",
            zone=zone,
            timestamp=ts,
            instrument_key=key,
            side=zone.side,
            price=(zone.lower_price + zone.upper_price) / 2.0,
            detail=(
                f"New {cluster.side}-side liquidity cluster "
                f"[{cluster.lower_price}, {cluster.upper_price}] holding "
                f"{cluster.liquidity:.2f} across {cluster.level_count} level(s)."
            ),
            liquidity_score=zone.liquidity_score,
            persistence_score=zone.persistence_score,
            is_mock=zone.is_mock,
        )
        return tracked, event

    def _refresh_zone(self, tracked, cluster, ts, key, is_mock):
        """Re-detected: update liquidity, persistence, and check replenishment."""
        events = []
        z = tracked.zone
        tracked.seen_snapshots += 1
        prior_liq = tracked.current_liquidity
        tracked.current_liquidity = cluster.liquidity
        tracked.reference_liquidity = max(
            tracked.reference_liquidity, cluster.liquidity
        )
        persistence = min(1.0, tracked.seen_snapshots / self._persistence_full)

        # Replenishment: liquidity climbed back after being swept/consumed.
        if tracked.was_swept and cluster.liquidity >= (
            prior_liq + tracked.reference_liquidity * _REPLENISH_FRACTION
        ):
            tracked.was_swept = False
            z = self._rebuild(
                z,
                replenishment_count=z.replenishment_count + 1,
                last_seen=ts,
                persistence_score=round(persistence, 4),
            )
            tracked.zone = z
            events.append(
                LiquidityZoneEvent(
                    kind="LiquidityReplenished",
                    zone=z,
                    timestamp=ts,
                    instrument_key=key,
                    side=z.side,
                    price=z.midpoint,
                    detail=(
                        f"Resting liquidity reappeared at the "
                        f"{z.side} wall after consumption."
                    ),
                    liquidity_score=z.liquidity_score,
                    persistence_score=z.persistence_score,
                    is_mock=z.is_mock,
                )
            )
            return events

        tracked.zone = self._rebuild(
            z, last_seen=ts, persistence_score=round(persistence, 4)
        )
        return events

    def _weaken_or_expire(self, tracked, ts, key, is_mock):
        """A zone absent from this snapshot: weakened or invalidated."""
        z = tracked.zone
        drop = (
            1.0 - (tracked.current_liquidity / tracked.reference_liquidity)
            if tracked.reference_liquidity > 0
            else 1.0
        )
        if drop >= (1.0 - _INVALIDATE_LIQUIDITY_DROP):
            new = self._rebuild(z, status=ZONE_INVALIDATED, last_seen=ts)
            tracked.zone = new
            return [
                LiquidityZoneEvent(
                    kind="LiquidityZoneInvalidated",
                    zone=new,
                    timestamp=ts,
                    instrument_key=key,
                    side=z.side,
                    price=z.midpoint,
                    detail=(
                        f"{z.side}-side wall at {z.midpoint:.2f} dissolved: "
                        f"resting liquidity fell to "
                        f"{tracked.current_liquidity:.2f} of "
                        f"{tracked.reference_liquidity:.2f}."
                    ),
                    liquidity_score=new.liquidity_score,
                    persistence_score=new.persistence_score,
                    is_mock=new.is_mock,
                )
            ]
        new = self._rebuild(z, status=z.status, last_seen=ts)
        tracked.zone = new
        return [
            LiquidityZoneEvent(
                kind="LiquidityZoneWeakened",
                zone=new,
                timestamp=ts,
                instrument_key=key,
                side=z.side,
                price=z.midpoint,
                detail=(
                    f"{z.side}-side wall at {z.midpoint:.2f} faded from the "
                    f"latest book."
                ),
                liquidity_score=new.liquidity_score,
                persistence_score=new.persistence_score,
                is_mock=new.is_mock,
            )
        ]

    def _apply_price_interaction(
        self, book, trades, price, ts, key, is_mock, prior_price=None
    ):
        """Touches and sweeps, from where price sat vs each active zone."""
        events = []
        # Price range over this step: the executed prints, the mid, and the
        # previous step's price -- a sweep *through* a thin zone is detected only
        # if the window includes where price came from, so a print that crosses
        # the band from below to above is caught (a single point in the band is
        # easy to straddle in one step and never contains a zone point).
        prices = [t.price for t in trades] + [price]
        if prior_price is not None:
            prices.append(prior_price)
        lo = min(prices)
        hi = max(prices)
        for zid, tracked in list(self._zones.items()):
            z = tracked.zone
            if not z.is_active:
                continue
            touched = z.lower_price <= hi and lo <= z.upper_price
            if not touched:
                continue
            # Executed volume that traded into the band -- a print strictly
            # inside the zone -- PLUS the aggressive flow that drove a clear
            # sweep *through* it (price crossed the far edge, which means the
            # wall was consumed even where no print landed exactly inside).
            in_band = sum(t.amount for t in trades if z.contains(t.price))
            if z.side == "ask":
                through = hi > z.upper_price
                driver = sum(
                    t.amount for t in trades
                    if t.price > z.upper_price or t.side.value == "up"
                )
            else:
                through = lo < z.lower_price
                driver = sum(
                    t.amount for t in trades
                    if t.price < z.lower_price or t.side.value == "down"
                )
            consumed = max(in_band, driver if through else 0.0)
            new_touch = z.touch_count + 1
            sweep = classify_sweep(
                z,
                intrazone_low=lo,
                intrazone_high=hi,
                close_price=price,
                consumed_volume=consumed,
            )
            if sweep.kind in (SWEEP_REJECTION, SWEEP_ACCEPTANCE):
                tracked.was_swept = True
                new = self._rebuild(
                    z,
                    touch_count=new_touch,
                    sweep_count=z.sweep_count + 1,
                    last_seen=ts,
                    status=(ZONE_SWEPT if sweep.kind == SWEEP_ACCEPTANCE else ZONE_TOUCHED),
                )
                tracked.zone = new
                events.append(
                    LiquidityZoneEvent(
                        kind=(
                            "LiquiditySwept"
                            if sweep.kind == SWEEP_ACCEPTANCE
                            else "LiquidityAbsorbed"
                        ),
                        zone=new,
                        timestamp=ts,
                        instrument_key=key,
                        side=z.side,
                        price=price,
                        volume=consumed,
                        detail=sweep.detail,
                        liquidity_score=new.liquidity_score,
                        persistence_score=new.persistence_score,
                        is_mock=new.is_mock,
                    )
                )
            else:
                new = self._rebuild(
                    z, touch_count=new_touch, last_seen=ts, status=ZONE_TOUCHED
                )
                tracked.zone = new
                events.append(
                    LiquidityZoneEvent(
                        kind="LiquidityConsumed",
                        zone=new,
                        timestamp=ts,
                        instrument_key=key,
                        side=z.side,
                        price=price,
                        volume=consumed,
                        detail=(
                            f"Price traded into the {z.side} wall at "
                            f"{z.midpoint:.2f}; {consumed:.2f} consumed."
                        ),
                        liquidity_score=new.liquidity_score,
                        persistence_score=new.persistence_score,
                        is_mock=new.is_mock,
                    )
                )
        return events

    @staticmethod
    def _rebuild(zone: LiquidityZone, **changes) -> LiquidityZone:
        """Return a new LiquidityZone with selected fields updated."""
        data = {
            "id": zone.id,
            "symbol": zone.symbol,
            "side": zone.side,
            "lower_price": zone.lower_price,
            "upper_price": zone.upper_price,
            "liquidity_score": zone.liquidity_score,
            "persistence_score": zone.persistence_score,
            "first_seen": zone.first_seen,
            "last_seen": zone.last_seen,
            "touch_count": zone.touch_count,
            "sweep_count": zone.sweep_count,
            "replenishment_count": zone.replenishment_count,
            "status": zone.status,
            "source": zone.source,
            "is_mock": zone.is_mock,
        }
        data.update(changes)
        return LiquidityZone(**data)
