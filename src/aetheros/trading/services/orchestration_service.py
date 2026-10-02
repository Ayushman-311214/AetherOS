"""
Orchestration service -- the deterministic Trading-desk pipeline.

This is the deterministic backbone of the Trading CEO (spec sections 4, 5, 26):
it runs the honest numerical core end to end for one instrument -- analysis ->
risk -> (optional) backtest -> critic -> composed report -- and hands back a
single :class:`TradingReport`. It *orchestrates*; it contains no analytical
logic of its own, exactly as the spec demands ("The CEO should orchestrate. It
should NOT contain all analytical logic.").

Everything here is deterministic and LLM-free: the later LLM-driven CEO agent
will sit on top of this service to interpret a natural-language request and
narrate the result, but it will never replace these calculations. The pipeline
inherits every honesty guarantee of the services it composes -- mock/unusable
data flows through to a NO_TRADE recommendation, and no probability is ever
fabricated (sections 2, 3, 28, 61).
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import Direction, ReportRecommendation, SourceTier
from ..domain.instrument import Instrument
from ..domain.market_data import MarketData
from ..domain.prediction import PredictionRecord
from ..domain.provenance import Provenance
from ..domain.report import PIPELINE_VERSION, TradingReport, _PROBABILITY_LIMITATION
from ..errors import (
    AnalysisError,
    CalendarError,
    FundamentalsError,
    MarketDataError,
    NewsError,
)
from ..events import PredictionCreated, TradingReportGenerated
from .analysis_service import AnalysisService
from .backtest_service import BacktestService
from .breakout_service import BreakoutService
from .calendar_service import EventCalendarService
from .critic_service import CriticService
from .divergence_service import DivergenceService
from .fundamental_service import FundamentalAnalysisService
from .market_data_service import MarketDataService
from .news_service import NewsSentimentService
from .prediction_store import PredictionStore
from .probability_service import ProbabilityService
from .anomaly_service import AnomalyService
from .historical_analogue_service import HistoricalAnalogueService
from .macro_service import MacroContextService
from .multi_timeframe_service import MultiTimeframeService
from .regime_service import RegimeService
from .relative_strength_service import RelativeStrengthService
from .risk_service import RiskService

logger = get_logger("trading.orchestration")


class OrchestrationService:
    """Deterministic end-to-end trading-report pipeline for one instrument."""

    def __init__(
        self,
        market_data: MarketDataService,
        analysis: AnalysisService,
        risk: RiskService,
        backtest: BacktestService,
        critic: CriticService,
        settings: Settings,
        *,
        probability: ProbabilityService | None = None,
        news: NewsSentimentService | None = None,
        calendar: EventCalendarService | None = None,
        fundamentals: FundamentalAnalysisService | None = None,
        regime: RegimeService | None = None,
        relative_strength: RelativeStrengthService | None = None,
        anomaly: AnomalyService | None = None,
        historical_analogue: HistoricalAnalogueService | None = None,
        macro: MacroContextService | None = None,
        multi_timeframe: MultiTimeframeService | None = None,
        divergence: DivergenceService | None = None,
        breakout: BreakoutService | None = None,
        prediction_store: PredictionStore | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._market_data = market_data
        self._analysis = analysis
        self._risk = risk
        self._backtest = backtest
        self._critic = critic
        self._settings = settings
        self._probability = probability
        self._news = news
        self._calendar = calendar
        self._fundamentals = fundamentals
        self._regime = regime
        self._relative_strength = relative_strength
        self._anomaly = anomaly
        self._historical_analogue = historical_analogue
        self._macro = macro
        self._multi_timeframe = multi_timeframe
        self._divergence = divergence
        self._breakout = breakout
        self._prediction_store = prediction_store
        self._event_bus = event_bus

    async def generate_report(
        self,
        symbol: str | Instrument,
        timeframe: str | None = None,
        *,
        limit: int | None = None,
        direction: Direction | None = None,
        account_equity: float | None = None,
        risk_pct: float | None = None,
        run_backtest: bool = False,
    ) -> TradingReport:
        # 1. Evidence-grounded analysis (fetches candles, fuses evidence).
        analysis = await self._analysis.analyze(symbol, timeframe, limit=limit)

        # 2. Deterministic risk geometry for the (possibly overridden) side.
        risk = await self._risk.assess(
            analysis,
            direction=direction,
            account_equity=account_equity,
            risk_pct=risk_pct,
        )

        # 3. Optional walk-forward backtest -- look-ahead-safe, off by default
        #    because it re-analyses every bar and is expensive per request. A
        #    calibrated probability estimate is computed whenever the quant layer
        #    is wired; both need the raw candle series, so fetch it once.
        backtest = None
        probability = None
        horizon = self._settings.TRADING_BACKTEST_HORIZON
        need_data = (
            run_backtest
            or self._probability is not None
            or self._regime is not None
            or self._relative_strength is not None
            or self._anomaly is not None
            or self._historical_analogue is not None
            or self._divergence is not None
            or self._breakout is not None
        )
        data = (
            await self._market_data.get_candles(symbol, timeframe, limit=limit)
            if need_data
            else None
        )

        if self._probability is not None and data is not None:
            probability = await self._probability.estimate(data)

        if run_backtest and data is not None:

            async def _signal(window: MarketData) -> Direction:
                result = await self._analysis.analyze_data(window, emit=False)
                return result.direction

            backtest = await self._backtest.run(data, _signal)
            horizon = backtest.horizon

        # 3b. Optional deterministic news/sentiment read, when the layer is
        #     wired. It is advisory context for the critic and the report -- it
        #     never lifts the recommendation above the critic's verdict, and a
        #     news-fetch failure must not sink the whole report, so it degrades
        #     to "no news read" rather than raising.
        news = None
        if self._news is not None:
            try:
                news = await self._news.analyze(symbol, limit=limit)
            except NewsError:
                logger.exception("News sentiment failed; continuing without it")
                news = None

        # 3c. Optional scheduled-event / economic-calendar read, when the layer
        #     is wired. Unlike news, a *reliable* calendar with a high-impact
        #     event lets the critic veto (spec section 5), but a calendar-fetch
        #     failure must not sink the report -- it degrades to "no calendar" so
        #     the event_risk check honestly SKIPs rather than raising.
        calendar = None
        if self._calendar is not None:
            try:
                calendar = await self._calendar.get_events(symbol)
            except CalendarError:
                logger.exception("Event calendar failed; continuing without it")
                calendar = None

        # 3d. Optional deterministic fundamental read, when the layer is wired.
        #     Like news, it is soft, advisory, longer-horizon context for the
        #     critic and the report -- it never lifts the recommendation above the
        #     critic's verdict, and a fundamentals-fetch failure must not sink the
        #     report, so it degrades to "no fundamentals" rather than raising.
        fundamentals = None
        if self._fundamentals is not None:
            try:
                fundamentals = await self._fundamentals.analyze(symbol)
            except FundamentalsError:
                logger.exception("Fundamental analysis failed; continuing without it")
                fundamentals = None

        # 3e. Optional deterministic market-regime read, when the layer is wired.
        #     It reuses the candle series already fetched above (no extra I/O),
        #     is pure numerical maths, and is situational context for the critic
        #     and the report -- it is never a price prediction and never lifts the
        #     recommendation above the critic's verdict. A mock/too-thin series
        #     yields an UNKNOWN/unreliable regime rather than a fabricated one.
        regime = None
        if self._regime is not None and data is not None:
            regime = await self._regime.detect(data)

        # 3f. Optional deterministic relative-strength (sector/benchmark) read,
        #     when the layer is wired. It reuses the instrument candle series
        #     already fetched above and fetches the benchmark series once. Unlike
        #     regime it does a benchmark I/O, so -- like news/calendar/fundamentals
        #     -- a fetch failure must not sink the report: it degrades to "no
        #     relative-strength read" rather than raising. It is the spec's
        #     "positive/negative sector strength" evidence line (sections 2, 27):
        #     situational context that never lifts the recommendation above the
        #     critic's verdict, and a mock/too-thin series yields an UNKNOWN/
        #     unreliable read rather than a fabricated one.
        relative_strength = None
        if self._relative_strength is not None and data is not None:
            try:
                benchmark_data = await self._market_data.get_candles(
                    self._relative_strength.default_benchmark,
                    timeframe,
                    limit=limit,
                )
                relative_strength = self._relative_strength.analyze(data, benchmark_data)
            except MarketDataError:
                logger.exception(
                    "Relative strength failed; continuing without it"
                )
                relative_strength = None

        # 3g. Optional deterministic statistical-anomaly read, when the layer is
        #     wired. Like regime it reuses the instrument candle series already
        #     fetched above (no extra I/O) and is pure numerical maths, so it is
        #     not try/except-wrapped. It is situational context for the critic and
        #     the report -- an unusual last-bar move is a DETECTED event, never a
        #     price prediction and never lifting the recommendation above the
        #     critic's verdict. A mock/too-thin series yields an UNKNOWN/unreliable
        #     read rather than a fabricated anomaly.
        anomaly = None
        if self._anomaly is not None and data is not None:
            anomaly = self._anomaly.analyze(data)

        # 3h. Optional deterministic historical-analogue read, when the layer is
        #     wired. Like regime and anomaly it reuses the instrument candle
        #     series already fetched above (no extra I/O) and is pure numerical
        #     maths, so it is not try/except-wrapped. It is look-ahead-safe
        #     situational context for the critic and the report -- a past
        #     tendency, never a prediction, and never lifting the recommendation
        #     above the critic's verdict. A mock/too-thin series yields an
        #     UNKNOWN/unreliable read rather than a fabricated tendency.
        historical_analogue = None
        if self._historical_analogue is not None and data is not None:
            historical_analogue = self._historical_analogue.analyze(data)

        # 3i. Optional deterministic broad-market macro-context read, when the
        #     layer is wired. Like relative strength it needs the *benchmark*
        #     candle series (not the instrument's), so it fetches once and -- like
        #     the other I/O-fetching layers -- a fetch failure must not sink the
        #     report: it degrades to "no macro read" rather than raising. It is
        #     the market backdrop a single-name signal sits inside (spec sections
        #     2, 5, 27): situational context that never lifts the recommendation
        #     above the critic's verdict, and a mock/too-thin benchmark yields an
        #     UNKNOWN/unreliable posture rather than a fabricated one.
        macro = None
        if self._macro is not None:
            try:
                macro_benchmark = await self._market_data.get_candles(
                    self._macro.default_benchmark, timeframe, limit=limit
                )
                macro = await self._macro.analyze(macro_benchmark)
            except MarketDataError:
                logger.exception("Macro context failed; continuing without it")
                macro = None

        # 3j. Optional deterministic multi-timeframe confirmation, when the layer
        #     is wired. It reuses the base analysis already computed at step 1 and
        #     runs one more analysis at a higher timeframe (a second fetch), so --
        #     like the other I/O-fetching layers -- a fetch/analysis failure must
        #     not sink the report: it degrades to "no multi-timeframe read". It is
        #     situational context (spec section 5): whether the higher-timeframe
        #     trend confirms the base call, never a prediction and never lifting
        #     the recommendation above the critic's verdict.
        multi_timeframe = None
        if self._multi_timeframe is not None:
            try:
                higher_analysis = await self._analysis.analyze(
                    symbol,
                    self._multi_timeframe.default_higher_timeframe,
                    limit=limit,
                )
                multi_timeframe = self._multi_timeframe.analyze(analysis, higher_analysis)
            except (MarketDataError, AnalysisError):
                logger.exception("Multi-timeframe failed; continuing without it")
                multi_timeframe = None

        # 3k. Optional deterministic momentum-divergence read, when the layer is
        #     wired. Like regime/anomaly/historical it reuses the instrument
        #     candle series already fetched above (no extra I/O) and is pure
        #     numerical maths, so it is not try/except-wrapped. It is situational
        #     context (spec section 5): a weakening-trend warning, never a price
        #     prediction and never lifting the recommendation above the critic's
        #     verdict. A mock/too-thin series yields an UNKNOWN/unreliable read.
        divergence = None
        if self._divergence is not None and data is not None:
            divergence = self._divergence.analyze(data)

        # 3l. Optional deterministic channel-breakout read, when the layer is
        #     wired. Like regime/anomaly/historical/divergence it reuses the
        #     instrument candle series already fetched above (no extra I/O) and is
        #     pure numerical maths, so it is not try/except-wrapped. It is
        #     price-action context (spec section 5): a breakout/breakdown of the
        #     recent range, never a price prediction and never lifting the
        #     recommendation above the critic's verdict.
        breakout = None
        if self._breakout is not None and data is not None:
            breakout = self._breakout.analyze(data)

        # 4. Adversarial go/no-go verdict over everything gathered so far.
        critique = await self._critic.critique(
            analysis,
            risk=risk,
            backtest=backtest,
            probability=probability,
            news=news,
            calendar=calendar,
            fundamentals=fundamentals,
            regime=regime,
            relative_strength=relative_strength,
            anomaly=anomaly,
            historical_analogue=historical_analogue,
            macro=macro,
            multi_timeframe=multi_timeframe,
            divergence=divergence,
            breakout=breakout,
        )

        report = TradingReport(
            analysis=analysis,
            risk=risk,
            critique=critique,
            backtest=backtest,
            probability=probability,
            news=news,
            calendar=calendar,
            fundamentals=fundamentals,
            regime=regime,
            relative_strength=relative_strength,
            anomaly=anomaly,
            historical_analogue=historical_analogue,
            macro=macro,
            multi_timeframe=multi_timeframe,
            divergence=divergence,
            breakout=breakout,
            recommendation=ReportRecommendation.from_verdict(critique.verdict),
            horizon=horizon,
            provenance=Provenance(
                source=analysis.provenance.source,
                tier=SourceTier.MOCK if analysis.provenance.is_mock else SourceTier.DERIVED,
                detail="deterministic orchestrated trading report",
            ),
            limitations=self._aggregate_limitations(
                analysis, risk, backtest, critique, probability, news, calendar,
                fundamentals, regime, relative_strength, anomaly, historical_analogue,
                macro, multi_timeframe, divergence, breakout,
            ),
            pipeline_version=PIPELINE_VERSION,
        )
        await self._emit(report)
        await self._record_prediction(report)
        return report

    # ------------------------------------------------------------------

    async def _record_prediction(self, report: TradingReport) -> None:
        """
        Capture the report's section-8 prediction contract: announce it on the
        bus and persist it to the audit store when one is wired.

        Both are audit side-effects on an already-produced report. Building the
        record, announcing it and storing it are each guarded so that a failure
        in any of them is logged and swallowed -- it can never sink a report that
        was produced honestly (sections 8, 16, 19, 28, 31). The prediction is
        announced whether or not a store is wired: it was created regardless of
        where (or whether) it is saved.
        """
        try:
            record = PredictionRecord.from_report(report)
        except Exception:
            logger.exception("Failed to build a PredictionRecord from the report")
            return

        await self._announce_prediction(record)

        if self._prediction_store is None:
            return
        try:
            await self._prediction_store.record(record)
        except Exception:
            logger.exception("Failed to record prediction to the audit store")

    async def _announce_prediction(self, record: PredictionRecord) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                PredictionCreated(
                    prediction_id=record.id,
                    instrument_key=record.instrument_key,
                    timeframe=record.timeframe,
                    recommendation=record.recommendation,
                    direction=record.direction,
                    confidence=record.confidence,
                    is_actionable=record.is_actionable,
                    probability_up=record.probability_up,
                    horizon_bars=record.horizon_bars,
                    model_pipeline=record.model_pipeline,
                    source_tier=record.source_tier,
                    is_mock=record.is_mock,
                )
            )
        except Exception:
            logger.exception("Failed to publish PredictionCreated")

    @staticmethod
    def _aggregate_limitations(
        analysis, risk, backtest, critique, probability=None, news=None, calendar=None,
        fundamentals=None, regime=None, relative_strength=None, anomaly=None,
        historical_analogue=None, macro=None, multi_timeframe=None, divergence=None,
        breakout=None,
    ) -> tuple[str, ...]:
        """
        Union every stage's limitations, de-duplicated and order-preserving. The
        standing "no calibrated probability" note is appended only when no
        reliable estimate was surfaced, so the omission is visible in the final
        report rather than silently absent.
        """
        seen: dict[str, None] = {}
        for source in (
            analysis, risk, backtest, critique, probability, news, calendar,
            fundamentals, regime, relative_strength, anomaly, historical_analogue,
            macro, multi_timeframe, divergence, breakout,
        ):
            if source is None:
                continue
            for lim in source.limitations:
                seen.setdefault(lim, None)
        if probability is None or not probability.is_reliable:
            seen.setdefault(_PROBABILITY_LIMITATION, None)
        return tuple(seen.keys())

    async def _emit(self, report: TradingReport) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                TradingReportGenerated(
                    instrument_key=report.instrument.key,
                    timeframe=report.analysis.timeframe_value,
                    recommendation=report.recommendation.value,
                    direction=report.direction.value,
                    confidence=report.confidence.value,
                    verdict=report.critique.verdict.value,
                    is_actionable=report.is_actionable,
                    source_tier=report.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish TradingReportGenerated")
