"""
Canonical market-intelligence features (Phase 4).

The flat, named, bounded feature vector the Signal Engine consumes downstream.
Every feature is deterministic from the composed reads it derives from --
structure, technical snapshot, price action, volume and regime -- never a
probability and never a trading decision. ``0.0``/``None`` are honest
"no reading" values.

The mappings are linear and documented; thresholds/weights live in the
underlying services and analyzers, not hidden in a magic constant here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.regime import RegimeAnalysis
from ..domain.structure import MarketStructure
from ..domain.technical import TechnicalSnapshot
from .price_action import PriceActionAnalysis
from .regime import classify_state
from .volume import VolumeAnalysis2

#: ADX is reported on a 0..100 scale; normalised to 0..1 for the feature vector.
_ADX_MAX = 100.0

#: ATR-as-fraction-of-price is scaled by this to map into a 0..1 volatility
#: feature (3% daily ATR ~ a full-volatility read). Linear cap, not a fit.
_VOL_SCALE = 33.0


@dataclass(frozen=True, slots=True)
class MarketFeatures:
    """
    The canonical market-intelligence feature vector for one series.

    ``symbol`` / ``timeframe`` identify the read; ``is_mock`` is the honesty
    flag. All scores are bounded and descriptive -- a consumer weights them,
    never reads one as a decision.
    """

    symbol: str
    timeframe: str
    is_mock: bool = False

    # Structure (0..1). trend_strength from the structure read; structure_
    # strength is how clean the HH/HL/LH/LL pattern is.
    trend_strength: float = 0.0
    structure_strength: float = 0.0
    breakout_strength: float = 0.0

    # Momentum / technical (bounded). momentum = signed last return; adx =
    # trend-strength; vwap_distance = signed % distance of price from VWAP.
    momentum: float = 0.0
    adx: float = 0.0
    rsi: float = 0.0          # 0..100, kept raw (a bounded oscillator)
    atr_pct: float = 0.0      # ATR as fraction of price
    volatility: float = 0.0   # realised-volatility feature (0..1, scaled)
    vwap_distance: float = 0.0  # signed % from VWAP

    # Volume (bounded). relative_volume is a ratio; net_flow/delta in [-1,1].
    relative_volume: float = 0.0
    volume_delta: float = 0.0   # signed estimated net volume share [-1,1]
    volume_state: str = "unknown"

    # Price action (descriptive).
    price_action: str = "unknown"       # the PriceActionKind label
    volatility_state: str = "unknown"   # expanding | contracting | steady | unknown

    # Regime (0..1 confidence + the 6-state label).
    regime: str = "unknown"
    regime_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "is_mock": self.is_mock,
            "trend_strength": self.trend_strength,
            "structure_strength": self.structure_strength,
            "breakout_strength": self.breakout_strength,
            "momentum": self.momentum,
            "adx": self.adx,
            "rsi": self.rsi,
            "atr_pct": self.atr_pct,
            "volatility": self.volatility,
            "vwap_distance": self.vwap_distance,
            "relative_volume": self.relative_volume,
            "volume_delta": self.volume_delta,
            "volume_state": self.volume_state,
            "price_action": self.price_action,
            "volatility_state": self.volatility_state,
            "regime": self.regime,
            "regime_confidence": self.regime_confidence,
        }


def extract_features(
    *,
    symbol: str,
    timeframe: str,
    structure: MarketStructure,
    technical: TechnicalSnapshot,
    price_action: PriceActionAnalysis,
    volume: VolumeAnalysis2,
    regime: RegimeAnalysis,
    is_mock: bool = False,
) -> MarketFeatures:
    """
    Distill the composed reads into the canonical feature vector.

    Reads only what the sub-analyses produced -- it computes nothing new, so a
    feature can never disagree with the read it was distilled from.
    """
    state = classify_state(regime)

    # Structure strength: how clean the HH/HL/LH/LL pattern is. A coherent
    # pattern (both higher-highs + higher-lows, or both lower variants) reads
    # stronger than a muddled one.
    hh, hl, lh, ll = (
        structure.higher_highs,
        structure.higher_lows,
        structure.lower_highs,
        structure.lower_lows,
    )
    coherent = (hh and hl) or (lh and ll)
    structure_strength = structure.trend_strength * (1.0 if coherent else 0.5)

    # Breakout strength: a structural breakout/breakdown signal, weighted by
    # its confidence band.
    breakout = 0.0
    for sig in structure.signals:
        if sig.type.value in ("breakout", "breakdown"):
            breakout = max(
                breakout,
                {"low": 0.33, "medium": 0.66, "high": 1.0}[sig.confidence.value],
            )
    # A confirmed price-action breakout reinforces the structural read.
    if price_action.is_breakout:
        breakout = max(breakout, 0.66)

    # Volatility feature: realised vol (or ATR-fraction) scaled to 0..1.
    vol_feat = 0.0
    if technical.atr is not None and technical.last_price > 0:
        atr_pct = technical.atr / technical.last_price
        vol_feat = min(1.0, atr_pct * _VOL_SCALE)
    elif regime.atr_pct is not None:
        vol_feat = min(1.0, regime.atr_pct * _VOL_SCALE)

    # Regime confidence: the analysis's own confidence band, mapped to 0..1.
    regime_conf = {"low": 0.33, "medium": 0.66, "high": 1.0}[
        regime.confidence.value
    ]
    if not regime.is_reliable:
        regime_conf = 0.0

    # vwap_distance: signed % of price from VWAP.
    vwap_dist = 0.0
    if technical.vwap is not None and technical.vwap > 0:
        vwap_dist = (technical.last_price - technical.vwap) / technical.vwap * 100.0

    momentum = 0.0
    if technical.return_pct is not None:
        momentum = technical.return_pct
    elif price_action.momentum is not None:
        momentum = price_action.momentum * 100.0

    return MarketFeatures(
        symbol=symbol,
        timeframe=timeframe,
        is_mock=is_mock,
        trend_strength=round(structure.trend_strength, 4),
        structure_strength=round(min(1.0, structure_strength), 4),
        breakout_strength=round(breakout, 4),
        momentum=round(momentum, 4),
        adx=round(
            (technical.adx or regime.adx or 0.0) / _ADX_MAX, 4
        ),
        rsi=round(technical.rsi or 0.0, 4),
        atr_pct=round(
            (technical.atr / technical.last_price)
            if (technical.atr is not None and technical.last_price > 0)
            else (regime.atr_pct or 0.0),
            6,
        ),
        volatility=round(vol_feat, 4),
        vwap_distance=round(vwap_dist, 4),
        relative_volume=round(volume.relative_volume or 0.0, 4),
        volume_delta=round(volume.net_flow, 4),
        volume_state=volume.volume_state,
        price_action=price_action.kind.value,
        volatility_state=price_action.volatility_state,
        regime=state.value,
        regime_confidence=round(regime_conf, 4),
    )
