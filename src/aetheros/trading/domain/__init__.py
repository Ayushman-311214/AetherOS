"""
Trading Intelligence domain models.

Pure, dependency-light value objects shared across the trading services,
tools and (future) quant/decision layers. Everything here is immutable,
JSON-serialisable via ``to_dict()``, and free of any I/O or LLM dependency.
"""

from __future__ import annotations

from .analysis import TradingAnalysis, VolumeAnalysis
from .chart import (
    ChartAnnotation,
    ChartAnnotationKind,
    ChartData,
    ChartPoint,
    ChartState,
)
from .decision import TradingDecision
from .enums import (
    AMDPhase,
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
    ICTConcept,
    KillZoneName,
    LiquidityEventKind,
    LiquidityPoolKind,
    OptimizationObjective,
    OrderStatus,
    OrderType,
    PositionStatus,
    RiskBand,
    SessionModelKind,
    SessionName,
    SMCZoneKind,
    SourceTier,
    StrategyCategory,
    StructureBreakType,
    StructureSignalType,
    Timeframe,
    TradeAction,
    TradingMode,
    TrendState,
)
from .evidence import Evidence
from .execution import ExecutionRequest, ExecutionResult
from .hybrid import HybridChartContext
from .ict import (
    AMDPhaseWindow,
    DailyBias,
    ICTAnalysis,
    JudasSwing,
    KillZone,
    KillZoneWindow,
    LiquidityPool,
    MarketStructureShift,
    OTEZone,
    PowerOfThree,
    SessionModel,
    SessionWindow,
    TradingSession,
)
from .instrument import Instrument
from .journal import JournalEntry
from .liquidity import LiquidityAnalysis
from .market_data import Candle, MarketData, Quote
from .order_book import OrderBook, OrderBookLevel, TradeTick
from .policy import PolicyCheck, PolicyVerdict
from .provenance import DataQuality, Provenance
from .risk_limits import AccountSnapshot, RiskLimitOutcome, RiskLimitsVerdict
from .signal import SignalCandidate, SignalEvaluation
from .simulation import SimulatedTrade, SimulationExitReason, SimulationReport
from .smc import (
    DealingRange,
    LiquidityEvent,
    SMCAnalysis,
    SMCZone,
    StructureBreak,
)
from .strategy import (
    ParameterCandidate,
    ParameterSearch,
    StrategyComparison,
    StrategyEvaluation,
    StrategyRuleMatch,
    StrategySetup,
)
from .structure import Level, MarketStructure, StructureSignal, SwingPoint
from .technical import (
    BollingerReading,
    MACDReading,
    SuperTrendReading,
    TechnicalSnapshot,
    VolumeProfileReading,
)
from .trade import Order, Portfolio, Position, RiskProfile, Strategy, TradeSignal
from .tradingview import TradingViewChartState, chart_url
from .visual import VisualObservation

__all__ = [
    # enums
    "AMDPhase",
    "Assertion",
    "Confidence",
    "DataQualityStatus",
    "Direction",
    "EvidenceType",
    "ICTConcept",
    "KillZoneName",
    "LiquidityEventKind",
    "LiquidityPoolKind",
    "OptimizationObjective",
    "OrderStatus",
    "OrderType",
    "PositionStatus",
    "RiskBand",
    "SessionModelKind",
    "SessionName",
    "SMCZoneKind",
    "SourceTier",
    "StrategyCategory",
    "StructureBreakType",
    "StructureSignalType",
    "Timeframe",
    "TradeAction",
    "TradingMode",
    "TrendState",
    # provenance
    "DataQuality",
    "Provenance",
    # instrument / market data
    "Instrument",
    "Candle",
    "MarketData",
    "Quote",
    # microstructure
    "OrderBook",
    "OrderBookLevel",
    "TradeTick",
    # journal
    "JournalEntry",
    # technical
    "BollingerReading",
    "SuperTrendReading",
    "VolumeProfileReading",
    "MACDReading",
    "TechnicalSnapshot",
    # structure
    "Level",
    "MarketStructure",
    "StructureSignal",
    "SwingPoint",
    # evidence & analysis
    "Evidence",
    "HybridChartContext",
    "TradingAnalysis",
    "TradingDecision",
    "VolumeAnalysis",
    "LiquidityAnalysis",
    # smart money concepts
    "DealingRange",
    "LiquidityEvent",
    "SMCAnalysis",
    "SMCZone",
    "StructureBreak",
    # ICT (time-based) concepts
    "AMDPhaseWindow",
    "DailyBias",
    "ICTAnalysis",
    "JudasSwing",
    "KillZone",
    "KillZoneWindow",
    "LiquidityPool",
    "MarketStructureShift",
    "OTEZone",
    "PowerOfThree",
    "SessionModel",
    "SessionWindow",
    "TradingSession",
    # strategy layer
    "StrategyRuleMatch",
    "StrategySetup",
    "StrategyEvaluation",
    "StrategyComparison",
    "ParameterCandidate",
    "ParameterSearch",
    # signal layer
    "SignalCandidate",
    "SignalEvaluation",
    # simulation layer
    "SimulatedTrade",
    "SimulationExitReason",
    "SimulationReport",
    # account-level risk limits and execution record
    "AccountSnapshot",
    "RiskLimitOutcome",
    "RiskLimitsVerdict",
    "ExecutionRequest",
    "ExecutionResult",
    # execution policy (Phase 26)
    "PolicyCheck",
    "PolicyVerdict",
    # Trading lifecycle and policy value objects
    "TradeSignal",
    "Order",
    "Position",
    "Strategy",
    "Portfolio",
    "RiskProfile",
    # visual observations
    "VisualObservation",
    # tradingview chart state
    "TradingViewChartState",
    "chart_url",
    # charts
    "ChartAnnotation",
    "ChartAnnotationKind",
    "ChartData",
    "ChartPoint",
    "ChartState",
]
