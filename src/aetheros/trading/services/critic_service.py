"""
Critic service -- the deterministic go/no-go validator.

The critic's job is to *challenge* a proposed signal, not to restate it. Given
the deterministic :class:`TradingAnalysis` (and, when available, the
:class:`RiskAssessment` and a :class:`BacktestResult`), it runs a fixed battery
of checks and returns a :class:`CriticReport` with one of three verdicts:

* ``INSUFFICIENT_EVIDENCE`` -- there was not enough sound input to judge at all
  (mock/unusable data, no directional side, or too little reliable evidence);
* ``REJECT`` -- the case was judged and found wanting (the evidence contradicts
  the fused direction, the risk/reward is too thin, or the signal has no
  measured edge over its historical baseline);
* ``APPROVE`` -- every hard check passed.

Every check and the final verdict are deterministic functions of the inputs --
no LLM, no fabrication (spec sections 5, 28). Preferring
``INSUFFICIENT_EVIDENCE`` over a manufactured ``APPROVE`` is the spec's core
honesty rule (section 61). When a calibrated :class:`ProbabilityEstimate` is
supplied, the ``probability_calibration`` check uses it: a *reliable* model that
contradicts the fused direction is a hard FAIL (the critic can reject a signal
its own quant layer disagrees with), while an unreliable/mock estimate only
WARNs and an absent one is ``SKIPPED`` -- never silently passed. When a
:class:`NewsAnalysis` is supplied, the ``news_sentiment`` check corroborates the
fused direction with soft, advisory weight: a reliable agreeing read PASSes, and
an opposing, non-committal, unreliable or mock read only WARNs -- sentiment never
single-handedly vetoes a signal. When an :class:`EventCalendar` is supplied, the
``event_risk`` check guards against trading into a scheduled catalyst (spec
section 5): a *reliable* calendar carrying a high-impact event inside its horizon
is a hard FAIL (the critic can reject a signal that runs straight into earnings
or a major release), a reliable calendar with no high-impact event PASSes, and an
unreliable/mock calendar only WARNs -- a synthetic calendar must never veto a
real signal. An absent calendar, or one for a not-yet-directional signal, is
``SKIPPED`` -- never silently passed. When a :class:`FundamentalAnalysis` is
supplied, the ``fundamentals`` check corroborates the fused direction with the
same soft, advisory weight as news: fundamentals sit on a longer horizon than a
short-term technical call, so a reliable agreeing read PASSes while an opposing,
non-committal, unreliable or mock read only WARNs -- a fundamental view never
single-handedly vetoes a near-term signal.
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.analysis import TradingAnalysis
from ..domain.backtest import BacktestResult
from ..domain.breakout import BreakoutAnalysis
from ..domain.divergence import DivergenceAnalysis
from ..domain.critique import CriticCheck, CriticReport
from ..domain.enums import (
    CheckStatus,
    CriticVerdict,
    Direction,
    MarketRegime,
    SourceTier,
    TimeframeAlignment,
)
from ..domain.event_calendar import EventCalendar
from ..domain.evidence import Evidence
from ..domain.fundamentals import FundamentalAnalysis
from ..domain.news import NewsAnalysis
from ..domain.probability import ProbabilityEstimate
from ..domain.provenance import Provenance
from ..domain.anomaly import AnomalyAnalysis
from ..domain.historical_analogue import HistoricalAnalogueAnalysis
from ..domain.macro import MacroContext
from ..domain.multi_timeframe import MultiTimeframeAnalysis
from ..domain.regime import RegimeAnalysis
from ..domain.relative_strength import RelativeStrengthAnalysis
from ..domain.risk import RiskAssessment
from ..events import SignalCritiqued

logger = get_logger("trading.critic")


class CriticService:
    """Deterministic adversarial validation of a proposed directional signal."""

    def __init__(
        self,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings
        self._event_bus = event_bus

    async def critique(
        self,
        analysis: TradingAnalysis,
        *,
        risk: RiskAssessment | None = None,
        backtest: BacktestResult | None = None,
        probability: ProbabilityEstimate | None = None,
        news: NewsAnalysis | None = None,
        calendar: EventCalendar | None = None,
        fundamentals: FundamentalAnalysis | None = None,
        regime: RegimeAnalysis | None = None,
        relative_strength: RelativeStrengthAnalysis | None = None,
        anomaly: AnomalyAnalysis | None = None,
        historical_analogue: HistoricalAnalogueAnalysis | None = None,
        macro: MacroContext | None = None,
        multi_timeframe: MultiTimeframeAnalysis | None = None,
        divergence: DivergenceAnalysis | None = None,
        breakout: BreakoutAnalysis | None = None,
    ) -> CriticReport:
        report = self._critique(
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
        await self._emit(report)
        return report

    # ------------------------------------------------------------------

    def _critique(
        self,
        analysis: TradingAnalysis,
        *,
        risk: RiskAssessment | None,
        backtest: BacktestResult | None,
        probability: ProbabilityEstimate | None = None,
        news: NewsAnalysis | None = None,
        calendar: EventCalendar | None = None,
        fundamentals: FundamentalAnalysis | None = None,
        regime: RegimeAnalysis | None = None,
        relative_strength: RelativeStrengthAnalysis | None = None,
        anomaly: AnomalyAnalysis | None = None,
        historical_analogue: HistoricalAnalogueAnalysis | None = None,
        macro: MacroContext | None = None,
        multi_timeframe: MultiTimeframeAnalysis | None = None,
        divergence: DivergenceAnalysis | None = None,
        breakout: BreakoutAnalysis | None = None,
    ) -> CriticReport:
        s = self._settings
        checks: list[CriticCheck] = []
        limitations = list(analysis.limitations)

        provenance = Provenance(
            source=analysis.provenance.source,
            tier=(
                SourceTier.MOCK
                if analysis.provenance.is_mock
                else SourceTier.DERIVED
            ),
            detail="deterministic signal critique",
        )

        # ---- Gate checks: failing any of these means we cannot judge -----
        data_usable = analysis.quality.usable
        checks.append(
            CriticCheck(
                name="data_quality",
                status=(
                    CheckStatus.PASS
                    if analysis.quality.ok
                    else CheckStatus.FAIL
                    if not data_usable
                    else CheckStatus.WARN
                ),
                detail=(
                    f"Data quality is '{analysis.quality.status.value}'."
                    + ("" if analysis.quality.ok else " " + "; ".join(analysis.quality.issues))
                ),
            )
        )

        is_mock = analysis.provenance.is_mock
        checks.append(
            CriticCheck(
                name="data_source",
                status=CheckStatus.FAIL if is_mock else CheckStatus.PASS,
                detail=(
                    "Data is synthetic MOCK; a signal on it verifies the machinery, "
                    "not a real edge."
                    if is_mock
                    else f"Data source tier is '{analysis.provenance.tier.value}'."
                ),
            )
        )

        direction = analysis.direction
        directional = direction in (Direction.UP, Direction.DOWN)
        checks.append(
            CriticCheck(
                name="direction_defined",
                status=(
                    CheckStatus.PASS
                    if directional
                    else CheckStatus.FAIL
                    if direction is Direction.UNKNOWN
                    else CheckStatus.WARN
                ),
                detail=f"Fused direction is '{direction.value}'.",
            )
        )

        reliable_evidence = [e for e in analysis.evidence if e.is_reliable]
        n_reliable = len(reliable_evidence)
        min_ev = s.TRADING_CRITIC_MIN_EVIDENCE
        checks.append(
            CriticCheck(
                name="evidence_sufficiency",
                status=(
                    CheckStatus.FAIL
                    if n_reliable == 0
                    else CheckStatus.WARN
                    if n_reliable < min_ev
                    else CheckStatus.PASS
                ),
                detail=(
                    f"{n_reliable} reliable evidence item(s) "
                    f"(of {len(analysis.evidence)} total; need >= {min_ev})."
                ),
            )
        )

        # ---- Judgement checks: only meaningful once a directional case exists.
        checks.append(self._conflict_check(analysis, reliable_evidence, directional))
        checks.append(self._risk_reward_check(risk, directional))
        checks.append(self._historical_check(backtest))
        checks.append(self._calibration_check(probability, analysis, directional))
        checks.append(self._news_check(news, analysis, directional))
        checks.append(self._fundamentals_check(fundamentals, analysis, directional))
        checks.append(self._regime_check(regime, analysis, directional))
        checks.append(
            self._relative_strength_check(relative_strength, analysis, directional)
        )
        checks.append(self._anomaly_check(anomaly, analysis, directional))
        checks.append(
            self._historical_analogue_check(historical_analogue, analysis, directional)
        )
        checks.append(self._macro_context_check(macro, analysis, directional))
        checks.append(
            self._multi_timeframe_check(multi_timeframe, directional)
        )
        checks.append(self._divergence_check(divergence, analysis, directional))
        checks.append(self._breakout_check(breakout, analysis, directional))
        checks.append(self._event_risk_check(calendar, directional))

        verdict, reasons = self._decide(
            checks,
            directional=directional,
            direction=direction,
            is_mock=is_mock,
            data_usable=data_usable,
            n_reliable=n_reliable,
        )

        return CriticReport(
            instrument=analysis.instrument,
            direction=direction,
            verdict=verdict,
            checks=tuple(checks),
            reasons=tuple(reasons),
            quality=analysis.quality,
            provenance=provenance,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    def _conflict_check(
        self,
        analysis: TradingAnalysis,
        reliable_evidence: list[Evidence],
        directional: bool,
    ) -> CriticCheck:
        """Do the reliable evidence items actually back the fused direction?"""
        if not directional:
            return CriticCheck(
                name="signal_conflict",
                status=CheckStatus.SKIPPED,
                detail="No directional side to corroborate.",
            )
        agree = sum(
            e.weight for e in reliable_evidence if e.direction is analysis.direction
        )
        against = sum(
            e.weight
            for e in reliable_evidence
            if e.direction in (Direction.UP, Direction.DOWN)
            and e.direction is not analysis.direction
        )
        total = agree + against
        if total <= 0.0:
            return CriticCheck(
                name="signal_conflict",
                status=CheckStatus.WARN,
                detail="No directional evidence weight to corroborate the call.",
            )
        agreement = agree / total
        min_agreement = self._settings.TRADING_CRITIC_MIN_AGREEMENT
        status = (
            CheckStatus.PASS
            if agreement > min_agreement
            else CheckStatus.FAIL
        )
        return CriticCheck(
            name="signal_conflict",
            status=status,
            detail=(
                f"{agreement:.0%} of directional evidence weight backs "
                f"'{analysis.direction.value}' (need > {min_agreement:.0%})."
            ),
        )

    def _risk_reward_check(
        self, risk: RiskAssessment | None, directional: bool
    ) -> CriticCheck:
        if risk is None:
            return CriticCheck(
                name="risk_reward",
                status=CheckStatus.SKIPPED,
                detail="No risk assessment supplied.",
            )
        if not directional:
            return CriticCheck(
                name="risk_reward",
                status=CheckStatus.SKIPPED,
                detail="No directional side to risk-plan.",
            )
        rr = risk.risk_reward_ratio
        min_reward = self._settings.TRADING_RISK_MIN_REWARD
        if rr is None:
            return CriticCheck(
                name="risk_reward",
                status=CheckStatus.WARN,
                detail="No risk/reward geometry could be derived (no stop/target).",
            )
        status = CheckStatus.PASS if rr >= min_reward else CheckStatus.FAIL
        return CriticCheck(
            name="risk_reward",
            status=status,
            detail=f"Risk/reward {rr:g} : 1 (need >= {min_reward:g}).",
        )

    def _historical_check(self, backtest: BacktestResult | None) -> CriticCheck:
        if backtest is None:
            return CriticCheck(
                name="historical_reliability",
                status=CheckStatus.SKIPPED,
                detail="No backtest supplied.",
            )
        if not backtest.is_reliable:
            return CriticCheck(
                name="historical_reliability",
                status=CheckStatus.WARN,
                detail=(
                    "Backtest is not reliable (mock data or too thin a sample); "
                    "it cannot confirm a real edge."
                ),
            )
        acc = backtest.directional_accuracy
        base = backtest.base_rate_up
        if acc is None or base is None:
            return CriticCheck(
                name="historical_reliability",
                status=CheckStatus.WARN,
                detail="Backtest produced no comparable accuracy/baseline.",
            )
        # A signal that does not beat the naive up-rate baseline has no edge.
        status = CheckStatus.PASS if acc > base else CheckStatus.FAIL
        return CriticCheck(
            name="historical_reliability",
            status=status,
            detail=(
                f"Directional accuracy {acc:.1%} vs. {base:.1%} baseline "
                f"({'beats' if acc > base else 'does not beat'} it)."
            ),
        )

    def _calibration_check(
        self,
        probability: ProbabilityEstimate | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does a calibrated probability corroborate the fused direction?

        An absent estimate is SKIPPED (nothing to check); an unreliable/mock one
        WARNs (it cannot confirm an edge); a reliable one that contradicts the
        fused side is a hard FAIL, and one that agrees PASSes. This is the only
        place the deterministic core lets a *validated* probability veto a signal
        (spec sections 5, 6, 28).
        """
        if probability is None:
            return CriticCheck(
                name="probability_calibration",
                status=CheckStatus.SKIPPED,
                detail="No probability estimate supplied; calibration cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="probability_calibration",
                status=CheckStatus.SKIPPED,
                detail="No directional side to corroborate with a probability.",
            )
        if not probability.is_reliable:
            reason = (
                probability.limitations[0]
                if probability.limitations
                else "estimate did not pass its out-of-sample reliability gate"
            )
            return CriticCheck(
                name="probability_calibration",
                status=CheckStatus.WARN,
                detail=(
                    f"Probability estimate is not reliable ({reason}); it cannot "
                    "confirm a calibrated edge."
                ),
            )

        p_up = probability.p_up
        prob_dir = probability.direction
        if prob_dir is analysis.direction:
            return CriticCheck(
                name="probability_calibration",
                status=CheckStatus.PASS,
                detail=(
                    f"Calibrated P(up)={p_up:.0%} agrees with the fused "
                    f"'{analysis.direction.value}' call (holdout Brier "
                    f"{probability.holdout_metrics.brier} vs baseline "
                    f"{probability.baseline_brier})."
                    if probability.holdout_metrics is not None
                    else f"Calibrated P(up)={p_up:.0%} agrees with the fused "
                    f"'{analysis.direction.value}' call."
                ),
            )
        if prob_dir in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="probability_calibration",
                status=CheckStatus.FAIL,
                detail=(
                    f"Calibrated model points '{prob_dir.value}' (P(up)={p_up:.0%}) "
                    f"against the fused '{analysis.direction.value}' call."
                ),
            )
        # Reliable but non-committal (inside the dead-band around 0.5).
        return CriticCheck(
            name="probability_calibration",
            status=CheckStatus.WARN,
            detail=(
                f"Calibrated model is non-committal (P(up)={p_up:.0%}); it neither "
                f"confirms nor contradicts the '{analysis.direction.value}' call."
            ),
        )

    def _news_check(
        self,
        news: NewsAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does the news/sentiment read corroborate the fused direction?

        News sentiment is *soft, advisory* context, deliberately weaker than the
        technical evidence: an absent read is SKIPPED and a not-yet-directional
        signal is SKIPPED (nothing to corroborate); an unreliable/mock/thin read
        WARNs (it cannot confirm a real catalyst); a reliable read that opposes or
        is non-committal on the fused side WARNs rather than vetoes; only a
        reliable read that agrees PASSes. This check NEVER hard-FAILs -- sentiment
        may flag concern but never single-handedly rejects a signal (spec sections
        5, 9, 28).
        """
        if news is None:
            return CriticCheck(
                name="news_sentiment",
                status=CheckStatus.SKIPPED,
                detail="No news/sentiment read supplied; sentiment cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="news_sentiment",
                status=CheckStatus.SKIPPED,
                detail="No directional side to corroborate with news sentiment.",
            )
        if not news.is_reliable:
            reason = (
                news.limitations[0]
                if news.limitations
                else "sentiment read did not clear its reliability gate"
            )
            return CriticCheck(
                name="news_sentiment",
                status=CheckStatus.WARN,
                detail=(
                    f"News sentiment is not reliable ({reason}); it cannot confirm "
                    "a real catalyst."
                ),
            )

        if news.direction is analysis.direction:
            return CriticCheck(
                name="news_sentiment",
                status=CheckStatus.PASS,
                detail=(
                    f"News sentiment is '{news.direction.value}' "
                    f"(mean score {news.sentiment_score:+.2f} over "
                    f"{news.item_count} headlines), agreeing with the fused "
                    f"'{analysis.direction.value}' call."
                ),
            )
        if news.direction in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="news_sentiment",
                status=CheckStatus.WARN,
                detail=(
                    f"News sentiment points '{news.direction.value}' against the "
                    f"fused '{analysis.direction.value}' call; treat the signal "
                    "with added caution."
                ),
            )
        return CriticCheck(
            name="news_sentiment",
            status=CheckStatus.WARN,
            detail=(
                f"News sentiment is non-directional ('{news.direction.value}'); it "
                f"neither confirms nor contradicts the '{analysis.direction.value}' "
                "call."
            ),
        )

    def _fundamentals_check(
        self,
        fundamentals: FundamentalAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does the fundamental health/valuation read corroborate the direction?

        Fundamentals are *soft, advisory* context on a longer horizon than a
        short-term technical directional call: a company's health can diverge
        from its near-term price setup, so a disagreement is a caution, not a
        contradiction. An absent read is SKIPPED and a not-yet-directional signal
        is SKIPPED (nothing to corroborate); an unreliable/mock/thin read WARNs
        (it cannot confirm a real fundamental picture); a reliable read that
        opposes or is non-committal on the fused side WARNs rather than vetoes;
        only a reliable read that agrees PASSes. This check NEVER hard-FAILs --
        fundamentals may flag concern but never single-handedly reject a near-term
        signal (spec sections 5, 9, 28).
        """
        if fundamentals is None:
            return CriticCheck(
                name="fundamentals",
                status=CheckStatus.SKIPPED,
                detail="No fundamental read supplied; company health cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="fundamentals",
                status=CheckStatus.SKIPPED,
                detail="No directional side to corroborate with fundamentals.",
            )
        if not fundamentals.is_reliable:
            reason = (
                fundamentals.limitations[0]
                if fundamentals.limitations
                else "fundamental read did not clear its reliability gate"
            )
            return CriticCheck(
                name="fundamentals",
                status=CheckStatus.WARN,
                detail=(
                    f"Fundamentals are not reliable ({reason}); they cannot confirm "
                    "the company's health picture."
                ),
            )

        if fundamentals.direction is analysis.direction:
            return CriticCheck(
                name="fundamentals",
                status=CheckStatus.PASS,
                detail=(
                    f"Fundamentals lean '{fundamentals.direction.value}' "
                    f"(health score {fundamentals.health_score:+.2f} over "
                    f"{fundamentals.scored_metric_count} scored metric(s)), agreeing "
                    f"with the fused '{analysis.direction.value}' call."
                ),
            )
        if fundamentals.direction in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="fundamentals",
                status=CheckStatus.WARN,
                detail=(
                    f"Fundamentals lean '{fundamentals.direction.value}' against the "
                    f"fused '{analysis.direction.value}' call; treat the signal with "
                    "added caution."
                ),
            )
        return CriticCheck(
            name="fundamentals",
            status=CheckStatus.WARN,
            detail=(
                f"Fundamentals are non-directional ('{fundamentals.direction.value}'); "
                f"they neither confirm nor contradict the '{analysis.direction.value}' "
                "call."
            ),
        )

    def _regime_check(
        self,
        regime: RegimeAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Is the fused direction compatible with the current market regime?

        The market regime is *situational context*, not a prediction, so it is
        soft, advisory weight like news and fundamentals -- it NEVER hard-FAILs.
        An absent read is SKIPPED, a not-yet-directional signal is SKIPPED, and
        an UNKNOWN regime is SKIPPED (nothing to weigh against); an
        unreliable/mock read WARNs (it cannot confirm the real market character).
        For a reliable, known regime: a trend that agrees with the fused side
        PASSes; a trend that opposes it WARNs (a counter-trend call carries added
        risk); and a ranging or volatile tape WARNs (directional signals are
        least reliable when the market has no persistent trend) -- caution the
        critic surfaces but never a veto (spec sections 5, 8, 28).
        """
        if regime is None:
            return CriticCheck(
                name="market_regime",
                status=CheckStatus.SKIPPED,
                detail="No market-regime read supplied; regime compatibility cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="market_regime",
                status=CheckStatus.SKIPPED,
                detail="No directional side to weigh against the market regime.",
            )
        if regime.regime is MarketRegime.UNKNOWN:
            return CriticCheck(
                name="market_regime",
                status=CheckStatus.SKIPPED,
                detail="Market regime is undetermined; nothing to weigh the signal against.",
            )
        if not regime.is_reliable:
            reason = (
                regime.limitations[0]
                if regime.limitations
                else "regime read did not clear its reliability gate"
            )
            return CriticCheck(
                name="market_regime",
                status=CheckStatus.WARN,
                detail=(
                    f"Market regime is not reliable ({reason}); it cannot confirm "
                    "the signal's market context."
                ),
            )

        if regime.regime.is_trending:
            if regime.direction is analysis.direction:
                return CriticCheck(
                    name="market_regime",
                    status=CheckStatus.PASS,
                    detail=(
                        f"Market regime is '{regime.regime.value}' "
                        f"(ADX {regime.adx}), aligned with the fused "
                        f"'{analysis.direction.value}' call."
                    ),
                )
            return CriticCheck(
                name="market_regime",
                status=CheckStatus.WARN,
                detail=(
                    f"Market regime is '{regime.regime.value}' against the fused "
                    f"'{analysis.direction.value}' call; a counter-trend signal "
                    "carries added risk."
                ),
            )
        if regime.regime is MarketRegime.VOLATILE:
            return CriticCheck(
                name="market_regime",
                status=CheckStatus.WARN,
                detail=(
                    f"Market regime is volatile (ATR {regime.atr_pct} of price); "
                    "directional signals are least reliable in a whipsawing tape."
                ),
            )
        return CriticCheck(
            name="market_regime",
            status=CheckStatus.WARN,
            detail=(
                f"Market regime is range-bound (ADX {regime.adx}); a directional "
                f"'{analysis.direction.value}' call sits against a sideways tape."
            ),
        )

    def _relative_strength_check(
        self,
        relative_strength: RelativeStrengthAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does the instrument's strength vs. its benchmark back the direction?

        Relative strength (the "positive/negative sector strength" line of spec
        sections 2 and 27) is *soft, advisory* context on the same footing as
        news, fundamentals and regime -- it NEVER hard-FAILs. An absent read is
        SKIPPED, a not-yet-directional signal is SKIPPED, and an UNKNOWN read is
        SKIPPED (nothing to weigh); an unreliable/mock read WARNs (it cannot
        confirm real sector strength). For a reliable, determinate read: a lean
        that agrees with the fused side PASSes, while an opposing or in-line
        (SIDEWAYS) lean WARNs -- caution the critic surfaces, never a veto (spec
        sections 5, 9, 28).
        """
        if relative_strength is None:
            return CriticCheck(
                name="relative_strength",
                status=CheckStatus.SKIPPED,
                detail=(
                    "No relative-strength read supplied; sector strength cannot "
                    "be checked."
                ),
            )
        if not directional:
            return CriticCheck(
                name="relative_strength",
                status=CheckStatus.SKIPPED,
                detail="No directional side to corroborate with relative strength.",
            )
        if relative_strength.direction is Direction.UNKNOWN:
            return CriticCheck(
                name="relative_strength",
                status=CheckStatus.SKIPPED,
                detail=(
                    "Relative strength is undetermined; nothing to weigh the "
                    "signal against."
                ),
            )
        if not relative_strength.is_reliable:
            reason = (
                relative_strength.limitations[0]
                if relative_strength.limitations
                else "relative-strength read did not clear its reliability gate"
            )
            return CriticCheck(
                name="relative_strength",
                status=CheckStatus.WARN,
                detail=(
                    f"Relative strength is not reliable ({reason}); it cannot "
                    "confirm real sector strength."
                ),
            )

        rel = relative_strength.relative_return
        rel_pct = f"{rel * 100:+.2f}%" if rel is not None else "n/a"
        if relative_strength.direction is analysis.direction:
            return CriticCheck(
                name="relative_strength",
                status=CheckStatus.PASS,
                detail=(
                    f"Instrument is '{relative_strength.direction.value}' vs. "
                    f"{relative_strength.benchmark_key} ({rel_pct} excess), agreeing "
                    f"with the fused '{analysis.direction.value}' call."
                ),
            )
        if relative_strength.direction in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="relative_strength",
                status=CheckStatus.WARN,
                detail=(
                    f"Instrument is '{relative_strength.direction.value}' vs. "
                    f"{relative_strength.benchmark_key} ({rel_pct} excess) against the "
                    f"fused '{analysis.direction.value}' call; treat the signal with "
                    "added caution."
                ),
            )
        return CriticCheck(
            name="relative_strength",
            status=CheckStatus.WARN,
            detail=(
                f"Instrument tracks {relative_strength.benchmark_key} in-line "
                f"({rel_pct} excess); relative strength neither confirms nor "
                f"contradicts the '{analysis.direction.value}' call."
            ),
        )

    def _anomaly_check(
        self,
        anomaly: AnomalyAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does a statistical last-bar anomaly bear on the fused direction?

        A detected outlier (spec sections 5, 9, 27) is *soft, advisory* context
        on the same footing as news, fundamentals, regime and relative strength
        -- it NEVER hard-FAILs. An absent read is SKIPPED, a not-yet-directional
        signal is SKIPPED, and an UNKNOWN read is SKIPPED (too thin to judge); an
        unreliable/mock read WARNs. For a reliable read: a quiet tape (no anomaly)
        PASSes as a clean, expected state; a directional outlier that agrees with
        the fused side PASSes (an unusual move confirming the call); a directional
        outlier that opposes it WARNs (an unusual move against the call carries
        added risk); and a non-directional (volume-only) spike WARNs -- unusual
        activity the critic surfaces but never a veto.
        """
        if anomaly is None:
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.SKIPPED,
                detail="No anomaly read supplied; unusual activity cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.SKIPPED,
                detail="No directional side to weigh a statistical anomaly against.",
            )
        if anomaly.direction is Direction.UNKNOWN:
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.SKIPPED,
                detail="Anomaly read is undetermined; nothing to weigh the signal against.",
            )
        if not anomaly.is_reliable:
            reason = (
                anomaly.limitations[0]
                if anomaly.limitations
                else "anomaly read did not clear its reliability gate"
            )
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.WARN,
                detail=(
                    f"Anomaly read is not reliable ({reason}); it cannot confirm "
                    "real unusual activity."
                ),
            )

        if not anomaly.is_anomalous:
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.PASS,
                detail=(
                    f"No statistical anomaly on the last bar (vs its "
                    f"{anomaly.lookback}-bar baseline); the tape is behaving normally."
                ),
            )
        if anomaly.direction is analysis.direction:
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.PASS,
                detail=(
                    f"A statistical anomaly leans '{anomaly.direction.value}', "
                    f"confirming the fused '{analysis.direction.value}' call."
                ),
            )
        if anomaly.direction in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="anomaly",
                status=CheckStatus.WARN,
                detail=(
                    f"A statistical anomaly leans '{anomaly.direction.value}' against "
                    f"the fused '{analysis.direction.value}' call; an unusual move the "
                    "other way carries added risk."
                ),
            )
        return CriticCheck(
            name="anomaly",
            status=CheckStatus.WARN,
            detail=(
                "A statistical anomaly (unusual volume) fired without a directional "
                f"move; it neither confirms nor contradicts the "
                f"'{analysis.direction.value}' call."
            ),
        )

    def _historical_analogue_check(
        self,
        historical: HistoricalAnalogueAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does the historical-analogue lean corroborate the fused direction?

        The analogue read (spec sections 1, 7, 15, 27) is *soft, advisory*
        context on the same footing as news, fundamentals, regime, relative
        strength and anomaly -- it NEVER hard-FAILs. An absent read is SKIPPED, a
        not-yet-directional signal is SKIPPED, and an UNKNOWN read is SKIPPED (too
        little history to judge); an unreliable/mock read WARNs. For a reliable
        read: a lean that agrees with the fused side PASSes (past analogues broke
        the same way), while an opposing or inconclusive (SIDEWAYS) lean WARNs --
        a caution the critic surfaces, never a veto. A historical tendency is not
        a guarantee the present will repeat.
        """
        if historical is None:
            return CriticCheck(
                name="historical_analogue",
                status=CheckStatus.SKIPPED,
                detail=(
                    "No historical-analogue read supplied; past-setup behaviour "
                    "cannot be checked."
                ),
            )
        if not directional:
            return CriticCheck(
                name="historical_analogue",
                status=CheckStatus.SKIPPED,
                detail="No directional side to corroborate with historical analogues.",
            )
        if historical.direction is Direction.UNKNOWN:
            return CriticCheck(
                name="historical_analogue",
                status=CheckStatus.SKIPPED,
                detail=(
                    "Historical-analogue read is undetermined; nothing to weigh the "
                    "signal against."
                ),
            )
        if not historical.is_reliable:
            reason = (
                historical.limitations[0]
                if historical.limitations
                else "analogue read did not clear its reliability gate"
            )
            return CriticCheck(
                name="historical_analogue",
                status=CheckStatus.WARN,
                detail=(
                    f"Historical analogues are not reliable ({reason}); they cannot "
                    "confirm a real tendency."
                ),
            )

        up_rate = historical.up_rate
        rate = f"{up_rate * 100:.0f}%" if up_rate is not None else "n/a"
        if historical.direction is analysis.direction:
            return CriticCheck(
                name="historical_analogue",
                status=CheckStatus.PASS,
                detail=(
                    f"Across {historical.neighbors} analogues {rate} rose, agreeing "
                    f"with the fused '{analysis.direction.value}' call (a past "
                    "tendency, not a guarantee)."
                ),
            )
        if historical.direction in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="historical_analogue",
                status=CheckStatus.WARN,
                detail=(
                    f"Historical analogues lean '{historical.direction.value}' "
                    f"({rate} rose) against the fused '{analysis.direction.value}' "
                    "call; treat the signal with added caution."
                ),
            )
        return CriticCheck(
            name="historical_analogue",
            status=CheckStatus.WARN,
            detail=(
                f"Historical analogues are inconclusive ({rate} rose); they neither "
                f"confirm nor contradict the '{analysis.direction.value}' call."
            ),
        )

    def _macro_context_check(
        self,
        macro: MacroContext | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Is the fused direction with or against the broad-market posture?

        The macro backdrop (spec sections 2, 5, 27) is *soft, advisory* context on
        the same footing as news, fundamentals, regime, relative strength,
        anomaly and historical analogue -- it NEVER hard-FAILs. An absent read is
        SKIPPED, a not-yet-directional signal is SKIPPED, and an UNKNOWN posture
        is SKIPPED (nothing to weigh); an unreliable/mock read WARNs. For a
        reliable read: a posture whose bias agrees with the fused side PASSes (the
        market backdrop supports the call), while an opposing posture (trading
        against the tape) or a NEUTRAL/range-bound market WARNs -- a caution the
        critic surfaces, never a veto.
        """
        if macro is None:
            return CriticCheck(
                name="macro_context",
                status=CheckStatus.SKIPPED,
                detail="No macro-context read supplied; the market backdrop cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="macro_context",
                status=CheckStatus.SKIPPED,
                detail="No directional side to weigh against the market backdrop.",
            )
        if macro.direction is Direction.UNKNOWN:
            return CriticCheck(
                name="macro_context",
                status=CheckStatus.SKIPPED,
                detail="Broad-market posture is undetermined; nothing to weigh the signal against.",
            )
        if not macro.is_reliable:
            reason = (
                macro.limitations[0]
                if macro.limitations
                else "macro read did not clear its reliability gate"
            )
            return CriticCheck(
                name="macro_context",
                status=CheckStatus.WARN,
                detail=(
                    f"Macro context is not reliable ({reason}); it cannot confirm "
                    "the market backdrop."
                ),
            )

        posture = macro.posture.value
        if macro.direction is analysis.direction:
            return CriticCheck(
                name="macro_context",
                status=CheckStatus.PASS,
                detail=(
                    f"Broad market is '{posture}', a backdrop that supports the "
                    f"fused '{analysis.direction.value}' call."
                ),
            )
        if macro.direction in (Direction.UP, Direction.DOWN):
            return CriticCheck(
                name="macro_context",
                status=CheckStatus.WARN,
                detail=(
                    f"Broad market is '{posture}' against the fused "
                    f"'{analysis.direction.value}' call; trading against the tape "
                    "carries added risk."
                ),
            )
        return CriticCheck(
            name="macro_context",
            status=CheckStatus.WARN,
            detail=(
                f"Broad market is '{posture}' (range-bound); it offers no tailwind "
                f"for the '{analysis.direction.value}' call."
            ),
        )

    def _multi_timeframe_check(
        self,
        mtf: MultiTimeframeAnalysis | None,
        directional: bool,
    ) -> CriticCheck:
        """Does the higher timeframe confirm the base-timeframe call?

        Multi-timeframe alignment (spec section 5) is *soft, advisory* context on
        the same footing as the other context layers -- it NEVER hard-FAILs. An
        absent read is SKIPPED, a not-yet-directional signal is SKIPPED, and an
        UNKNOWN alignment is SKIPPED (nothing to weigh); an unreliable/mock read
        WARNs. For a reliable read: a CONFIRMED alignment PASSes (the higher
        timeframe backs the call), while a CONFLICT (a counter-trend call) or a
        NEUTRAL/trendless higher timeframe WARNs -- a caution the critic surfaces,
        never a veto. The alignment is already measured against the fused call
        (its base read is this same analysis).
        """
        if mtf is None:
            return CriticCheck(
                name="multi_timeframe",
                status=CheckStatus.SKIPPED,
                detail="No multi-timeframe read supplied; higher-timeframe confirmation cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="multi_timeframe",
                status=CheckStatus.SKIPPED,
                detail="No directional side to confirm across timeframes.",
            )
        if mtf.alignment is TimeframeAlignment.UNKNOWN:
            return CriticCheck(
                name="multi_timeframe",
                status=CheckStatus.SKIPPED,
                detail="Multi-timeframe alignment is undetermined; nothing to weigh.",
            )
        if not mtf.is_reliable:
            reason = (
                mtf.limitations[0]
                if mtf.limitations
                else "multi-timeframe read did not clear its reliability gate"
            )
            return CriticCheck(
                name="multi_timeframe",
                status=CheckStatus.WARN,
                detail=(
                    f"Multi-timeframe read is not reliable ({reason}); it cannot "
                    "confirm the higher-timeframe trend."
                ),
            )

        if mtf.alignment is TimeframeAlignment.CONFIRMED:
            return CriticCheck(
                name="multi_timeframe",
                status=CheckStatus.PASS,
                detail=(
                    f"The {mtf.higher_timeframe} trend '{mtf.higher_direction.value}' "
                    f"confirms the {mtf.base_timeframe} '{mtf.base_direction.value}' call."
                ),
            )
        if mtf.alignment is TimeframeAlignment.CONFLICT:
            return CriticCheck(
                name="multi_timeframe",
                status=CheckStatus.WARN,
                detail=(
                    f"The {mtf.higher_timeframe} trend '{mtf.higher_direction.value}' "
                    f"conflicts with the {mtf.base_timeframe} "
                    f"'{mtf.base_direction.value}' call; a counter-trend call carries "
                    "added risk."
                ),
            )
        return CriticCheck(
            name="multi_timeframe",
            status=CheckStatus.WARN,
            detail=(
                f"The {mtf.higher_timeframe} timeframe is trendless "
                f"('{mtf.higher_direction.value}'); it offers no higher-timeframe "
                "confirmation."
            ),
        )

    def _divergence_check(
        self,
        divergence: DivergenceAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does a momentum divergence bear on the fused direction?

        Divergence (spec section 5) is *soft, advisory* context on the same
        footing as the other context layers -- it NEVER hard-FAILs. An absent
        read is SKIPPED, a not-yet-directional signal is SKIPPED, and an UNKNOWN
        read is SKIPPED (too few pivots to judge); an unreliable/mock read WARNs.
        For a reliable read: no divergence PASSes (nothing weakening the trend); a
        divergence whose lean agrees with the fused side PASSes (momentum is
        turning the way of the call); a divergence against the fused side WARNs (a
        weakening-trend warning the other way) -- a caution the critic surfaces,
        never a veto.
        """
        if divergence is None:
            return CriticCheck(
                name="divergence",
                status=CheckStatus.SKIPPED,
                detail="No divergence read supplied; momentum divergence cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="divergence",
                status=CheckStatus.SKIPPED,
                detail="No directional side to weigh a momentum divergence against.",
            )
        if divergence.direction is Direction.UNKNOWN:
            return CriticCheck(
                name="divergence",
                status=CheckStatus.SKIPPED,
                detail="Divergence read is undetermined; nothing to weigh the signal against.",
            )
        if not divergence.is_reliable:
            reason = (
                divergence.limitations[0]
                if divergence.limitations
                else "divergence read did not clear its reliability gate"
            )
            return CriticCheck(
                name="divergence",
                status=CheckStatus.WARN,
                detail=(
                    f"Divergence read is not reliable ({reason}); it cannot confirm "
                    "a real momentum divergence."
                ),
            )

        if not divergence.has_divergence:
            return CriticCheck(
                name="divergence",
                status=CheckStatus.PASS,
                detail=(
                    f"No momentum divergence against {divergence.oscillator}; "
                    "nothing weakening the trend."
                ),
            )
        if divergence.direction is analysis.direction:
            return CriticCheck(
                name="divergence",
                status=CheckStatus.PASS,
                detail=(
                    f"A momentum divergence leans '{divergence.direction.value}', "
                    f"turning the way of the fused '{analysis.direction.value}' call."
                ),
            )
        return CriticCheck(
            name="divergence",
            status=CheckStatus.WARN,
            detail=(
                f"A momentum divergence leans '{divergence.direction.value}' against "
                f"the fused '{analysis.direction.value}' call; momentum may be "
                "weakening the other way."
            ),
        )

    def _breakout_check(
        self,
        breakout: BreakoutAnalysis | None,
        analysis: TradingAnalysis,
        directional: bool,
    ) -> CriticCheck:
        """Does a channel breakout bear on the fused direction?

        A breakout (spec section 5) is *soft, advisory* context on the same
        footing as the other context layers -- it NEVER hard-FAILs. An absent
        read is SKIPPED, a not-yet-directional signal is SKIPPED, and an UNKNOWN
        read is SKIPPED (too thin to judge); an unreliable/mock read WARNs. For a
        reliable read: no breakout PASSes (nothing to flag); a breakout whose
        direction agrees with the fused side PASSes (price action confirms the
        call -- more so when volume-confirmed); a breakout against the fused side
        WARNs -- a caution the critic surfaces, never a veto.
        """
        if breakout is None:
            return CriticCheck(
                name="breakout",
                status=CheckStatus.SKIPPED,
                detail="No breakout read supplied; channel breakouts cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="breakout",
                status=CheckStatus.SKIPPED,
                detail="No directional side to weigh a channel breakout against.",
            )
        if breakout.direction is Direction.UNKNOWN:
            return CriticCheck(
                name="breakout",
                status=CheckStatus.SKIPPED,
                detail="Breakout read is undetermined; nothing to weigh the signal against.",
            )
        if not breakout.is_reliable:
            reason = (
                breakout.limitations[0]
                if breakout.limitations
                else "breakout read did not clear its reliability gate"
            )
            return CriticCheck(
                name="breakout",
                status=CheckStatus.WARN,
                detail=(
                    f"Breakout read is not reliable ({reason}); it cannot confirm "
                    "a real breakout."
                ),
            )

        if not breakout.has_breakout:
            return CriticCheck(
                name="breakout",
                status=CheckStatus.PASS,
                detail=(
                    f"No channel breakout (last close inside the "
                    f"{breakout.lookback}-bar range); nothing to flag."
                ),
            )
        confirmed = " (volume-confirmed)" if breakout.volume_confirmed else ""
        if breakout.direction is analysis.direction:
            return CriticCheck(
                name="breakout",
                status=CheckStatus.PASS,
                detail=(
                    f"A '{breakout.direction.value}' channel breakout{confirmed} "
                    f"confirms the fused '{analysis.direction.value}' call."
                ),
            )
        return CriticCheck(
            name="breakout",
            status=CheckStatus.WARN,
            detail=(
                f"A '{breakout.direction.value}' channel breakout{confirmed} runs "
                f"against the fused '{analysis.direction.value}' call; treat the "
                "signal with added caution."
            ),
        )

    def _event_risk_check(
        self,
        calendar: EventCalendar | None,
        directional: bool,
    ) -> CriticCheck:
        """Is the signal running into a scheduled, high-impact event?

        Unlike news sentiment, a *reliable* calendar is allowed to hard-FAIL: a
        high-impact event (earnings, a major economic release) inside the horizon
        is exactly the case the spec's section 5 REJECT example describes. But the
        veto only fires on trustworthy data -- an absent calendar is SKIPPED, a
        not-yet-directional signal is SKIPPED (nothing to guard), an
        unreliable/mock calendar WARNs (synthetic events must never reject a real
        signal), a reliable calendar with no high-impact event PASSes, and only a
        reliable calendar carrying a high-impact event FAILs (spec sections 5, 28).
        """
        if calendar is None:
            return CriticCheck(
                name="event_risk",
                status=CheckStatus.SKIPPED,
                detail="No event calendar supplied; upcoming-event risk cannot be checked.",
            )
        if not directional:
            return CriticCheck(
                name="event_risk",
                status=CheckStatus.SKIPPED,
                detail="No directional side to guard against event risk.",
            )
        if not calendar.is_reliable:
            reason = (
                calendar.limitations[0]
                if calendar.limitations
                else "calendar did not clear its reliability gate"
            )
            return CriticCheck(
                name="event_risk",
                status=CheckStatus.WARN,
                detail=(
                    f"Event calendar is not reliable ({reason}); it cannot confirm "
                    "or rule out scheduled event risk."
                ),
            )
        if calendar.has_high_impact:
            nxt = calendar.next_event
            when = (
                f" ({nxt.event_type.value} in ~{nxt.days_until(calendar.reference_time):.1f}d)"
                if nxt is not None
                else ""
            )
            return CriticCheck(
                name="event_risk",
                status=CheckStatus.FAIL,
                detail=(
                    f"A high-impact scheduled event falls within the "
                    f"{calendar.horizon_days}-day horizon{when}; trading into it "
                    "carries event risk the historical signal cannot price."
                ),
            )
        return CriticCheck(
            name="event_risk",
            status=CheckStatus.PASS,
            detail=(
                f"No high-impact event within the {calendar.horizon_days}-day "
                f"horizon ({calendar.event_count} scheduled event(s))."
            ),
        )

    @staticmethod
    def _decide(
        checks: list[CriticCheck],
        *,
        directional: bool,
        direction: Direction,
        is_mock: bool,
        data_usable: bool,
        n_reliable: int,
    ) -> tuple[CriticVerdict, list[str]]:
        """
        Fold the checks into a verdict. Insufficient-evidence gates come first:
        without sound, directional, corroborated input there is nothing to judge.
        Only then can a judged case be REJECTed on a hard failure.
        """
        reasons: list[str] = []

        if not data_usable:
            reasons.append("Data is missing or invalid; nothing can be judged.")
        if is_mock:
            reasons.append("Data is synthetic MOCK; no real signal to validate.")
        if direction is Direction.UNKNOWN:
            reasons.append("No directional lean was formed from the evidence.")
        elif not directional:
            reasons.append(
                f"Direction is '{direction.value}': no tradable side to validate."
            )
        if n_reliable == 0:
            reasons.append("No reliable evidence supports any call.")

        if reasons:
            return CriticVerdict.INSUFFICIENT_EVIDENCE, reasons

        # We have a sound, directional, evidence-backed case -- now judge it.
        failed = [c for c in checks if c.status is CheckStatus.FAIL]
        if failed:
            reasons = [f"{c.name}: {c.detail}" for c in failed]
            return CriticVerdict.REJECT, reasons

        warned = [c for c in checks if c.status is CheckStatus.WARN]
        reasons = [f"{c.name}: {c.detail}" for c in warned]
        return CriticVerdict.APPROVE, reasons

    async def _emit(self, report: CriticReport) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                SignalCritiqued(
                    instrument_key=report.instrument.key,
                    direction=report.direction.value,
                    verdict=report.verdict.value,
                    approved=report.approved,
                    check_count=len(report.checks),
                    failed_checks=len(report.failed_checks),
                    source_tier=report.provenance.tier.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish SignalCritiqued")
