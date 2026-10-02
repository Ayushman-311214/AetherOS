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
from .domain.enums import Direction
from .errors import TradingError
from .domain.market_data import MarketData
from .indicators import core as ind
from .services.analysis_service import AnalysisService
from .services.backtest_service import BacktestService
from .services.breakout_service import BreakoutService
from .services.calendar_service import EventCalendarService
from .services.calibration_history_service import CalibrationHistoryService
from .services.ceo_agent_service import CEOAgentService
from .services.ceo_service import TradingCEOService
from .services.critic_service import CriticService
from .services.divergence_service import DivergenceService
from .services.evidence_service import EvidenceService
from .services.explanation_service import ExplanationService
from .services.fundamental_service import FundamentalAnalysisService
from .services.market_data_service import MarketDataService
from .services.market_structure_service import MarketStructureService
from .services.monitoring_service import MonitoringService
from .services.monitoring_scheduler import MonitoringScheduler
from .services.news_service import NewsSentimentService
from .services.orchestration_service import OrchestrationService
from .services.outcome_store import OutcomeStore
from .services.performance_service import PredictionPerformanceService
from .services.portfolio_service import PortfolioRiskService
from .services.prediction_store import PredictionStore
from .services.probability_service import ProbabilityService
from .services.anomaly_service import AnomalyService
from .services.historical_analogue_service import HistoricalAnalogueService
from .services.macro_service import MacroContextService
from .services.multi_timeframe_service import MultiTimeframeService
from .services.regime_service import RegimeService
from .services.scan_service import WatchlistScanService
from .services.relative_strength_service import RelativeStrengthService
from .services.risk_service import RiskService
from .services.track_record_service import PredictionTrackRecordService

# Indicators exposed by calculate_indicator and the arity of their inputs.
_PRICE_INDICATORS = {"sma", "ema", "rsi", "bollinger", "volatility", "volume_ma"}
_OHLC_INDICATORS = {"atr", "adx", "vwap", "macd"}


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


def _split_symbols(symbols: str | list[str]) -> list[str]:
    """Accept a list, or a comma/whitespace-separated string, of symbols."""
    if isinstance(symbols, str):
        return [s for s in symbols.replace(",", " ").split() if s]
    return [str(s) for s in symbols]


def _backtest() -> BacktestService:
    return container.resolve(BacktestService)


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
        "volatility, volume_ma. 'period' applies to indicators that take one."
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
    else:
        supported = sorted(_PRICE_INDICATORS | _OHLC_INDICATORS)
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
        "Produce a plain-language CEO brief for an instrument: run the full "
        "deterministic report, then have the LLM narrate it in clear prose. The "
        "deterministic core decides (direction, probability, risk, "
        "recommendation); the LLM only explains and never invents a number. The "
        "full report is embedded as the source of truth. If no LLM is configured "
        "(or it fails) the brief falls back to a deterministic templated summary "
        "rather than failing -- the core works without the LLM. A MOCK/"
        "insufficient run is narrated honestly as NO_TRADE."
    ),
)
async def brief_instrument(
    symbol: str,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict[str, Any]:
    brief = await _ceo().brief(symbol, timeframe, limit=limit)
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
