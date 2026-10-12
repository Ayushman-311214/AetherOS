"""
Trading Intelligence tools.

Thin, schema-friendly wrappers that expose the deterministic trading services
through the central ToolRegistry (CLAUDE.md section 11 -- agents never reach
past the registry into a service directly). Each tool resolves its service from
the DI container, does minimal coercion, and returns a JSON-serialisable dict
via the domain objects' ``to_dict()``.

The tools deliberately return the data-quality and provenance of everything
they touch, so a caller (or the LLM) can always see when a result rests on
MOCK, stale or partial data rather than real market data.
"""

from __future__ import annotations

from typing import Any

from ..core.container import container
from ..tools import tool
from .alerts import AlertService
from .alerts.rules import price_alert
from .analytics import JournalAnalyticsService
from .backtesting.comparison import compare_backtests
from .domain.enums import Direction, OptimizationObjective
from .domain.market_data import MarketData
from .errors import TradingError
from .indicators import core as ind
from .indicators.registry import get_indicator
from .services.analysis_service import AnalysisService
from .services.anomaly_service import AnomalyService
from .services.backtest_service import BacktestService
from .services.breakout_service import BreakoutService
from .services.calendar_service import EventCalendarService
from .services.calibration_history_service import CalibrationHistoryService
from .services.ceo_agent_service import CEOAgentService
from .services.ceo_service import TradingCEOService
from .services.chart_service import ChartCaptureService, ChartService
from .services.critic_service import CriticService
from .services.decision_service import DecisionService
from .services.divergence_service import DivergenceService
from .services.evidence_service import EvidenceService
from .services.explanation_service import ExplanationService
from .services.fundamental_service import FundamentalAnalysisService
from .services.historical_analogue_service import HistoricalAnalogueService
from .services.hybrid_service import HybridContextService
from .services.ict_service import ICTService
from .services.journal_service import JournalService
from .services.journal_store import JournalStore
from .services.liquidity_service import LiquidityService
from .services.macro_service import MacroContextService
from .services.market_data_service import MarketDataService
from .services.market_structure_service import MarketStructureService
from .services.monitoring_scheduler import MonitoringScheduler
from .services.monitoring_service import MonitoringService
from .services.multi_timeframe_service import MultiTimeframeService
from .services.news_service import NewsSentimentService
from .services.orchestration_service import OrchestrationService
from .services.outcome_store import OutcomeStore
from .services.performance_service import PredictionPerformanceService
from .services.portfolio_service import PortfolioRiskService
from .services.prediction_store import PredictionStore
from .services.probability_service import ProbabilityService
from .services.regime_service import RegimeService
from .services.relative_strength_service import RelativeStrengthService
from .services.risk_service import RiskService
from .services.scan_service import WatchlistScanService
from .services.signal_service import SignalService
from .services.simulation_service import SimulationService
from .services.smc_service import SMCService
from .services.strategy_service import StrategyService
from .services.track_record_service import PredictionTrackRecordService
from .services.visual_service import VisualObservationService
from .services.walk_forward_service import WalkForwardService
from .strategies.optimization import ParameterGrid, strategy_signal

# Indicators exposed by calculate_indicator and the arity of their inputs.
_PRICE_INDICATORS = {"sma", "ema", "rsi", "bollinger", "volatility", "volume_ma"}
_OHLC_INDICATORS = {"atr", "adx", "vwap", "macd", "supertrend"}
_PRICE_VOLUME_INDICATORS = {"volume_profile"}


def _market_data() -> MarketDataService:
    return container.resolve(MarketDataService)


def _structure() -> MarketStructureService:
    return container.resolve(MarketStructureService)


def _evidence() -> EvidenceService:
    return container.resolve(EvidenceService)


def _analysis() -> AnalysisService:
    return container.resolve(AnalysisService)


def _risk() -> RiskService:
    return container.resolve(RiskService)


def _regime() -> RegimeService:
    return container.resolve(RegimeService)


def _relative_strength() -> RelativeStrengthService:
    return container.resolve(RelativeStrengthService)


def _anomaly() -> AnomalyService:
    return container.resolve(AnomalyService)


def _historical() -> HistoricalAnalogueService:
    return container.resolve(HistoricalAnalogueService)


def _macro() -> MacroContextService:
    return container.resolve(MacroContextService)


def _liquidity() -> LiquidityService:
    return container.resolve(LiquidityService)


def _smc() -> SMCService:
    return container.resolve(SMCService)


def _ict() -> ICTService:
    return container.resolve(ICTService)


def _strategy() -> StrategyService:
    return container.resolve(StrategyService)


def _signals() -> SignalService:
    return container.resolve(SignalService)


def _scan() -> WatchlistScanService:
    return container.resolve(WatchlistScanService)


def _multi_timeframe() -> MultiTimeframeService:
    return container.resolve(MultiTimeframeService)


def _divergence() -> DivergenceService:
    return container.resolve(DivergenceService)


def _breakout() -> BreakoutService:
    return container.resolve(BreakoutService)


def _portfolio() -> PortfolioRiskService:
    return container.resolve(PortfolioRiskService)


def _simulation() -> SimulationService:
    return container.resolve(SimulationService)


def _visual() -> VisualObservationService:
    return container.resolve(VisualObservationService)


def _hybrid() -> HybridContextService:
    return container.resolve(HybridContextService)


def _journal() -> JournalService:
    return container.resolve(JournalService)


def _journal_store() -> JournalStore:
    return container.resolve(JournalStore)


def _journal_analytics() -> JournalAnalyticsService:
    return container.resolve(JournalAnalyticsService)


def _alerts() -> AlertService:
    return container.resolve(AlertService)


def _split_symbols(symbols: str | list[str]) -> list[str]:
    """Accept a list, or a comma/whitespace-separated string, of symbols."""
    if isinstance(symbols, str):
        return [s for s in symbols.replace(",", " ").split() if s]
    return [str(s) for s in symbols]


def _backtest() -> BacktestService:
    return container.resolve(BacktestService)


def _walk_forward() -> WalkForwardService:
    return container.resolve(WalkForwardService)


def _critic() -> CriticService:
    return container.resolve(CriticService)


def _probability() -> ProbabilityService:
    return container.resolve(ProbabilityService)


def _news() -> NewsSentimentService:
    return container.resolve(NewsSentimentService)


def _events() -> EventCalendarService:
    return container.resolve(EventCalendarService)


def _fundamentals() -> FundamentalAnalysisService:
    return container.resolve(FundamentalAnalysisService)


def _orchestrator() -> OrchestrationService:
    return container.resolve(OrchestrationService)


def _explanation() -> ExplanationService:
    return container.resolve(ExplanationService)


def _decision() -> DecisionService:
    return container.resolve(DecisionService)


def _prediction_store() -> PredictionStore:
    return container.resolve(PredictionStore)


def _track_record() -> PredictionTrackRecordService:
    return container.resolve(PredictionTrackRecordService)


def _monitoring() -> MonitoringService:
    return container.resolve(MonitoringService)


def _monitoring_scheduler() -> MonitoringScheduler:
    return container.resolve(MonitoringScheduler)


def _outcome_store() -> OutcomeStore:
    return container.resolve(OutcomeStore)


def _performance() -> PredictionPerformanceService:
    return container.resolve(PredictionPerformanceService)


def _calibration_history() -> CalibrationHistoryService:
    return container.resolve(CalibrationHistoryService)


def _ceo() -> TradingCEOService:
    return container.resolve(TradingCEOService)


def _ceo_agent() -> CEOAgentService:
    return container.resolve(CEOAgentService)


@tool(
    category="trading.data",
    description=(
        "Get the latest price quote for an instrument (symbol like 'AAPL' or "
        "'NSE:RELIANCE'). Includes provenance and source tier; a MOCK tier "
        "means the number is synthetic, not real market data."
    ),
)
async def get_market_quote(symbol: str) -> dict[str, Any]:
    quote = await _market_data().get_quote(symbol)
    return quote.to_dict()


