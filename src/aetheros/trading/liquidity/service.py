"""
Liquidity-intelligence service (Phase 2).

The orchestration point that ties the whole layer together without holding any
analytical logic itself (the engine/trackers/analyzers own that). For a given
instrument it pulls an ordered ``(order-book, trades)`` stream through the
injected sources, replays it through a :class:`LiquidityEngine`, and:

* publishes every lifecycle/flow change as a canonical ``LiquidityEvent``
  subclass on the shared ``EventBus``,
* persists each ``LiquidityObservation`` and zone update through the injected
  stores (optional -- the service works identically with them absent),
* returns the latest observation, live zones and the feature vector.

It never fabricates: a source that cannot serve books or trades raises a typed
error, and a publish/store failure is logged and swallowed so a side-effect can
never break the read. ``is_mock`` is stamped on every record so a synthetic book
can never read as a real wall.
"""

from __future__ import annotations

from dataclasses import dataclass

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.instrument import Instrument
from ..domain.order_book import OrderBook
from ..errors import InvalidSymbolError, MarketDataError
from ..events import LIQUIDITY_EVENT_TYPES
from .engine import LiquidityEngine, LiquidityStepResult
from .features import LiquidityFeatures, extract_features
from .observation import LiquidityObservation
from .persistence import ObservationStore, ZoneStore
from .sources import OrderBookSource, TradeSource
from .tracker import LiquidityZoneEvent
from .zone import LiquidityZone

logger = get_logger("trading.liquidity.service")


@dataclass(frozen=True, slots=True)
class LiquidityReport:
    """The service's read for one instrument: observation + zones + features."""

    observation: LiquidityObservation | None
    zones: tuple[LiquidityZone, ...]
    features: LiquidityFeatures | None
    events_emitted: int
    is_mock: bool = False

    def to_dict(self) -> dict:
        return {
            "observation": (
                self.observation.to_dict() if self.observation else None
            ),
            "zones": [z.to_dict() for z in self.zones],
            "features": self.features.to_dict() if self.features else None,
            "events_emitted": self.events_emitted,
            "is_mock": self.is_mock,
        }


