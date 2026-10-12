"""
Order-book / tape liquidity intelligence (Phase 2).

This package holds the canonical *microstructure* liquidity layer: observations
built from order-book snapshots and executed-trade prints, the zones resting
liquidity clusters into, and the events a change in that liquidity announces.

It is deliberately separate from the candle-based ``LiquidityService`` /
``LiquidityAnalysis`` (which reads a volume-*at-price* profile off OHLCV bars)
and from the SMC price-action ``LiquidityEvent`` (a swing sweep on bars). Those
answer "where did volume trade" and "did price take a level"; this answers
"where is resting and aggressive liquidity right now, and what is it doing".
The two vocabularies are kept distinct so neither is silently overloaded
(CLAUDE.md sections 9, 22).

Everything here is a pure, deterministic function of the order-book and trade
stream it is handed -- no I/O, no LLM, and no wall-clock reads inside an
analyzer, so the same historical input always replays to the same observations,
zones, events and features (the backtestable-design requirement).

Honesty: an observation can only assert what its source snapshot/prints
actually contained. ``is_mock`` is surfaced on every record, and a zone's
``status`` reports what happened to it (touched / swept / invalidated) rather
than guessing what it *means*.
"""

from __future__ import annotations

from .engine import LiquidityEngine, LiquidityStepResult
from .features import LiquidityFeatures, extract_features
from .observation import LiquidityObservation
from .persistence import (
    FileObservationStore,
    FileZoneStore,
    InMemoryObservationStore,
    InMemoryZoneStore,
    ObservationStore,
    ZoneStore,
)
from .service import LiquidityIntelligenceService, LiquidityReport
from .sources import (
    CandleSource,
    MarketDataSource,
    OrderBookSource,
    ProviderSource,
    TradeSource,
)
from .tracker import LiquidityZoneEvent, ZoneTracker
from .zone import LiquidityZone

__all__ = [
    "CandleSource",
    "FileObservationStore",
    "FileZoneStore",
    "InMemoryObservationStore",
    "InMemoryZoneStore",
    "LiquidityEngine",
    "LiquidityFeatures",
    "LiquidityIntelligenceService",
    "LiquidityObservation",
    "LiquidityReport",
    "LiquidityStepResult",
    "LiquidityZone",
    "LiquidityZoneEvent",
    "MarketDataSource",
    "ObservationStore",
    "OrderBookSource",
    "ProviderSource",
    "TradeSource",
    "ZoneStore",
    "ZoneTracker",
    "extract_features",
]