@tool(
    category="trading.data",
    description=(
        "Get recent OHLCV candles for an instrument and timeframe (1m, 5m, "
        "15m, 30m, 1h, 4h, 1d, 1w). Returns summary stats, data quality and a "
        "small tail of recent candles -- not the full series."
    ),
)
async def get_market_candles(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    return data.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Calculate one technical indicator's latest value for an instrument. "
        "Supported: sma, ema, rsi, macd, atr, bollinger, vwap, adx, "
        "volatility, volume_ma, supertrend (trend side, line and flip stop), "
        "volume_profile (point of control and value area; 'period' sets the "
        "bin count). 'period' applies to indicators that take one. Custom "
        "indicators registered at runtime are also accepted by name."
    ),
)
async def calculate_indicator(
    symbol: str,
    indicator: str,
    timeframe: str = "1d",
    period: int = 14,
    limit: int = 300,
) -> dict[str, Any]:
    name = indicator.strip().lower()
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    closes = data.closes()
    highs = data.highs()
    lows = data.lows()
    volumes = data.volumes()

    result: dict[str, Any] = {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "indicator": name,
        "bars": data.count,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
    }

    if name == "sma":
        result["value"] = ind.last_finite(ind.sma(closes, period))
        result["period"] = period
    elif name == "ema":
        result["value"] = ind.last_finite(ind.ema(closes, period))
        result["period"] = period
    elif name == "rsi":
        result["value"] = ind.last_finite(ind.rsi(closes, period))
        result["period"] = period
    elif name == "atr":
        result["value"] = ind.last_finite(ind.atr(highs, lows, closes, period))
        result["period"] = period
    elif name == "adx":
        result["value"] = ind.last_finite(ind.adx(highs, lows, closes, period))
        result["period"] = period
    elif name == "vwap":
        result["value"] = ind.last_finite(ind.vwap(highs, lows, closes, volumes))
    elif name == "volatility":
        result["value"] = ind.last_finite(ind.volatility(closes, period))
        result["period"] = period
    elif name == "volume_ma":
        result["value"] = ind.last_finite(ind.volume_ma(volumes, period))
        result["period"] = period
    elif name == "macd":
        macd_line, signal_line, hist = ind.macd(closes)
        result["value"] = {
            "macd": ind.last_finite(macd_line),
            "signal": ind.last_finite(signal_line),
            "histogram": ind.last_finite(hist),
        }
    elif name == "bollinger":
        mid, upper, lower = ind.bollinger(closes, period)
        result["value"] = {
            "middle": ind.last_finite(mid),
            "upper": ind.last_finite(upper),
            "lower": ind.last_finite(lower),
        }
        result["period"] = period
    elif name == "supertrend":
        st_line, st_dir, st_stop = ind.supertrend(highs, lows, closes, period)
        direction = ind.last_finite(st_dir)
        result["value"] = {
            "direction": ("up" if direction > 0 else "down") if direction is not None else None,
            "line": ind.last_finite(st_line),
            "stop": ind.last_finite(st_stop),
        }
        result["period"] = period
    elif name == "volume_profile":
        profile = ind.volume_profile(closes, volumes, period)
        result["value"] = profile.to_dict() if profile else None
        result["bins"] = period
    else:
        supported = sorted(
            _PRICE_INDICATORS | _OHLC_INDICATORS | _PRICE_VOLUME_INDICATORS
        )
        # A custom indicator registered through the extension point takes the
        # same arrays and returns an input-aligned result; try it before
        # refusing the name.
        custom = get_indicator(name)
        if custom is not None:
            try:
                result["value"] = custom(closes, highs, lows, volumes)
                result["custom"] = True
                return result
            except Exception as exc:  # a custom indicator's failure is its own
                return {
                    "error": f"Custom indicator '{name}' failed: {exc}",
                    "supported": supported,
                }
        return {
            "error": f"Unknown indicator '{indicator}'.",
            "supported": supported,
        }

    return result


@tool(
    category="trading.analysis",
    description=(
        "Analyze the market structure of an instrument: trend, swing points, "
        "support/resistance levels and structural signals (breakout/breakdown/"
        "range). Deterministic; every detection carries its reference price."
    ),
)
async def analyze_market_structure(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    structure = _structure().analyze(data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "structure": structure.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Get support and resistance levels for an instrument, clustered from "
        "swing pivots and ranked by proximity to the current price."
    ),
)
async def get_support_resistance(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    structure = _structure().analyze(data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "last_price": data.last_price,
        "supports": [lvl.to_dict() for lvl in structure.supports],
        "resistances": [lvl.to_dict() for lvl in structure.resistances],
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Analyze recent volume behaviour for an instrument: last volume vs its "
        "moving average, relative volume and whether volume is rising/falling."
    ),
)
async def get_volume_analysis(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    volume = _evidence().build_volume_analysis(data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "volume": volume.to_dict() if volume else None,
    }


@tool(
    category="trading.analysis",
    description=(
        "Analyze the liquidity profile of an instrument: where traded volume "
        "sits relative to price (volume-profile point of control and 70% value "
        "area), participation (relative volume vs its moving average), a "
        "volatility spread proxy (ATR as a fraction of price) and price's "
        "distance to the point of control. Deterministic situational context "
        "-- never a prediction; carries no probability. Inputs that cannot be "
        "computed from the available bars are reported as null with a "
        "limitation, never fabricated."
    ),
)
async def analyze_liquidity(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    liquidity = _liquidity().analyze(data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "liquidity": liquidity.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Detect Smart Money Concepts structure on an instrument: break of "
        "structure (BOS) and change of character (CHoCH) from closes through "
        "confirmed swings, the order blocks and fair value gaps behind those "
        "moves, mitigation blocks (order blocks price returned to and "
        "respected), liquidity sweeps and equal-highs/lows pools, and the "
        "premium/discount read of the active dealing range. Every detection "
        "carries the bars, prices and reasons it was derived from. "
        "Deterministic situational context -- never a prediction, never a "
        "probability, and derived from candle geometry rather than keywords."
    ),
)
async def analyze_smc(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    smc = _smc().analyze(data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "smc": smc.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Run the ICT (Inner Circle Trader) analysis of an instrument: the daily "
        "bias read from the prior day, market structure shifts (a change of "
        "character confirmed by displacement), kill-zone windows with the share "
        "of the session range each carried, the optimal trade entry "
        "(0.618-0.79) band of the active leg, resting liquidity pools at equal "
        "highs/lows and session and prior-day extremes, Judas swings, "
        "Power-of-Three session decomposition, and how each session behaved "
        "against the one before it. Detection is time-based and deterministic, "
        "using real session windows in an exchange timezone with daylight-"
        "saving handled -- every concept carries the timestamps, prices and "
        "reasons it was derived from. Situational context only: never a "
        "prediction, never a probability."
    ),
)
async def analyze_ict(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    ict = _ict().analyze(data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "ict": ict.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Select and compare trading strategies on one instrument: run every "
        "named strategy (or the full registered panel) over a single shared "
        "read of the market, and report what each made of it -- the setup it "
        "found, the side it took, the price it was read at, the structural "
        "level that would void it, and the named rules that did and did not "
        "hold. Reports the panel's consensus AND its disagreement: a split "
        "panel yields no consensus direction and lists the dissenters rather "
        "than averaging a 3-2 vote into one answer. When no strategy finds a "
        "setup the comparison says so -- that is the system's insufficient-"
        "evidence result, not a failure. Setups carry no stop, target or size: "
        "risk geometry is the risk engine's deterministic output."
    ),
)
async def evaluate_strategies(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
    strategies: str | list[str] | None = None,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    comparison = await _strategy().compare(
        data,
        strategy_ids=_split_symbols(strategies) if strategies else None,
    )
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "comparison": comparison.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "List the trading strategies available for evaluation: each strategy's "
        "id, name, category (scalping, swing, trend following, mean reversion, "
        "ICT, SMC, breakout), what it looks for, and its current parameters. "
        "Use the returned ids with evaluate_strategies and optimize_strategy."
    ),
)
async def list_strategies() -> dict[str, Any]:
    registry = _strategy().registry
    return {
        "strategies": [
            {
                "strategy_id": strategy.strategy_id,
                "name": strategy.name,
                "category": strategy.category.value,
                "description": strategy.description,
                "parameters": dict(strategy.parameters),
            }
            for strategy in registry.all()
        ]
    }