class LiquidityIntelligenceService:
    """
    Drives the liquidity engine over a source-fetched stream.

    Holds no analytical logic -- it sequences fetches, feeds the engine, and
    fans the results out to the bus and the stores. ``engine_factory`` lets a
    caller inject a fresh engine per run (default: one per call), keeping the
    service itself stateless and deterministic.
    """

    def __init__(
        self,
        order_book_source: OrderBookSource,
        trade_source: TradeSource | None = None,
        *,
        event_bus: EventBus | None = None,
        observation_store: ObservationStore | None = None,
        zone_store: ZoneStore | None = None,
    ) -> None:
        self._books = order_book_source
        self._trades = trade_source
        self._event_bus = event_bus
        self._obs_store = observation_store
        self._zone_store = zone_store

    @staticmethod
    def _coerce_instrument(symbol: str | Instrument) -> Instrument:
        if isinstance(symbol, Instrument):
            return symbol
        try:
            return Instrument.parse(symbol)
        except ValueError as exc:
            raise InvalidSymbolError(
                f"Cannot resolve instrument '{symbol}' for liquidity analysis.",
                context={"symbol": symbol},
                cause=exc,
            ) from exc

    async def analyze(
        self,
        symbol: str | Instrument,
        *,
        depth: int = 10,
        trade_limit: int = 50,
    ) -> LiquidityReport:
        """
        Pull one (book, trades) step for the instrument and return the read.

        Fetches the order book (required -- a source that cannot serve books is
        a typed refusal) and, when a trade source is wired, the recent prints.
        Replays the step through a fresh engine, publishes the events it
        produced, persists the observation + zones, and returns the report.
        """
        instrument = self._coerce_instrument(symbol)
        try:
            book = await self._books.order_book(instrument, depth=depth)
        except (MarketDataError, InvalidSymbolError):
            raise
        except Exception as exc:
            raise MarketDataError(
                f"Order-book source '{self._books.name}' failed for "
                f"{instrument.key}.",
                context={"symbol": instrument.symbol},
                cause=exc,
            ) from exc

        trades: tuple = ()
        if self._trades is not None:
            try:
                trades = await self._trades.recent_trades(
                    instrument, limit=trade_limit
                )
            except Exception:
                # Missing tape is honest "no flow", not a failure of the read.
                logger.debug("Trade source unavailable; continuing without tape.")
                trades = ()

        return await self._replay(book, trades)

    async def replay(
        self,
        steps: list[tuple[OrderBook, tuple]],
        *,
        is_mock: bool = False,
    ) -> LiquidityReport:
        """
        Replay a recorded ``(book, trades)`` stream deterministically.

        This is the backtestable path: feed a historical stream and get the
        identical observations, zones, events and features a live feed would
        have produced. Each step only sees data up to itself -- no look-ahead.
        """
        engine = LiquidityEngine()
        last: LiquidityStepResult | None = None
        emitted = 0
        for book, trades in steps:
            last = engine.step(book, tuple(trades or ()), is_mock=is_mock)
            emitted += await self._publish_and_persist(last)
        return self._report(engine, last, emitted)

    async def _replay(
        self, book: OrderBook, trades: tuple
    ) -> LiquidityReport:
        engine = LiquidityEngine()
        last = engine.step(book, trades)
        emitted = await self._publish_and_persist(last)
        return self._report(engine, last, emitted)

    # ------------------------------------------------------------------
    # Fan-out
    # ------------------------------------------------------------------

    async def _publish_and_persist(self, step: LiquidityStepResult) -> int:
        """Publish every event the step produced and persist observation+zones."""
        emitted = 0
        for zone_event in step.events:
            if await self._publish(zone_event):
                emitted += 1
        await self._persist_observation(step.observation)
        for zone in step.zones:
            await self._persist_zone(zone)
        return emitted

    async def _publish(self, zone_event: LiquidityZoneEvent) -> bool:
        """Publish one zone event as its canonical ``LiquidityEvent`` subclass."""
        if self._event_bus is None:
            return False
        cls = LIQUIDITY_EVENT_TYPES.get(zone_event.kind)
        if cls is None:
            logger.warning(f"Unknown liquidity event kind '{zone_event.kind}'.")
            return False
        z = zone_event.zone
        event = cls(
            instrument_key=zone_event.instrument_key,
            side=zone_event.side,
            zone_id=z.id,
            lower_price=z.lower_price,
            upper_price=z.upper_price,
            price=zone_event.price,
            volume=zone_event.volume,
            liquidity_score=zone_event.liquidity_score,
            persistence_score=zone_event.persistence_score,
            detail=zone_event.detail,
            source_tier=z.source,
            is_mock=zone_event.is_mock,
        )
        try:
            await self._event_bus.publish(event)
            return True
        except Exception:
            logger.exception(f"Failed to publish {zone_event.kind}")
            return False

    async def _persist_observation(self, observation) -> None:
        if self._obs_store is None:
            return
        try:
            await self._obs_store.record(observation)
        except Exception:
            logger.exception("Failed to persist a liquidity observation.")

    async def _persist_zone(self, zone) -> None:
        if self._zone_store is None:
            return
        try:
            await self._zone_store.record(zone)
        except Exception:
            logger.exception("Failed to persist a liquidity zone.")

    def _report(
        self, engine: LiquidityEngine, last, emitted: int
    ) -> LiquidityReport:
        if last is None:
            return LiquidityReport(
                observation=None, zones=(), features=None, events_emitted=0
            )
        obs = last.observation
        zones = engine.zones
        # Running counters the feature vector is normalised against.
        sweeps_up = sum(
            1 for z in zones if z.side == "ask" for _ in range(z.sweep_count)
        )
        sweeps_down = sum(
            1 for z in zones if z.side == "bid" for _ in range(z.sweep_count)
        )
        features = extract_features(
            obs,
            zones,
            observations_seen=1,
            sweep_up_count=sweeps_up,
            sweep_down_count=sweeps_down,
            absorption_bid=last.absorption.score
            if last.absorption.side == "bid"
            else 0.0,
            absorption_ask=last.absorption.score
            if last.absorption.side == "ask"
            else 0.0,
            replenishment_score=max(
                (z.persistence_score for z in zones if z.is_active), default=0.0
            ),
        )
        return LiquidityReport(
            observation=obs,
            zones=zones,
            features=features,
            events_emitted=emitted,
            is_mock=obs.is_mock,
        )
