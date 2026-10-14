"""
Feature-vector -> evidence conversion (Phase 5).

Turns the Phase 2-4 feature vectors (``MarketFeatures``, ``LiquidityFeatures``,
heatmap cells) into ``Evidence`` items the signal engine aggregates over, and
reports which feature sources were missing -- so a quantitative feature becomes
a *traceable evidence claim* rather than a number silently folded into a
direction.

Two honesty rules:

* **A feature is evidence only when it actually says something.** A neutral or
  absent read (UNKNOWN regime, zero imbalance, no zones) contributes a
  SIDEWAYS/UNKNOWN evidence item at LOW confidence or nothing at all -- never
  a fabricated lean.
* **Missing is recorded, not assumed.** A feature vector the caller didn't
  supply becomes a ``MissingSource``; the caller can see exactly which inputs
  the assessment rested on.
"""

from __future__ import annotations

from ..domain.enums import Assertion, Confidence, Direction, EvidenceType
from ..domain.evidence import Evidence
from ..domain.instrument import Instrument
from ..domain.provenance import DataQuality, Provenance
from .evidence import MissingSource

#: Feature-value thresholds. Documented, conservative; the feature vectors
#: themselves are bounded so these only pick out a *meaningful* read.
_MOMENTUM_BAND = 0.2       # % momentum above which it counts as evidence
_VWAP_BAND = 0.1           # % vwap distance above which it's evidence
_NETFLOW_BAND = 0.15       # |net_flow| above which flow is evidence
_IMBALANCE_BAND = 0.2      # |imbalance| above which resting lean is evidence
_REGIME_CONF_MIN = 0.4     # regime confidence needed to count as evidence


def _ev(
    instrument: Instrument,
    evidence_type: EvidenceType,
    direction: Direction,
    detail: str,
    weight: float,
    confidence: Confidence,
    provenance: Provenance,
    quality: DataQuality,
) -> Evidence:
    return Evidence(
        instrument_key=instrument.key,
        type=evidence_type,
        assertion=Assertion.CALCULATED,
        direction=direction,
        detail=detail,
        weight=min(1.0, weight),
        confidence=confidence,
        provenance=provenance,
        quality=quality,
    )


def features_to_evidence(
    *,
    market_features,
    liquidity_features,
    heatmap_cells,
    instrument: Instrument,
    timeframe: str,
    provenance: Provenance,
    quality: DataQuality,
) -> tuple[list[Evidence], list[MissingSource], int]:
    """
    Convert the supplied feature vectors to evidence + missing-source records.

    Returns ``(evidence, missing, provided_count)``: the evidence items the
    features produced, the sources that were absent, and how many feature
    sources were actually provided (for the coverage input).
    """
    evidence: list[Evidence] = []
    missing: list[MissingSource] = []
    provided = 0

    # ---- Market-intel features (structure / technical / regime / volume) ----
    if market_features is not None:
        provided += 1
        evidence.extend(
            _market_features(market_features, instrument, provenance, quality)
        )
    else:
        missing.append(
            MissingSource("market_features", "market-intel read not provided")
        )

    # ---- Liquidity features (order-book / tape) ----
    if liquidity_features is not None:
        provided += 1
        evidence.extend(
            _liquidity_features(
                liquidity_features, instrument, provenance, quality
            )
        )
    else:
        missing.append(
            MissingSource(
                "liquidity_features", "order-book/tape read not provided"
            )
        )

    # ---- Heatmap-derived cells (aggregated liquidity behaviour) ----
    if heatmap_cells:
        provided += 1
        evidence.extend(
            _heatmap_features(heatmap_cells, instrument, provenance, quality)
        )
    else:
        missing.append(
            MissingSource("heatmap", "no heatmap cells provided")
        )

    return evidence, missing, provided