@tool(
    category="trading.analysis",
    description=(
        "Search a strategy's parameters for a better configuration, by running "
        "an explicit grid of values through the walk-forward backtester. Each "
        "bar is evaluated using only the bars up to and including it, so the "
        "search cannot see the future, and the strategy's current settings are "
        "always measured as a baseline to compare against. Reports the best "
        "*reliable* configuration, or explicitly reports that none qualified -- "
        "a thin sample or synthetic data never crowns a winner. Objectives: "
        "directional_accuracy, cumulative_return, sharpe. This measures a "
        "configuration's historical behaviour; it does not predict."
    ),
)
async def optimize_strategy(
    symbol: str,
    strategy: str,
    parameters: dict[str, list[float]],
    timeframe: str = "1d",
    limit: int = 500,
    objective: str = "directional_accuracy",
    horizon: int | None = None,
    warmup: int | None = None,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    search = await _strategy().optimize(
        data,
        strategy,
        ParameterGrid.from_dict(parameters),
        objective=OptimizationObjective(objective),
        horizon=horizon,
        warmup=warmup,
    )
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "search": search.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Walk-forward test a strategy: split its history into consecutive "
        "train/test folds, choose the best parameters on each training window "
        "using only what was known then, and measure those choices on the test "
        "window that follows. Reports the pooled OUT-OF-SAMPLE accuracy, win "
        "rate, profit factor, expectancy, Sharpe and max drawdown, alongside the "
        "in-sample average so the gap between them is visible -- a large gap "
        "means the parameters were fitted, not found. An embargo of 'horizon' "
        "bars sits between train and test so a training bar's forward label "
        "cannot reach into the test window. Returns not-reliable with the reason "
        "when the data is MOCK or the folds too few or too thin."
    ),
)
async def walk_forward_backtest(
    symbol: str,
    strategy: str,
    parameters: dict[str, list[float]] | None = None,
    timeframe: str = "1d",
    limit: int = 1000,
    objective: str = "directional_accuracy",
    horizon: int | None = None,
    warmup: int | None = None,
    train_bars: int | None = None,
    test_bars: int | None = None,
    anchored: bool = False,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    report = await _walk_forward().run(
        data,
        strategy,
        ParameterGrid.from_dict(parameters or {}),
        objective=OptimizationObjective(objective),
        horizon=horizon,
        warmup=warmup,
        train_bars=train_bars,
        test_bars=test_bars,
        anchored=anchored,
    )
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "walk_forward": report.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Compare several strategies by backtesting each over the SAME "
        "instrument, timeframe, horizon and warmup, then ranking them on one "
        "named metric: directional_accuracy, win_rate, profit_factor, "
        "expectancy, sharpe, cumulative_return (higher is better) or "
        "max_drawdown (lower is better). Refuses to compare backtests measured "
        "on different questions, and declares a winner ONLY when it is reliable "
        "and strictly beat the runner-up -- a tie, a synthetic-data leader or an "
        "unreliable leader yields no winner with the reason stated."
    ),
)
async def compare_strategy_backtests(
    symbol: str,
    strategies: str | list[str],
    timeframe: str = "1d",
    limit: int = 300,
    metric: str = "directional_accuracy",
    horizon: int | None = None,
    warmup: int | None = None,
) -> dict[str, Any]:
    service = _strategy()
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    build_context = service.build_context

    results: dict[str, Any] = {}
    for strategy_id in _split_symbols(strategies):
        strategy = service.registry.get(strategy_id)
        if strategy is None:
            raise TradingError(
                f"Unknown strategy '{strategy_id}'. Registered: "
                f"{', '.join(service.registry.ids()) or 'none'}.",
                hint="Run list_strategies to see the registered strategies.",
            )
        results[strategy_id] = await _backtest().run(
            data,
            strategy_signal(strategy, build_context),
            horizon=horizon,
            warmup=warmup,
        )

    comparison = compare_backtests(results, metric=metric)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "provenance": data.provenance.to_dict(),
        "quality": data.quality.to_dict(),
        "comparison": comparison.to_dict(),
    }


@tool(
    category="trading.simulation",
    description=(
        "Paper-trade one strategy over an instrument's own history against a "
        "VIRTUAL account: replay the candles bar by bar, decide each bar on a "
        "past-only window, size the position from the account's live equity, "
        "pass it through the admission gate, and let the real PAPER venue fill "
        "it at the replayed bar. Returns the trades, the equity curve, "
        "per-trade metrics and an is_reliable verdict with its limitations. "
        "Real market data, fake money: no order here can reach a live venue, "
        "and a MOCK or too-thin series comes back unreliable with the reason "
        "stated rather than dressed up as a result."
    ),
)
async def simulate_strategy(
    symbol: str,
    strategy: str,
    timeframe: str = "1d",
    limit: int = 300,
    warmup: int | None = None,
    initial_balance: float | None = None,
    commission_bps: float | None = None,
    slippage_bps: float | None = None,
) -> dict[str, Any]:
    registry = _strategy().registry
    if registry.get(strategy) is None:
        raise TradingError(
            f"Unknown strategy '{strategy}'. Registered: "
            f"{', '.join(registry.ids()) or 'none'}.",
            hint="Run list_strategies to see the registered strategies.",
        )
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    report = await _simulation().run(
        data,
        strategy,
        warmup=warmup,
        initial_balance=initial_balance,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
    )
    entries = _journal().entries_for_report(report)
    # Persist the settled trail (spec Phase 27). Recording upserts on the
    # entry's content-addressed id, so re-running the same history refreshes
    # the row in place rather than duplicating it; a run that settled nothing
    # writes nothing. Persistence is a side effect -- the tool returns the same
    # entries whether or not the store is durable.
    for entry in entries:
        await _journal_store().record(entry)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "simulation": report.to_dict(),
        "journal": {
            "entry_count": len(entries),
            "entries": [entry.to_dict() for entry in entries],
        },
    }


@tool(
    category="trading.analytics",
    description=(
        "Measure trading performance from a strategy's own paper-trade "
        "journal: paper-trade the strategy over its history, turn the settled "
        "trades into journal entries, and aggregate them into win rate, "
        "profit factor, expectancy, Sharpe, max drawdown, average planned "
        "risk/reward, monthly return and per-strategy/symbol/timeframe "
        "breakdowns. Open trades carry no result and never enter the P/L "
        "metrics; a thin or MOCK book comes back is_reliable=false with the "
        "reason stated. Measures a book that already exists -- it never trades."
    ),
)
async def journal_performance(
    symbol: str,
    strategy: str,
    timeframe: str = "1d",
    limit: int = 300,
    warmup: int | None = None,
    initial_balance: float | None = None,
    commission_bps: float | None = None,
    slippage_bps: float | None = None,
) -> dict[str, Any]:
    registry = _strategy().registry
    if registry.get(strategy) is None:
        raise TradingError(
            f"Unknown strategy '{strategy}'. Registered: "
            f"{', '.join(registry.ids()) or 'none'}.",
            hint="Run list_strategies to see the registered strategies.",
        )
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    report = await _simulation().run(
        data,
        strategy,
        warmup=warmup,
        initial_balance=initial_balance,
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
    )
    entries = _journal().entries_for_report(report)
    analytics = _journal_analytics().summarize(entries)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "strategy": strategy,
        "entry_count": len(entries),
        "analytics": analytics.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Generate trading signals on an instrument: run every strategy (or a "
        "named subset), and for each setup that fired, derive the full risk "
        "geometry (entry, stop, target, risk/reward, size from the account "
        "risk budget), run the critic, and emit a BUY or SELL signal ONLY if "
        "every gate passes -- side agreement, actionable data, an APPROVE "
        "critic verdict, and an acceptable risk/reward. Every rejected "
        "candidate names the gates it failed; a run where nothing fired is "
        "the honest insufficient-evidence result. A signal is a proposal with "
        "confidence, risk, reasoning and evidence -- never an order, and "
        "nothing here reaches a broker."
    ),
)
async def generate_signals(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
    strategies: str | list[str] | None = None,
    account_equity: float | None = None,
    risk_pct: float | None = None,
) -> dict[str, Any]:
    evaluation = await _signals().evaluate(
        symbol,
        timeframe=timeframe,
        limit=limit,
        strategy_ids=_split_symbols(strategies) if strategies else None,
        account_equity=account_equity,
        risk_pct=risk_pct,
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "provenance": evaluation.provenance.to_dict()
        if evaluation.provenance
        else None,
        "quality": evaluation.quality.to_dict() if evaluation.quality else None,
        "signals": evaluation.to_dict(),
    }


