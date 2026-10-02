"""
Trading Intelligence domain models.

Pure, dependency-light value objects shared across the trading services,
tools and (future) quant/decision layers. Everything here is immutable,
JSON-serialisable via ``to_dict()``, and free of any I/O or LLM dependency.
"""

from __future__ import annotations

from .analysis import TradingAnalysis, VolumeAnalysis
from .enums import (
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
    SourceTier,
    StructureSignalType,
    Timeframe,
    TrendState,
)
from .evidence import Evidence
from .instrument import Instrument
from .market_data import Candle, MarketData, Quote
from .provenance import DataQuality, Provenance
from .structure import Level, MarketStructure, StructureSignal, SwingPoint
from .technical import BollingerReading, MACDReading, TechnicalSnapshot

__all__ = [
    # enums
    "Assertion",
    "Confidence",
    "DataQualityStatus",
    "Direction",
    "EvidenceType",
    "SourceTier",
    "StructureSignalType",
    "Timeframe",
    "TrendState",
    # provenance
    "DataQuality",
    "Provenance",
    # instrument / market data
    "Instrument",
    "Candle",
    "MarketData",
    "Quote",
    # technical
    "BollingerReading",
    "MACDReading",
    "TechnicalSnapshot",
    # structure
    "Level",
    "MarketStructure",
    "StructureSignal",
    "SwingPoint",
    # evidence & analysis
    "Evidence",
    "TradingAnalysis",
    "VolumeAnalysis",
]
