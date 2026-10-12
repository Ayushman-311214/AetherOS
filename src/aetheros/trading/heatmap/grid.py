"""
The time x price grid builder -- the single shared engine under all six views.

:class:`HeatmapGrid` accumulates an ordered liquidity stream (observations,
zones and the lifecycle events the engine emits) into a bounded, configurable
grid of ``HeatmapCell`` bins. One grid feeds every view; the views differ only
in which cell quantity becomes the intensity channel, so binning, aggregation,
normalisation and look-ahead-safety live in exactly one place.

Two hard requirements drive the design:

* **Bounded memory.** The grid is a fixed-resolution matrix over a rolling
  window. Adding a step writes into existing bins or evicts the oldest
  time-bucket; it never grows without bound. ``capacity`` caps the number of
  live time-buckets, so a long replay cannot exhaust RAM.
* **Look-ahead-free.** ``update`` reads only the step it is handed (one
  observation, the zones/events it produced). A bin's value at step *t* is a
  pure function of steps ``<= t`` -- feeding a recorded stream reproduces
  exactly the grid a live feed would have shown.

Binning is honest: a bin is labelled by its *start* time and *lower* price, so
the cell's own ``timestamp``/``price`` always round-trip to the same bin --
never silently shifted by the bucket size.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import replace
from datetime import datetime

from ..liquidity.observation import LiquidityObservation
from ..liquidity.tracker import LiquidityZoneEvent
from ..liquidity.zone import LiquidityZone
from .cell import HeatmapCell


def _bucket_time(ts: datetime, bucket_seconds: float) -> datetime:
    """Floor ``ts`` to its bucket boundary (UTC-epoch aligned)."""
    epoch = ts.timestamp()
    start = math.floor(epoch / bucket_seconds) * bucket_seconds
    return datetime.fromtimestamp(start, tz=ts.tzinfo)


def _bucket_price(price: float, price_step: float) -> float:
    """Floor ``price`` to its price-bin boundary."""
    return math.floor(price / price_step) * price_step


class HeatmapGrid:
    """
    A bounded, incremental time x price grid of ``HeatmapCell`` bins.

    ``price_step`` sets the vertical resolution (size of one price bin);
    ``bucket_seconds`` sets the horizontal resolution (size of one time bin);
    ``capacity`` caps how many distinct time-buckets are retained -- once full,
    the oldest bucket is evicted (a rolling window, never unbounded RAM).

    The grid is a pure function of the stream fed to it. It holds no wall clock
    and no randomness; two grids fed the same ordered steps reach identical
    cells.
    """

    def __init__(
        self,
        *,
        price_step: float,
        bucket_seconds: float,
        capacity: int = 256,
        symbol: str = "",
    ) -> None:
        if price_step <= 0:
            raise ValueError("price_step must be positive.")
        if bucket_seconds <= 0:
            raise ValueError("bucket_seconds must be positive.")
        if capacity <= 0:
            raise ValueError("capacity must be positive.")
        self._price_step = float(price_step)
        self._bucket_seconds = float(bucket_seconds)
        self._capacity = int(capacity)
        self._symbol = symbol
        # Ordered (newest at end) so eviction drops the oldest time-bucket.
        self._cells: OrderedDict[tuple[datetime, float], HeatmapCell] = (
            OrderedDict()
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def price_step(self) -> float:
        return self._price_step

    @property
    def bucket_seconds(self) -> float:
        return self._bucket_seconds

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def cell_count(self) -> int:
        return len(self._cells)

    @property
    def cells(self) -> tuple[HeatmapCell, ...]:
        """All live cells, oldest-bucket first (deterministic order)."""
        return tuple(self._cells.values())

    def time_buckets(self) -> int:
        """How many distinct time-buckets are currently retained."""
        return len({key[0] for key in self._cells})

    # ------------------------------------------------------------------
    # Incremental update
    # ------------------------------------------------------------------

    def update(
        self,
        observation: LiquidityObservation,
        *,
        zones: tuple[LiquidityZone, ...] = (),
        events: tuple[LiquidityZoneEvent, ...] = (),
    ) -> None:
        """
        Fold one engine step into the grid.

        The observation's own resting/executed volumes aggregate into the cell
        at its (time, price) bin; zones contribute persistence and resting size
        to the bins their bands cover; lifecycle events land their score on the
        bin they happened in. Only this step's data is read -- never a future
        one.
        """
        ts = observation.timestamp
        tbucket = _bucket_time(ts, self._bucket_seconds)

        # The cell the observation's reference price sits in.
        pbin = _bucket_price(observation.price, self._price_step)
        self._accumulate(
            tbucket,
            pbin,
            bid=observation.bid_liquidity,
            ask=observation.ask_liquidity,
            buy=observation.executed_buy_volume,
            sell=observation.executed_sell_volume,
            pressure=self._pressure(observation),
            mock=observation.is_mock,
            samples=1,
        )

        # Zones paint their persistence + resting share onto the bins they span.
        for zone in zones:
            if not zone.is_active:
                continue
            self._paint_zone(tbucket, zone)

        # Lifecycle events score onto the bin at the event's price.
        for ev in events:
            self._score_event(tbucket, ev)

        self._enforce_capacity()

    def _accumulate(
        self,
        tbucket: datetime,
        pbin: float,
        *,
        bid: float = 0.0,
        ask: float = 0.0,
        buy: float = 0.0,
        sell: float = 0.0,
        persistence: float = 0.0,
        consumption: float = 0.0,
        replenishment: float = 0.0,
        sweep: float = 0.0,
        absorption: float = 0.0,
        pressure: float = 0.0,
        mock: bool = False,
        samples: int = 0,
    ) -> None:
        key = (tbucket, pbin)
        cell = self._cells.get(key)
        if cell is None:
            cell = HeatmapCell(
                timestamp=tbucket.isoformat(),
                price=pbin,
                time_span_seconds=self._bucket_seconds,
                price_span=self._price_step,
                is_mock=mock,
            )
            self._cells[key] = cell
        else:
            self._cells.move_to_end(key)
        self._cells[key] = replace(
            cell,
            bid_intensity=cell.bid_intensity + bid,
            ask_intensity=cell.ask_intensity + ask,
            executed_buy_volume=cell.executed_buy_volume + buy,
            executed_sell_volume=cell.executed_sell_volume + sell,
            # Derived scores take the max (the strongest signal seen in the bin),
            # never a sum -- a score is a level, not an accumulation.
            persistence=max(cell.persistence, persistence),
            consumption=max(cell.consumption, consumption),
            replenishment=max(cell.replenishment, replenishment),
            sweep_score=max(cell.sweep_score, sweep),
            absorption_score=max(cell.absorption_score, absorption),
            pressure_score=max(cell.pressure_score, pressure),
            sample_count=cell.sample_count + samples,
            is_mock=cell.is_mock or mock,
        )

    def _paint_zone(self, tbucket: datetime, zone: LiquidityZone) -> None:
        """Paint a live zone's persistence + resting size onto its covered bins."""
        lo = _bucket_price(zone.lower_price, self._price_step)
        hi = _bucket_price(zone.upper_price, self._price_step)
        step = self._price_step
        p = lo
        while p <= hi + 1e-9:
            # A bid zone shows as resting support; an ask zone as resting supply.
            self._accumulate(
                tbucket,
                p,
                bid=zone.liquidity_score if zone.side == "bid" else 0.0,
                ask=zone.liquidity_score if zone.side == "ask" else 0.0,
                persistence=zone.persistence_score,
                mock=zone.is_mock,
            )
            p = round(p + step, 10)

    def _score_event(self, tbucket: datetime, ev: LiquidityZoneEvent) -> None:
        """Land a lifecycle event's score on the bin at its price."""
        price = ev.price if ev.price is not None else ev.zone.midpoint
        pbin = _bucket_price(price, self._price_step)
        scores = {
            "LiquiditySwept": {"sweep": 1.0},
            "LiquidityAbsorbed": {"absorption": 0.7, "sweep": 0.4},
            "LiquidityConsumed": {"consumption": 0.6},
            "LiquidityReplenished": {"replenishment": 0.8},
            "LiquidityZoneCreated": {"persistence": ev.persistence_score},
            "LiquidityZoneWeakened": {"consumption": 0.3},
            "LiquidityZoneInvalidated": {"consumption": 0.9},
        }.get(ev.kind)
        if scores is None:
            return
        self._accumulate(
            tbucket,
            pbin,
            sweep=scores.get("sweep", 0.0),
            absorption=scores.get("absorption", 0.0),
            consumption=scores.get("consumption", 0.0),
            replenishment=scores.get("replenishment", 0.0),
            persistence=scores.get("persistence", 0.0),
            mock=ev.is_mock,
        )

    @staticmethod
    def _pressure(observation: LiquidityObservation) -> float:
        """
        A derived 0..1 market-pressure read for one observation.

        Combines the resting imbalance and the aggressive net flow, both in
        [-1,1], into a single unsigned pressure magnitude. The formula is a
        documented heuristic -- NOT a calibrated statistic: pressure is simply
        the larger of the resting lean and the executed lean, blended toward
        whichever side is doing more work. It is honest about being a derived,
        descriptive quantity, not a validated probability.
        """
        resting = observation.imbalance     # -1..1
        flow = observation.net_flow         # -1..1
        # Unsigned magnitude of the dominant push, averaged: a market leaning
        # AND flowing the same way pressures harder than one pulling apart.
        magnitude = (abs(resting) + abs(flow)) / 2.0
        return round(min(1.0, magnitude), 4)

    # ------------------------------------------------------------------
    # Bounded retention
    # ------------------------------------------------------------------

    def _enforce_capacity(self) -> None:
        """
        Evict the oldest time-bucket(s) once the time-window is full.

        ``_cells`` is insertion-ordered with the newest bucket at the end, so
        the oldest buckets sit at the front. This pops leading entries until
        the number of distinct retained buckets is back within ``capacity`` --
        a rolling window, never unbounded growth.
        """
        while True:
            buckets = {k[0] for k in self._cells}
            if len(buckets) <= self._capacity:
                return
            oldest = min(buckets)
            self._cells = OrderedDict(
                (k, v) for k, v in self._cells.items() if k[0] != oldest
            )

    def clear(self) -> None:
        self._cells.clear()