@tool(
    category="trading.analysis",
    description=(
        "Detect the market regime of an instrument -- trending (up/down), "
        "ranging or volatile -- from ADX (trend strength) and ATR-as-a-"
        "fraction-of-price (realised volatility). Deterministic situational "
        "context, not a prediction; carries no probability. MOCK, unusable or "
        "too-thin data yields an UNKNOWN regime that is never reliable rather "
        "than a fabricated one."
    ),
)
async def detect_market_regime(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    regime = await _regime().detect(data)
    return regime.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Measure an instrument's relative strength against a benchmark (default "
        "a broad-market proxy; pass 'benchmark' like 'SPY' or 'NSE:NIFTY' to "
        "override) over a lookback window: compare the two return series and "
        "report whether the instrument OUTPERFORMED (up), UNDERPERFORMED (down) "
        "or tracked (sideways) the benchmark, with the excess return and a "
        "MARKET_CONTEXT evidence item. This is the deterministic 'sector/market "
        "strength' read, not a prediction and carrying no probability. It is "
        "flagged NOT reliable -- with the reason -- on MOCK, unusable or too-thin "
        "data on either the instrument or the benchmark, and returns an UNKNOWN "
        "lean rather than fabricating one."
    ),
)
async def analyze_relative_strength(
    symbol: str,
    benchmark: str | None = None,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    service = _relative_strength()
    benchmark_symbol = (benchmark or "").strip() or service.default_benchmark
    market_data = _market_data()
    instrument_data = await market_data.get_candles(symbol, timeframe, limit=limit)
    benchmark_data = await market_data.get_candles(
        benchmark_symbol, timeframe, limit=limit
    )
    analysis = service.analyze(instrument_data, benchmark_data)
    return analysis.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Detect whether the most recent bar is a statistical anomaly against the "
        "instrument's own trailing baseline: z-score the last bar's return, "
        "volume and overnight gap versus the prior window and flag a ~3-sigma or "
        "larger outlier, with an ANOMALY evidence item and its directional lean "
        "(a big up/down move leans that way; a volume-only spike is non-"
        "directional). This is deterministic outlier detection, not a prediction "
        "and carrying no probability. It is flagged NOT reliable -- with the "
        "reason -- on MOCK, unusable or too-thin data, and reports a determinate "
        "'no anomaly' read on a quiet tape rather than inventing an event."
    ),
)
async def detect_anomalies(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    analysis = _anomaly().analyze(data)
    return analysis.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Find historical analogues for an instrument's current setup: compare the "
        "latest bar's causal feature vector to every past bar with a fully-"
        "realised forward outcome, take the K nearest, and report how they "
        "resolved -- the up-rate and mean forward return over the horizon, with a "
        "HISTORICAL evidence item and its directional lean. This is look-ahead-"
        "safe deterministic pattern-matching, not a prediction and carrying no "
        "probability. It is flagged NOT reliable -- with the reason -- on MOCK, "
        "unusable or too-thin history, and reports an inconclusive (sideways) read "
        "on an even analogue split rather than inventing a lean."
    ),
)
async def find_historical_analogues(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 400,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    analysis = _historical().analyze(data)
    return analysis.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Read the broad-market risk posture from a market benchmark (default a "
        "broad-market proxy; pass 'benchmark' like 'SPY' or 'NSE:NIFTY' to "
        "override): classify the benchmark's own regime and report whether the "
        "overall market is RISK_ON (trending up), RISK_OFF (trending down or "
        "whipsawing) or NEUTRAL (range-bound), with a MACRO evidence item. This "
        "is the context a single-name signal sits inside, not a prediction and "
        "carrying no probability. It is flagged NOT reliable -- with the reason -- "
        "on MOCK, unusable or too-thin benchmark data, returning an UNKNOWN "
        "posture rather than fabricating one."
    ),
)
async def analyze_macro_context(
    benchmark: str | None = None,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    service = _macro()
    benchmark_symbol = (benchmark or "").strip() or service.default_benchmark
    data = await _market_data().get_candles(benchmark_symbol, timeframe, limit=limit)
    context = await service.analyze(data)
    return context.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Scan a watchlist and rank it by directional signal strength: run the "
        "deterministic analysis across several instruments (pass 'symbols' as a "
        "comma- or space-separated list like 'AAPL, MSFT, NVDA') and return them "
        "ordered so the strongest ACTIONABLE setups surface first. Each row "
        "carries its own direction, confidence, score and an honest reliability "
        "flag; a mock/unusable/UNKNOWN symbol is included but flagged not "
        "actionable and ranked last, and a symbol whose data could not be fetched "
        "is reported as an error row rather than dropped or fabricated. This "
        "ranks, it does not predict."
    ),
)
async def scan_watchlist(
    symbols: str | list[str],
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    result = await _scan().scan(_split_symbols(symbols), timeframe, limit=limit)
    return result.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Size a basket of trades against one risk budget: for each symbol (pass "
        "'symbols' as a comma/space-separated list) run the deterministic risk "
        "assessment, then allocate position sizes across the actionable ones so "
        "the whole book risks at most a total budget (a fraction of account "
        "equity, split per trade) and stays under a gross-exposure cap, scaling "
        "down if needed. A symbol with no actionable trade or no usable stop is "
        "excluded with a reason. This is advisory risk geometry, not a "
        "recommendation to trade, and it fabricates no sizing on missing data."
    ),
)
async def size_portfolio(
    symbols: str | list[str],
    account_equity: float,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    from .domain.portfolio import PortfolioCandidate

    analysis_service = _analysis()
    risk_service = _risk()
    candidates: list[PortfolioCandidate] = []
    for symbol in _split_symbols(symbols):
        try:
            analysis = await analysis_service.analyze(symbol, timeframe, limit=limit)
            assessment = await risk_service.assess(analysis, account_equity=account_equity)
        except (TradingError, ValueError):
            continue
        if (
            not assessment.is_actionable
            or assessment.stop_loss is None
            or not assessment.risk_per_unit
        ):
            continue
        candidates.append(
            PortfolioCandidate(
                instrument_key=assessment.instrument.key,
                direction=assessment.direction,
                entry=assessment.entry,
                stop=assessment.stop_loss,
                risk_per_share=assessment.risk_per_unit,
            )
        )
    plan = _portfolio().allocate(candidates, account_equity=account_equity)
    return plan.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Check multi-timeframe confirmation for an instrument: run the "
        "deterministic analysis on a base timeframe and a higher one (default "
        "weekly; pass 'higher_timeframe' to override) and report whether the "
        "higher-timeframe trend CONFIRMS the base read, CONFLICTS with it (a "
        "counter-trend call), or is NEUTRAL, with a TREND evidence item carrying "
        "the higher-timeframe trend. This is context, not a prediction. It is "
        "flagged NOT reliable -- with the reason -- on MOCK, unusable or too-thin "
        "data on either timeframe, returning UNKNOWN rather than fabricating an "
        "alignment."
    ),
)
async def analyze_multi_timeframe(
    symbol: str,
    timeframe: str = "1d",
    higher_timeframe: str | None = None,
    limit: int = 300,
) -> dict[str, Any]:
    service = _multi_timeframe()
    higher_tf = (higher_timeframe or "").strip() or service.default_higher_timeframe
    analysis = _analysis()
    base = await analysis.analyze(symbol, timeframe, limit=limit)
    higher = await analysis.analyze(symbol, higher_tf, limit=limit)
    return service.analyze(base, higher).to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Detect regular momentum divergence between price and RSI for an "
        "instrument: a lower price low against a higher RSI low is bullish "
        "divergence (a weakening downtrend), a higher price high against a lower "
        "RSI high is bearish (a weakening uptrend). Returns the divergence "
        "direction with a MOMENTUM evidence item. This is a deterministic "
        "technical read, not a prediction and carrying no probability. It is "
        "flagged NOT reliable -- with the reason -- on MOCK, unusable or too-thin "
        "data, and reports 'no divergence' (sideways) on a clean series rather "
        "than inventing one."
    ),
)
async def detect_divergence(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    return _divergence().analyze(data).to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Detect a channel breakout for an instrument: whether the latest close "
        "pushed above the prior-N-bar highest high (bullish breakout) or below "
        "the lowest low (bearish breakdown), with above-average-volume "
        "confirmation. Returns the breakout direction and channel edges with a "
        "MARKET_STRUCTURE evidence item. This is a deterministic price-action "
        "read, not a prediction and carrying no probability. It is flagged NOT "
        "reliable -- with the reason -- on MOCK, unusable or too-thin data, and "
        "reports 'no breakout' (sideways) when the close sits inside the channel."
    ),
)
async def detect_breakout(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    return _breakout().analyze(data).to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Run the full deterministic analysis for an instrument: technical "
        "indicators, market structure, volume and fused, evidence-backed "
        "directional lean with an honest confidence. Returns 'unknown' with "
        "limitations when the data is insufficient or synthetic rather than "
        "fabricating a signal. This is analysis, not a guarantee."
    ),
)
async def analyze_instrument(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    analysis = await _analysis().analyze(symbol, timeframe, limit=limit)
    return analysis.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Build a deterministic risk plan for an instrument: entry, a volatility- "
        "or structure-based stop, target(s), risk/reward, an explicit "
        "invalidation level and -- if 'account_equity' is given -- a position "
        "size for 'risk_pct' percent of equity. 'direction' (up/down) overrides "
        "the analysed bias; without a defined side it returns no geometry rather "
        "than inventing one. Not actionable on MOCK or unusable data. This is "
        "risk math, not trade advice."
    ),
)
async def assess_risk(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
    direction: str | None = None,
    account_equity: float | None = None,
    risk_pct: float | None = None,
) -> dict[str, Any]:
    override: Direction | None = None
    if direction is not None and direction.strip():
        try:
            override = Direction(direction.strip().lower())
        except ValueError:
            return {
                "error": f"Unknown direction '{direction}'.",
                "supported": [Direction.UP.value, Direction.DOWN.value],
            }

    analysis = await _analysis().analyze(symbol, timeframe, limit=limit)
    assessment = await _risk().assess(
        analysis,
        direction=override,
        account_equity=account_equity,
        risk_pct=risk_pct,
    )
    return assessment.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Backtest the deterministic directional signal on an instrument's own "
        "history: walk the candles bar by bar, predict from past bars only, and "
        "score each call against the realised move 'horizon' bars later. Returns "
        "directional accuracy vs. the empirical up-rate (the baseline to beat), "
        "coverage and trade-return stats. Look-ahead-safe by construction. NOT "
        "reliable on MOCK data or a thin sample -- it verifies the method, not a "
        "real edge, and reports no fabricated probabilities."
    ),
)
async def backtest_signal(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
    horizon: int | None = None,
    warmup: int | None = None,
) -> dict[str, Any]:
    analysis = _analysis()

    async def _signal(window: MarketData) -> Direction:
        # emit=False: a walk-forward run must not flood the bus with one
        # AnalysisCompleted per bar.
        result = await analysis.analyze_data(window, emit=False)
        return result.direction

    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    result = await _backtest().run(
        data, _signal, horizon=horizon, warmup=warmup
    )
    return result.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Run the deterministic critic on an instrument's current signal. It "
        "challenges the fused analysis and its risk geometry with a fixed battery "
        "of checks -- evidence sufficiency, whether the indicators actually agree "
        "with the fused direction, data quality/source, and risk/reward -- and "
        "returns a go/no-go verdict: APPROVE, REJECT, or INSUFFICIENT_EVIDENCE, "
        "each with its reasons. It rejects weak or self-contradicting setups and "
        "returns INSUFFICIENT_EVIDENCE on MOCK or unusable data rather than "
        "approving a fabricated signal. This is validation, not trade advice."
    ),
)
async def critique_signal(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    analysis = await _analysis().analyze(symbol, timeframe, limit=limit)
    risk = await _risk().assess(analysis)
    report = await _critic().critique(analysis, risk=risk)
    return report.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Estimate a calibrated probability that an instrument closes higher over "
        "the next 'horizon' bars. Trains a deterministic logistic model on causal "
        "features, splits the history time-ordered into train/calibration/holdout, "
        "Platt-calibrates it, and reports P(up)/P(down) with out-of-sample Brier, "
        "log-loss, accuracy and ECE. Flags the estimate NOT reliable -- and gives "
        "the reason -- on MOCK data, thin history, or when it fails to beat the "
        "naive base-rate baseline. A probability is an estimate under stated "
        "conditions, never a guarantee (spec sections 3, 6, 28)."
    ),
)
async def estimate_probability(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 400,
    horizon: int | None = None,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    estimate = await _probability().estimate(data, horizon=horizon)
    return estimate.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Generate the full deterministic trading report for an instrument -- the "
        "end-to-end desk pipeline: analysis, risk geometry, a calibrated "
        "probability estimate, the critic's go/no-go verdict and (optionally, if "
        "'run_backtest' is true) a look-ahead-safe backtest, composed into one "
        "report with key levels, evidence, an invalidation level and an explicit "
        "recommendation (approved / rejected / no_trade). A calibrated probability "
        "is surfaced only when it passes its out-of-sample reliability gate -- "
        "never fabricated -- and the report returns 'no_trade' on MOCK or "
        "insufficient data rather than inventing a signal. This is analysis, not "
        "trade advice or a guarantee."
    ),
)
async def generate_trading_report(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
    direction: str | None = None,
    account_equity: float | None = None,
    risk_pct: float | None = None,
    run_backtest: bool = False,
) -> dict[str, Any]:
    override: Direction | None = None
    if direction is not None and direction.strip():
        try:
            override = Direction(direction.strip().lower())
        except ValueError:
            return {
                "error": f"Unknown direction '{direction}'.",
                "supported": [Direction.UP.value, Direction.DOWN.value],
            }

    report = await _orchestrator().generate_report(
        symbol,
        timeframe,
        limit=limit,
        direction=override,
        account_equity=account_equity,
        risk_pct=risk_pct,
        run_backtest=run_backtest,
    )
    return report.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Explain WHY an instrument's recommendation came out the way it did: run "
        "the full deterministic report, then consolidate every piece of evidence "
        "it gathered (core technical/structure/volume plus each fused context "
        "layer) into one de-duplicated ledger grouped into reasons that support "
        "vs oppose the fused direction, with the net reliable weight and the "
        "critic's reasons. This explains the existing recommendation; it computes "
        "no new signal and invents no number. A MOCK/insufficient run explains "
        "itself honestly as NO_TRADE."
    ),
)
async def explain_signal(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    report = await _orchestrator().generate_report(symbol, timeframe, limit=limit)
    return _explanation().explain(report).to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Produce the structured trading decision for an instrument: market view, "
        "strategy setup, direction, confidence, supporting vs contradictory "
        "evidence, entry/stop/target/risk-reward/invalidation, reasoning, "
        "uncertainty and provenance -- assembled from the deterministic report, "
        "the strategy panel and (when a screenshot is available) the visual "
        "read. The decision never exceeds its report and never reaches a broker: "
        "the LLM reasons over it, execution stays deterministic and "
        "policy-controlled. A MOCK/insufficient run decides NO_TRADE with the "
        "uncertainty stated. Pass 'with_visual=True' to include the chart-"
        "screenshot read as an advisory note. This is analysis, not trade advice."
    ),
)
async def decide(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
    with_visual: bool = False,
) -> dict[str, Any]:
    hybrid = None
    if with_visual:
        hybrid = await _hybrid().build(symbol, timeframe, limit=limit)
    decision = await _decision().decide(
        symbol, timeframe=timeframe, limit=limit, hybrid=hybrid
    )
    return _decision().to_dict_context(decision)


