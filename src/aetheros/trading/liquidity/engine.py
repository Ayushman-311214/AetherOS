"""
The liquidity observation engine.

:class:`LiquidityEngine` is the deterministic heart of the layer: it folds an
ordered stream of ``(order-book snapshot, trade prints)`` steps into
:class:`LiquidityObservation` records, runs the independent analyzers, advances
the :class:`ZoneTracker`, and collects the canonical liquidity events the
service publishes onto the shared bus.

It is deliberately a *replayable* engine rather than a live listener: the same
ordered input always produces the same observations, zones and events. That is
what makes the whole layer backtestable -- feed a recorded historical stream and
you get the identical intelligence a live feed would have produced, with no
look-ahead because every step only ever sees the book and prints *up to* that
step.

The engine returns plain values; publishing to the EventBus and persistence are
the service layer's job, kept out of here so the engine stays pure and unit-
testable without a bus.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.order_book import OrderBook, TradeTick
from .analyzers import (
    AbsorptionResult,
    ImbalanceResult,
    analyze_absorption,
    analyze_imbalance,
)
from .observation import LiquidityObservation
from .tracker import LiquidityZoneEvent, ZoneTracker
from .zone import LiquidityZone

#: Fraction of the book's total depth used to define the "top" resting
#: liquidity an observation reports (top-of-book, not the whole ladder).
_TOP_DEPTH_SHARE = 0.5


@dataclass(frozen=True, slots=True)
class LiquidityStepResult:
    """Everything one engine step produced."""

    observation: LiquidityObservation
    imbalance: ImbalanceResult
    absorption: AbsorptionResult
    zones: tuple[LiquidityZone, ...]
    events: tuple[LiquidityZoneEvent, ...]


class LiquidityEngine:
    """
    Folds an (order-book, trades) stream into observations, zones and events.

    Holds a ``ZoneTracker`` for zone lifecycle state; the rest is recomputed
    per step from the inputs. ``prior_price`` feeds the absorption analyzer the
    window's realised price change -- carried on the engine because it is the
    one piece of state that is genuinely *between* steps (last step's price vs
    this one's).
    """

    def __init__(self, *, source: str = "", persistence_full: int = 10) -> None:
        self._tracker = ZoneTracker(persistence_full=persistence_full)
        self._source = source
        self._prior_price: float | None = None
        self._typical_move: float = 0.0

    @property
    def tracker(self) -> ZoneTracker:
        return self._tracker

    @property
    def zones(self) -> tuple[LiquidityZone, ...]:
        return self._tracker.zones

    # ------------------------------------------------------------------

    def _top_depth(self, book: OrderBook) -> tuple[float, float]:
        """Resting bid/ask liquidity in the top ``_TOP_DEPTH_SHARE`` of the book."""
        def _take(levels):
            total = sum(l.amount for l in levels)
            if total <= 0:
                return 0.0
            target = total * _TOP_DEPTH_SHARE
            acc = 0.0
            for level in levels:
                if acc >= target:
                    break
                acc += level.amount
            return acc
        return _take(book.bids), _take(book.asks)

    def _executed(self, trades: tuple[TradeTick, ...]) -> tuple[float, float]:
        """Buyer- vs seller-initiated volume over the step's prints."""
        buy = sum(t.amount for t in trades if t.side.value == "up")
        sell = sum(t.amount for t in trades if t.side.value == "down")
        return buy, sell

    def step(
        self,
        book: OrderBook,
        trades: tuple[TradeTick, ...] = (),
        *,
        is_mock: bool = False,
    ) -> LiquidityStepResult:
        """
        Advance the engine by one step and return what it produced.

        Only this step's book and prints are read -- nothing after -- so a
        replayed step is look-ahead-free by construction.
        """
        book_mock = is_mock or book.provenance.is_mock
        bid_liq, ask_liq = self._top_depth(book)
        buy_vol, sell_vol = self._executed(trades)
        price = book.mid_price or book.best_bid or book.best_ask or 0.0

        # Realised price change over this step's window (for absorption).
        price_change = (
            price - self._prior_price if self._prior_price is not None else 0.0
        )

        observation = LiquidityObservation(
            symbol=book.instrument.key,
            timestamp=book.timestamp,
            price=price,
            bid_liquidity=bid_liq,
            ask_liquidity=ask_liq,
            executed_buy_volume=buy_vol,
            executed_sell_volume=sell_vol,
            source=self._source or book.provenance.source,
            is_mock=book_mock,
        )

        imbalance = analyze_imbalance(observation)
        absorption = analyze_absorption(
            observation,
            price_change=price_change,
            typical_price_move=self._typical_move,
        )

        zone_events = self._tracker.update(
            book, trades, reference_price=price,
            typical_price_move=self._typical_move,
            prior_price=self._prior_price, is_mock=book_mock,
        )

        # Update the running volatility baseline honestly: a rolling mean of the
        # per-step absolute price move, so absorption is judged against real
        # recent volatility, not a fixed constant.
        move = abs(price_change)
        if self._typical_move <= 0:
            self._typical_move = move
        else:
            self._typical_move = 0.9 * self._typical_move + 0.1 * move
        self._prior_price = price

        # Build flow-level events the service will publish.
        events = list(zone_events)
        if imbalance.is_significant:
            events.append(
                LiquidityZoneEvent(
                    kind="LiquidityImbalanceChanged",
                    zone=self._placeholder_zone(book, observation),
                    timestamp=book.timestamp,
                    instrument_key=book.instrument.key,
                    side=imbalance.dominant_side,
                    price=price,
                    detail=(
                        f"Resting book is {imbalance.dominant_side}-heavy "
                        f"(imbalance {imbalance.imbalance:+.2f})."
                    ),
                    is_mock=book_mock,
                )
            )
        if absorption.side != "none":
            events.append(
                LiquidityZoneEvent(
                    kind="LiquidityAbsorbed",
                    zone=self._placeholder_zone(book, observation),
                    timestamp=book.timestamp,
                    instrument_key=book.instrument.key,
                    side=absorption.side,
                    price=price,
                    volume=absorption.aggressive_volume,
                    detail=absorption.detail,
                    is_mock=book_mock,
                )
            )

        return LiquidityStepResult(
            observation=observation,
            imbalance=imbalance,
            absorption=absorption,
            zones=self._tracker.zones,
            events=tuple(events),
        )

    def _placeholder_zone(self, book, observation) -> LiquidityZone:
        """
        A transient zone-like carrier for non-zone events (imbalance/absorption).

        These events are about the *book as a whole*, not a tracked zone, so a
        lightweight single-level carrier is built purely to satisfy the event's
        ``zone`` field -- it is never tracked and never reused.
        """
        lo = book.best_bid or observation.price
        hi = book.best_ask or observation.price
        if hi <= lo:
            hi = lo + max(1e-9, observation.price * 1e-4)
        return LiquidityZone(
            symbol=book.instrument.key,
            side="bid" if observation.imbalance >= 0 else "ask",
            lower_price=lo,
            upper_price=hi,
            first_seen=book.timestamp,
            last_seen=book.timestamp,
            source=observation.source,
            is_mock=observation.is_mock,
        )