def _market_features(f, instrument, provenance, quality) -> list[Evidence]:
    ev: list[Evidence] = []
    w_base = 0.3

    # Trend / structure.
    if f.trend_strength > 0:
        direction = (
            Direction.UP
            if f.regime == "trending_bullish"
            else Direction.DOWN if f.regime == "trending_bearish"
            else Direction.SIDEWAYS
        )
        if direction in (Direction.UP, Direction.DOWN):
            ev.append(_ev(
                instrument, EvidenceType.MARKET_STRUCTURE, direction,
                f"Structure trend strength {f.trend_strength:.2f} "
                f"({f.regime}).",
                weight=w_base + f.structure_strength * 0.5,
                confidence=Confidence.from_score(f.trend_strength),
                provenance=provenance, quality=quality,
            ))

    # Momentum.
    if abs(f.momentum) >= _MOMENTUM_BAND:
        ev.append(_ev(
            instrument, EvidenceType.MOMENTUM,
            Direction.UP if f.momentum > 0 else Direction.DOWN,
            f"Momentum {f.momentum:+.2f}%.",
            weight=min(0.5, abs(f.momentum) / 10.0),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))

    # Regime (only when confident enough to mean something).
    if f.regime_confidence >= _REGIME_CONF_MIN and f.regime != "unknown":
        regime_dir = (
            Direction.UP if f.regime == "trending_bullish"
            else Direction.DOWN if f.regime == "trending_bearish"
            else Direction.SIDEWAYS
        )
        ev.append(_ev(
            instrument, EvidenceType.REGIME, regime_dir,
            f"Market regime '{f.regime}' (confidence {f.regime_confidence:.2f}).",
            weight=w_base + f.regime_confidence * 0.3,
            confidence=Confidence.MEDIUM,
            provenance=provenance, quality=quality,
        ))

    # Volume delta / net flow.
    if abs(f.volume_delta) >= _NETFLOW_BAND:
        ev.append(_ev(
            instrument, EvidenceType.VOLUME,
            Direction.UP if f.volume_delta > 0 else Direction.DOWN,
            f"Estimated net-flow {f.volume_delta:+.2f} ({f.volume_state}).",
            weight=min(0.4, abs(f.volume_delta)),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))

    # VWAP distance (price-vs-mean lean).
    if abs(f.vwap_distance) >= _VWAP_BAND:
        ev.append(_ev(
            instrument, EvidenceType.TECHNICAL,
            Direction.UP if f.vwap_distance > 0 else Direction.DOWN,
            f"Price {f.vwap_distance:+.2f}% from VWAP.",
            weight=min(0.4, abs(f.vwap_distance) / 5.0),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))

    # Volatility (descriptive, non-directional).
    if f.volatility > 0 or f.volatility_state in ("expanding", "contracting"):
        ev.append(_ev(
            instrument, EvidenceType.VOLATILITY, Direction.SIDEWAYS,
            f"Volatility {f.volatility_state} ({f.volatility:.2f}).",
            weight=min(0.3, f.volatility * 0.5),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    return ev


def _liquidity_features(f, instrument, provenance, quality) -> list[Evidence]:
    ev: list[Evidence] = []
    # Resting-liquidity imbalance.
    if abs(f.liquidity_imbalance) >= _IMBALANCE_BAND:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE,
            Direction.UP if f.liquidity_imbalance > 0 else Direction.DOWN,
            f"Resting book imbalance {f.liquidity_imbalance:+.2f}.",
            weight=min(0.5, abs(f.liquidity_imbalance)),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    # Sweeps (pressure on each side).
    if f.sweep_up_score >= 0.3:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE, Direction.UP,
            f"Ask-side sweep pressure ({f.sweep_up_score:.2f}).",
            weight=min(0.4, f.sweep_up_score),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    if f.sweep_down_score >= 0.3:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE, Direction.DOWN,
            f"Bid-side sweep pressure ({f.sweep_down_score:.2f}).",
            weight=min(0.4, f.sweep_down_score),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    # Absorption (non-directional evidence of a wall working).
    if max(f.absorption_bid_score, f.absorption_ask_score) >= 0.3:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE, Direction.SIDEWAYS,
            f"Absorption detected (bid {f.absorption_bid_score:.2f} / "
            f"ask {f.absorption_ask_score:.2f}).",
            weight=min(0.4, max(f.absorption_bid_score, f.absorption_ask_score)),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    # Persistence / replenishment (non-directional stickiness).
    if f.persistence_score >= 0.3 or f.replenishment_score >= 0.3:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE, Direction.SIDEWAYS,
            f"Persistent liquidity (persistence {f.persistence_score:.2f}, "
            f"replenishment {f.replenishment_score:.2f}).",
            weight=min(0.4, max(f.persistence_score, f.replenishment_score)),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    return ev


def _heatmap_features(cells, instrument, provenance, quality) -> list[Evidence]:
    """
    Fold heatmap cells into a small set of aggregate evidence items.

    The cells are aggregated (not one evidence item per cell -- that would
    flood the ledger): the strongest sweep/absorption bin and the densest
    resting-liquidity bin each contribute one item.
    """
    if not cells:
        return []
    ev: list[Evidence] = []
    # Strongest sweep bin.
    sweep = max(cells, key=lambda c: c.sweep_score, default=None)
    if sweep is not None and sweep.sweep_score >= 0.4:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE, Direction.SIDEWAYS,
            f"Strong sweep activity near {sweep.price:.2f} "
            f"(score {sweep.sweep_score:.2f}).",
            weight=min(0.5, sweep.sweep_score),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    # Densest resting-liquidity bin.
    liq = max(cells, key=lambda c: c.total_intensity, default=None)
    if liq is not None and liq.total_intensity > 0:
        ev.append(_ev(
            instrument, EvidenceType.MARKET_STRUCTURE,
            Direction.UP if liq.imbalance > _IMBALANCE_BAND
            else Direction.DOWN if liq.imbalance < -_IMBALANCE_BAND
            else Direction.SIDEWAYS,
            f"Dense resting liquidity near {liq.price:.2f} "
            f"(imbalance {liq.imbalance:+.2f}).",
            weight=min(0.4, liq.total_intensity / 100.0),
            confidence=Confidence.LOW,
            provenance=provenance, quality=quality,
        ))
    return ev