@tool(
    category="trading.analysis",
    description=(
        "Produce a plain-language CEO brief for an instrument: run the full "
        "deterministic report, then have the LLM narrate it in clear prose. The "
        "deterministic core decides (direction, probability, risk, "
        "recommendation); the LLM only explains and never invents a number. The "
        "full report is embedded as the source of truth. If no LLM is configured "
        "(or it fails) the brief falls back to a deterministic templated summary "
        "rather than failing -- the core works without the LLM. A MOCK/"
        "insufficient run is narrated honestly as NO_TRADE. Pass "
        "'with_visual=True' to hand the LLM the unified hybrid context (report "
        "numbers plus the chart-screenshot read and its trust rules) instead of "
        "the bare report; without a screenshot the narration rests on numbers "
        "alone."
    ),
)
async def brief_instrument(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
    with_visual: bool = False,
) -> dict[str, Any]:
    brief = await _ceo().brief(symbol, timeframe, limit=limit, with_visual=with_visual)
    return brief.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Answer a free-text trading request end to end: the CEO interprets which "
        "instrument and timeframe you mean (LLM-assisted when configured, a "
        "deterministic heuristic otherwise), runs the full deterministic report, "
        "and narrates it. Pass the plain request as 'request', e.g. 'should I "
        "look at AAPL this week?'. The deterministic core still decides; the LLM "
        "only interprets and explains. Returns an error if no instrument can be "
        "identified rather than analysing a guess."
    ),
)
async def ask_ceo(request: str) -> dict[str, Any]:
    try:
        brief = await _ceo().respond(request)
    except ValueError as exc:
        return {"error": str(exc)}
    return brief.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Run an agentic CEO investigation of a free-text request: the LLM chooses "
        "and sequences the deterministic trading tools itself (analyse, risk, "
        "calendar, explain, ...), each running through the real registry, until "
        "it reaches a grounded answer or the tool-call budget is hit. The LLM "
        "orchestrates and explains; every number comes from a tool result, never "
        "the model. Only trading tools are callable, and an optional 'persona' "
        "(research | quant | critic | full) narrows the sub-agent's toolset. With "
        "no LLM configured it returns an honest 'needs an LLM' result."
    ),
)
async def investigate_ceo(
    request: str,
    persona: str | None = None,
) -> dict[str, Any]:
    investigation = await _ceo_agent().investigate(request, persona=persona)
    return investigation.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Analyze news sentiment for an instrument with a deterministic finance "
        "lexicon (NOT an LLM): fetch recent headlines, score each into a signed "
        "polarity, and fuse them into a net directional lean with a "
        "positive/negative/neutral split and matched terms. Returns NEWS/SENTIMENT "
        "evidence, data quality and provenance. Sentiment is a derived "
        "interpretation of sourced text, never the source's own claim, and is "
        "flagged NOT reliable -- with the reason -- on MOCK headlines, too few "
        "items, or no news at all rather than fabricating a lean."
    ),
)
async def analyze_news_sentiment(
    symbol: str,
    limit: int = 12,
) -> dict[str, Any]:
    analysis = await _news().analyze(symbol, limit=limit)
    return analysis.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Look up scheduled events for an instrument within a horizon (default "
        "7 days): earnings, dividends, guidance, economic releases, corporate "
        "actions and meetings. Returns the events soonest-first, whether any is "
        "high-impact, the next event and its days away, plus data quality and "
        "provenance. A scheduled event is sourced calendar data, never a claim "
        "about what price will do, and the calendar is flagged NOT reliable -- "
        "with the reason -- on MOCK entries rather than passing synthetic events "
        "off as a real calendar. An empty calendar is an honest 'no scheduled "
        "event risk' result, not a failure."
    ),
)
async def get_market_events(
    symbol: str,
    horizon_days: int = 7,
) -> dict[str, Any]:
    calendar = await _events().get_events(symbol, horizon_days=horizon_days)
    return calendar.to_dict()


