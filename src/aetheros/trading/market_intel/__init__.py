"""
Non-liquidity market intelligence (Phase 4).

The layer that combines with the liquidity engine: market structure, price
action, volume/price action, technical indicators and market regime. It
*composes* the existing deterministic services (``MarketStructureService``,
``TechnicalAnalysisService``, ``RegimeService``, the indicator library) rather
than re-implementing them, and adds the pieces those services did not cover:

* a **6-state regime model** + a stateful transition tracker that emits
  ``MarketRegimeChanged`` only on a real, confirmed transition,
* a **price-action read** (momentum / rejection / breakout / failed breakout /
  acceptance / range / volatility expansion-contraction),
* a **volume read** (relative volume, buy/sell split where derivable, delta /
  net flow, volume-price divergence),
* a canonical **MarketFeatures** vector the Signal Engine can consume.

Everything here is a pure function of the candle series (and any prior regime)
it is handed -- no I/O, no LLM, no wall clock -- so the same historical input
always reproduces the same reads (the backtestable / no-look-ahead rule). These
are *evidence and features*, never trading signals; no layer here emits a
direction as a decision.
"""

from __future__ import annotations

from .features import MarketFeatures, extract_features
from .price_action import (
    PriceActionAnalysis,
    PriceActionKind,
    PriceActionService,
)
from .regime import (
    MarketRegimeState,
    RegimeTracker,
    RegimeTransition,
    classify_state,
)
from .service import MarketIntelReport, MarketIntelService
from .volume import VolumeActionService, VolumeAnalysis2

__all__ = [
    "MarketFeatures",
    "MarketIntelReport",
    "MarketIntelService",
    "MarketRegimeState",
    "PriceActionAnalysis",
    "PriceActionKind",
    "PriceActionService",
    "RegimeTracker",
    "RegimeTransition",
    "VolumeActionService",
    "VolumeAnalysis2",
    "classify_state",
    "extract_features",
]