@tool(
    category="trading.analysis",
    description=(
        "Analyze company fundamentals for an instrument with a deterministic "
        "signed-factor rubric (NOT an LLM): fetch the latest reported financials "
        "(margins, growth, leverage, cash flow, valuation ratios) and score each "
        "into a net health/valuation lean with per-metric factors. Returns "
        "FUNDAMENTAL evidence, data quality and provenance. The lean is a derived "
        "interpretation over sourced figures, never the source's own claim, and "
        "is flagged NOT reliable -- with the reason -- on MOCK financials or too "
        "few reported metrics rather than fabricating a read. A missing metric is "
        "honestly absent, never a fabricated zero."
    ),
)
async def analyze_fundamentals(symbol: str) -> dict[str, Any]:
    analysis = await _fundamentals().analyze(symbol)
    return analysis.to_dict()


def _clean_key(instrument_key: str | None) -> str | None:
    """Normalise an optional instrument filter; blank means 'all instruments'."""
    if instrument_key is None:
        return None
    cleaned = instrument_key.strip()
    return cleaned or None


@tool(
    category="trading.audit",
    description=(
        "List the settled paper-trade journal entries AetherOS has persisted -- "
        "the durable trade trail, newest first, optionally filtered to one "
        "instrument key (like 'AAPL:NASDAQ') and capped at 'limit'. Each entry "
        "is one content-addressed round trip with its verbatim geometry (entry, "
        "exit, stop, target, planned risk/reward), realised P/L and net P/L, and "
        "its provenance. Unlike the within-session prediction trail, this one "
        "survives a restart when the journal store is file-backed. It reports "
        "what was recorded, never re-scored; an empty trail is an honest "
        "'nothing journalled yet', not an error."
    ),
)
async def list_journal(
    instrument_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    entries = await _journal_store().list_entries(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    return {
        "count": len(entries),
        "entries": [entry.to_dict() for entry in entries],
    }


@tool(
    category="trading.audit",
    description=(
        "List the predictions AetherOS has recorded this session -- the auditable "
        "section-8 contract of every trading report it produced, newest first, "
        "optionally filtered to one instrument key (like 'AAPL:NASDAQ') and capped "
        "at 'limit'. Each entry carries the recommendation (including an honest "
        "'no_trade'), direction, confidence, horizon, any calibrated probability "
        "and its source tier. This reads an in-process, within-session audit trail "
        "(it does not survive a restart -- durable storage is not yet built) and "
        "reports predictions as they were recorded, never re-scored or upgraded."
    ),
)
async def list_predictions(
    instrument_key: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    records = await _prediction_store().list_records(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    return {
        "count": len(records),
        "predictions": [record.to_dict() for record in records],
    }


@tool(
    category="trading.audit",
    description=(
        "Evaluate the track record of the predictions recorded this session: "
        "resolve each recorded prediction against the market data that has since "
        "unfolded and summarise them into directional accuracy, coverage and -- "
        "when the predictions carried calibrated probabilities -- Brier score and "
        "expected calibration error, optionally scoped to one instrument key and "
        "capped at 'limit'. This is an on-demand read (NOT a continuous monitoring "
        "loop): it stores nothing and learns nothing. A prediction whose horizon "
        "has not elapsed is PENDING and one that cannot be located is UNRESOLVABLE "
        "-- neither is scored -- and a thin sample or one resolved on MOCK data is "
        "reported but flagged NOT a reliable track record. An empty history is an "
        "honest 'nothing to measure yet', not an error."
    ),
)
async def evaluate_track_record(
    instrument_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    performance = await _track_record().evaluate(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    return performance.to_dict()


@tool(
    category="trading.audit",
    description=(
        "Run one monitoring sweep over the recorded predictions: resolve the "
        "outstanding ones against the freshest market data, partition them into "
        "resolved / pending / unresolvable, and summarise the resolved batch into "
        "a track record (optionally scoped to one instrument_key, capped at "
        "limit). This is a single bounded 'Observe Result -> Evaluate' pass, not a "
        "running background loop. PENDING/UNRESOLVABLE outcomes are surfaced and a "
        "thin or MOCK sample is reported but never called a reliable track record."
    ),
)
async def run_monitoring_pass(
    instrument_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    report = await _monitoring().run_once(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    return report.to_dict()


def _scheduler_state(scheduler) -> dict[str, Any]:
    return {
        "running": scheduler.is_running,
        "enabled": scheduler.enabled,
        "interval_seconds": scheduler.interval_seconds,
    }


@tool(
    category="trading.audit",
    description=(
        "Start the autonomous monitoring loop: it runs one bounded monitoring "
        "sweep every configured interval. It only starts when the loop is enabled "
        "in configuration (TRADING_MONITOR_ENABLED); otherwise it reports "
        "started=false and stays off. Returns the loop state (running/enabled/"
        "interval). This is bounded, opt-in autonomy -- not a tight loop."
    ),
)
async def start_monitoring_loop() -> dict[str, Any]:
    scheduler = _monitoring_scheduler()
    started = await scheduler.start()
    state = _scheduler_state(scheduler)
    state["started"] = started
    return state


@tool(
    category="trading.audit",
    description=(
        "Stop the autonomous monitoring loop if it is running (cleanly cancels "
        "the background task). Idempotent -- safe to call when the loop is not "
        "running. Returns the loop state."
    ),
)
async def stop_monitoring_loop() -> dict[str, Any]:
    scheduler = _monitoring_scheduler()
    await scheduler.stop()
    return {"stopped": True, **_scheduler_state(scheduler)}


@tool(
    category="trading.audit",
    description=(
        "Report the autonomous monitoring loop's state: whether it is currently "
        "running, whether it is enabled in configuration, and the sweep interval "
        "in seconds."
    ),
)
async def monitoring_loop_status() -> dict[str, Any]:
    return _scheduler_state(_monitoring_scheduler())


@tool(
    category="trading.audit",
    description=(
        "List the resolved prediction outcomes accumulated in the durable outcome "
        "store (optionally scoped to one instrument_key, capped at limit, newest "
        "first). Unlike evaluate_track_record -- which re-resolves predictions "
        "live each call -- this reads the outcomes that monitoring sweeps have "
        "already recorded over time. Returns an empty list when nothing has been "
        "accumulated yet (honest, not an error)."
    ),
)
async def list_outcomes(
    instrument_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    outcomes = await _outcome_store().list_outcomes(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    return {"count": len(outcomes), "outcomes": [o.to_dict() for o in outcomes]}


@tool(
    category="trading.audit",
    description=(
        "Aggregate the ACCUMULATED resolved outcomes in the durable store into a "
        "track record: directional accuracy, coverage, mean realised return and "
        "calibration (Brier/ECE) over the outcomes monitoring sweeps have recorded "
        "over time (optionally scoped to one instrument_key). Unlike "
        "evaluate_track_record it does not re-resolve live; it reads history. A "
        "thin or MOCK-sourced sample is reported but never called a reliable track "
        "record, and an empty history is a valid 'nothing to measure yet' summary."
    ),
)
async def evaluate_outcome_history(
    instrument_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    outcomes = await _outcome_store().list_outcomes(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    performance = await _performance().summarize(outcomes)
    return performance.to_dict()


@tool(
    category="trading.audit",
    description=(
        "Audit how well the system's PAST calibrated probabilities actually "
        "matched the outcomes that unfolded (optionally scoped to one "
        "instrument_key): realised Brier vs a base-rate baseline, ECE, a "
        "reliability curve, and an over-/under-confident read -- and, only when "
        "the live track record is large enough to trust, a PROPOSED recalibration "
        "correction fit on that history. This is the honest first step of "
        "learning from history: it measures and proposes, it does NOT modify the "
        "live probability model. A thin or MOCK-sourced record proposes no "
        "correction (overfit guard), and an empty history is an honest 'cannot "
        "measure yet'."
    ),
)
async def audit_calibration(
    instrument_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    audit = await _calibration_history().audit(
        instrument_key=_clean_key(instrument_key),
        limit=limit,
    )
    return audit.to_dict()


@tool(
    category="trading.audit",
    description=(
        "Recalibrate an instrument's live probability using the accumulated "
        "outcome history: estimate P(up) now, derive a recalibration correction "
        "from past predictions validated OUT-OF-SAMPLE on a held-out tail, and "
        "apply it ONLY if it beats the uncorrected holdout Brier and the sample "
        "clears the floor. Returns the raw and corrected P(up) and whether the "
        "correction was trusted. An untrusted or thin history leaves the "
        "probability unchanged -- it never manufactures confidence."
    ),
)
async def recalibrate_probability(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    estimate = await _probability().estimate(data)
    correction = await _calibration_history().derive_correction()
    raw_p_up = estimate.p_up
    corrected = correction.apply(raw_p_up)
    applied = correction.trusted and corrected != raw_p_up
    return {
        "instrument_key": data.instrument.key,
        "timeframe": timeframe,
        "estimate_is_reliable": estimate.is_reliable,
        "raw_p_up": round(raw_p_up, 6),
        "corrected_p_up": round(corrected, 6),
        "applied": applied,
        "correction": correction.to_dict(),
    }


# ==========================================================
# Chart engine (Phase 3)
# ==========================================================


def _chart_service() -> ChartService:
    return container.resolve(ChartService)


def _chart_capture() -> ChartCaptureService | None:
    from ..core.container import container as _container

    if not _container.has(ChartCaptureService):
        return None
    return _container.resolve(ChartCaptureService)


@tool(
    category="trading.charts",
    description=(
        "Project an instrument's candle series into chart data: the "
        "timeframe, the computed time and price ranges, data quality and "
        "provenance, plus a small tail of recent (time, OHLCV) points. Use "
        "this when the chart-level view of the series is needed rather than "
        "indicator values."
    ),
)
async def build_chart_data(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    chart = _chart_service().build_chart(data)
    payload = chart.to_dict()
    payload["quality"] = data.quality.to_dict()
    return payload


@tool(
    category="trading.charts",
    description=(
        "Synchronize multiple charts onto their common time window: fetches "
        "each symbol's candles at one timeframe and trims every series to "
        "the shared range so comparisons are aligned. Symbols without "
        "overlap are reported with a limitation instead of being silently "
        "dropped or fabricated."
    ),
)
async def synchronize_charts(
    symbols: str | list[str],
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    wanted = _split_symbols(symbols)
    if not wanted:
        return {"error": "No symbols supplied.", "charts": {}}
    if len(wanted) > 8:
        return {
            "error": "Synchronize at most 8 symbols per call.",
            "charts": {},
        }

    market_data = _market_data()
    series: dict[str, Any] = {}
    failures: list[dict[str, str]] = []
    for symbol in wanted:
        try:
            data = await market_data.get_candles(symbol, timeframe, limit=limit)
            series[symbol] = data
        except TradingError as exc:
            failures.append({"symbol": symbol, "error": exc.message})

    synced = _chart_service().synchronize(series)
    charts: dict[str, Any] = {}
    for key, entry in synced.items():
        chart = entry["chart"]
        charts[key] = {
            "synced": entry["synced"],
            "limitation": entry.get("limitation"),
            "window": entry.get("window"),
            "chart": chart.to_dict() if chart is not None else None,
        }
    return {
        "timeframe": timeframe,
        "requested": len(wanted),
        "aligned": sum(1 for c in charts.values() if c["synced"]),
        "fetch_failures": failures,
        "charts": charts,
    }


@tool(
    category="trading.charts",
    description=(
        "Capture a screenshot of a chart from the screen -- the whole primary "
        "monitor by default, or a region when left/top/width/height are all "
        "given. Returns the image dimensions and capture metadata, not the "
        "pixels. Requires the desktop screen-capture subsystem; on a headless "
        "machine it fails with an explicit error instead of returning a fake "
        "frame."
    ),
)
async def capture_chart_screenshot(
    left: int | None = None,
    top: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    capture = _chart_capture()
    if capture is None:
        return {
            "error": (
                "Screen capture is unavailable (headless machine or the "
                "desktop subsystem is not registered); no screenshot was "
                "taken."
            ),
        }
    metadata = await capture.save_screenshot(
        left=left, top=top, width=width, height=height
    )
    return metadata


@tool(
    category="trading.charts",
    description=(
        "Read a chart screenshot with vision and return the observations as "
        "trading evidence with provenance: captures the screen (or region), "
        "runs OCR text recognition and object detection over the frame, and "
        "returns one observation per read (label, confidence, bounding box, "
        "source, timestamp) plus VISUAL evidence for the strong reads. Visual "
        "uncertainty stays visible -- every item keeps its backend confidence "
        "verbatim, capped below API-derived numbers in fusion. Requires the "
        "desktop screen-capture and vision subsystems; degrades honestly when "
        "either is absent."
    ),
)
async def observe_chart(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 200,
    left: int | None = None,
    top: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    from ..vision.controller import VisionService

    capture = _chart_capture()
    if capture is None:
        return {
            "error": (
                "Screen capture is unavailable (headless machine or the "
                "desktop subsystem is not registered); no screenshot was "
                "taken."
            ),
        }
    if not container.has(VisionService):
        return {
            "error": (
                "Vision is unavailable (the vision subsystem is not "
                "registered); the screenshot was not taken."
            ),
        }
    data = await _market_data().get_candles(symbol, timeframe, limit=limit)
    image, shot = await capture.capture_chart(
        left=left, top=top, width=width, height=height
    )
    vision: VisionService = container.resolve(VisionService)
    service = _visual()
    text_blocks: list = []
    detections: list = []
    if vision.has_ocr:
        try:
            text_blocks = await vision.read_text(image)
        except Exception:
            text_blocks = []
    if vision.has_detector:
        try:
            detections = await vision.detect_objects(image)
        except Exception:
            detections = []
    text_obs = service.observe_text(text_blocks, instrument_key=data.instrument.key)
    object_obs = service.observe_objects(detections, instrument_key=data.instrument.key)
    observations = text_obs + object_obs
    evidence = service.to_evidence(observations, data)
    return {
        "symbol": data.instrument.key,
        "timeframe": data.timeframe.value,
        "screenshot": shot,
        "capabilities": vision.capabilities(),
        "observations": [obs.to_dict() for obs in observations],
        "evidence": [item.to_dict() for item in evidence],
    }


@tool(
    category="trading.analysis",
    description=(
        "Build the unified hybrid chart context for an instrument: the "
        "deterministic numerical read (market state, chart projection, "
        "technical state, news, fundamentals, decision metadata) side by side "
        "with the visual read (chart screenshot metadata, vision capabilities, "
        "observations, VISUAL evidence, and a visual-vs-numerical cross-check). "
        "This is the single context the LLM reasons over when it must weigh "
        "BOTH numbers and pictures. Provenance-weighted trust is embedded: "
        "visual reads stay UNCERTAIN guesses with verbatim confidence and "
        "capped weight, never equal to API-derived facts, and a conflict is "
        "reported with the numerical read governing. By default the visual "
        "sections degrade honestly when screen capture or vision is absent "
        "(pass 'with_visual=False' to skip the screenshot attempt entirely). "
        "This is analysis, not a guarantee."
    ),
)
async def build_hybrid_context(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
    with_visual: bool = True,
) -> dict[str, Any]:
    context = await _hybrid().build(
        symbol, timeframe, limit=limit, with_visual=with_visual
    )
    return context.to_dict()


@tool(
    category="trading.audit",
    description=(
        "List the trading alerts the alert engine has recently generated "
        "(newest last, optionally capped by 'limit'). Alerts come from the "
        "shared event stream -- a generated signal, a reliable news read, a "
        "risk-limit breach, a regime change, an event-risk warning -- or from "
        "an armed price watch. Each carries its kind, severity, instrument, "
        "and whether its basis was reliable. Returns an empty list when nothing "
        "has fired yet (honest, not an error). This reads what already fired; "
        "it raises nothing."
    ),
)
async def list_alerts(limit: int | None = None) -> dict[str, Any]:
    alerts = _alerts().recent(limit=limit)
    return {
        "count": len(alerts),
        "channels": [c.value for c in _alerts().router.channels],
        "alerts": [alert.to_dict() for alert in alerts],
    }


@tool(
    category="trading.audit",
    description=(
        "Arm a one-shot price watch: fetch the latest quote for an instrument "
        "and, ONLY if the live price has crossed the given threshold (above when "
        "'direction' is 'above', below when 'below'), raise a price alert and "
        "route it to the configured channels. Returns whether the threshold was "
        "crossed, the quote's price and provenance, and -- when it fired -- the "
        "alert and its per-channel delivery results. A MOCK-tier or unreliable "
        "quote never raises an alert (synthetic numbers do not page a desk); the "
        "result says so. This is a notification, not an order, and reaches no "
        "broker."
    ),
)
async def watch_price(
    symbol: str,
    threshold: float,
    direction: str = "above",
) -> dict[str, Any]:
    side = direction.strip().lower()
    if side not in ("above", "below"):
        raise TradingError(
            f"Unknown direction '{direction}'. Use 'above' or 'below'.",
            hint="direction is the side of the threshold to watch.",
        )
    quote = await _market_data().get_quote(symbol)
    price = quote.price
    crossed = price >= threshold if side == "above" else price <= threshold
    result: dict[str, Any] = {
        "symbol": quote.instrument.key,
        "price": price,
        "threshold": threshold,
        "direction": side,
        "crossed": crossed,
        "provenance": quote.provenance.to_dict(),
        "fired": False,
        "reason": "",
        "alert": None,
        "deliveries": [],
    }
    if not crossed:
        result["reason"] = "Price has not crossed the watched threshold."
        return result
    if quote.provenance.is_mock:
        result["reason"] = (
            "Quote is MOCK-tier; a synthetic price never raises a real alert."
        )
        return result
    alert = price_alert(
        instrument_key=quote.instrument.key,
        price=price,
        threshold=threshold,
        direction=side,
    )
    deliveries = await _alerts().raise_alert(alert)
    result["fired"] = True
    result["reason"] = "Threshold crossed on a live quote; alert raised."
    result["alert"] = alert.to_dict()
    result["deliveries"] = [d.to_dict() for d in deliveries]
    return result
