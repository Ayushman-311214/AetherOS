"""
Trading-decision service (spec Phase 20).

Produces the structured, explainable :class:`TradingDecision` from real
evidence: the deterministic report (market/technical/SMC/ICT read, risk
geometry, critic verdict, news, events, provenance), the strategy panel's
evaluations (the setup the decision is built from), and -- when supplied --
the hybrid context's visual read. It assembles; it computes nothing. Every
number is lifted verbatim from an already-produced object, so there is one
source of truth for the direction, the geometry and the evidence weights.

Two honesty rules are structural:

* **The decision cannot exceed its report.** Direction, confidence,
  recommendation and actionability are copied off the deterministic report;
  the decision layer never upgrades a call.
* **No decision is a valid decision.** When the evidence does not resolve to
  a tradable side, the record says so with the uncertainty stated -- never a
  fabricated side.

Nothing here can reach a broker. The decision is a record the
policy/execution layers may judge; the LLM reasons over it, and execution
remains deterministic and policy-controlled.
"""

from __future__ import annotations

from typing import Any

from ...core.logging import get_logger
from ..domain.decision import TradingDecision
from ..domain.enums import Direction, ReportRecommendation
from ..domain.explanation import Explanation
from ..domain.hybrid import HybridChartContext
from ..domain.report import TradingReport
from ..domain.strategy import StrategyEvaluation, StrategySetup
from .explanation_service import ExplanationService
from .market_data_service import MarketDataService
from .orchestration_service import OrchestrationService
from .strategy_service import StrategyService

logger = get_logger("trading.decision")


class DecisionService:
    """Structured-decision assembly over the deterministic report and panel."""

    def __init__(
        self,
        orchestration: OrchestrationService,
        market_data: MarketDataService,
        strategy: StrategyService,
        explanation: ExplanationService,
    ) -> None:
        self._orchestration = orchestration
        self._market_data = market_data
        self._strategy = strategy
        self._explanation = explanation

    async def decide(
        self,
        symbol: str,
        *,
        timeframe: str | None = None,
        limit: int | None = None,
        strategy_ids: list[str] | None = None,
        hybrid: HybridChartContext | None = None,
        report: TradingReport | None = None,
        evaluations: list[StrategyEvaluation] | None = None,
    ) -> TradingDecision:
        """
        Produce the structured decision for one analysis request.

        Runs the deterministic report and the strategy panel unless already
        supplied (tests and the hybrid path reuse a finished report rather
        than re-running the pipeline). The visual read arrives only through
        the optional hybrid context -- as a note, never as a number.
        """
        if report is None:
            report = await self._orchestration.generate_report(
                symbol, timeframe, limit=limit
            )
        if evaluations is None:
            evaluations = await self._run_panel(
                symbol, timeframe=timeframe, limit=limit, strategy_ids=strategy_ids
            )
        explanation = self._explanation.explain(report)
        setup = self._pick_setup(report, evaluations)
        return self.assemble(report, explanation, setup, evaluations, hybrid=hybrid)

    # ------------------------------------------------------------------

    async def _run_panel(
        self,
        symbol: str,
        *,
        timeframe: str | None,
        limit: int | None,
        strategy_ids: list[str] | None,
    ) -> list[StrategyEvaluation]:
        """Evaluate the strategy panel; a panel failure degrades, never sinks."""
        try:
            data = await self._market_data.get_candles(symbol, timeframe, limit=limit)
            comparison = await self._strategy.compare(
                data, strategy_ids=strategy_ids
            )
            return list(comparison.evaluations)
        except Exception:
            logger.exception("Strategy panel failed; the decision records no setup")
            return []

    # ------------------------------------------------------------------

    @staticmethod
    def assemble(
        report: TradingReport,
        explanation: Explanation,
        setup: StrategySetup | None,
        evaluations: list[StrategyEvaluation],
        *,
        hybrid: HybridChartContext | None = None,
    ) -> TradingDecision:
        """
        Lift a finished report, explanation, setup and panel into one decision.

        Pure: no I/O, no re-analysis. The setup is the highest-confidence
        firing evaluation whose side agrees with the report; anything else --
        no firing, no agreement -- is an honest no-setup decision.
        """
        market_view = DecisionService._market_view(report)
        reasoning = DecisionService._reasoning(report, explanation, setup, evaluations)
        uncertainty = DecisionService._uncertainty(report, explanation, setup, hybrid)
        visual_note = DecisionService._visual_note(report, hybrid)
        limitations = list(report.limitations)
        if hybrid is not None:
            for line in hybrid.metadata.get("limitations", ()):
                if line not in limitations:
                    limitations.append(line)

        return TradingDecision(
            instrument=report.instrument,
            timeframe_value=report.analysis.timeframe_value,
            market_view=market_view,
            strategy_id=setup.strategy_id if setup else None,
            strategy_name=setup.strategy_name if setup else None,
            setup_id=setup.setup_id or None if setup else None,
            direction=report.direction,
            confidence=report.confidence,
            recommendation=report.recommendation,
            is_actionable=report.is_actionable,
            supporting=explanation.supporting,
            contradictory=explanation.opposing,
            supporting_weight=explanation.supporting_weight,
            contradictory_weight=explanation.opposing_weight,
            net_weight=explanation.net_weight,
            entry=report.risk.entry,
            stop_loss=report.risk.stop_loss,
            take_profit=report.risk.target,
            risk_reward_ratio=report.risk.risk_reward_ratio,
            invalidation=report.risk.invalidation,
            reasoning=reasoning,
            uncertainty=tuple(uncertainty),
            critic_reasons=tuple(report.critique.reasons),
            provenance=report.provenance,
            quality=report.quality,
            limitations=tuple(limitations),
            visual_note=visual_note,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _pick_setup(
        report: TradingReport, evaluations: list[StrategyEvaluation]
    ) -> StrategySetup | None:
        """The agreeing firing setup with the strongest confidence, if any."""
        if report.direction not in (Direction.UP, Direction.DOWN):
            return None
        candidates = [
            evaluation.setup
            for evaluation in evaluations
            if evaluation.fired
            and evaluation.setup is not None
            and evaluation.setup.direction is report.direction
        ]
        if not candidates:
            return None
        order = {"very_high": 5, "high": 4, "medium": 3, "low": 2, "very_low": 1}
        candidates.sort(
            key=lambda s: order.get(s.confidence.value, 0), reverse=True
        )
        return candidates[0]

    @staticmethod
    def _market_view(report: TradingReport) -> str:
        """The backdrop in one sentence: trend, regime and key price facts."""
        structure = report.analysis.structure
        view = (
            f"{report.instrument.key} ({report.analysis.timeframe_value}): "
            f"{structure.trend.value} trend, last {report.analysis.last_price:g}."
        )
        if report.regime is not None:
            view += f" Regime: {report.regime.regime.value}."
        if structure.supports or structure.resistances:
            levels = ", ".join(
                f"{lvl.price:g}"
                for lvl in list(structure.supports)[:2]
                + list(structure.resistances)[:2]
            )
            view += f" Key levels near {levels}."
        return view

    @staticmethod
    def _reasoning(
        report: TradingReport,
        explanation: Explanation,
        setup: StrategySetup | None,
        evaluations: list[StrategyEvaluation],
    ) -> str:
        """Why this decision, from the explanation summary plus the setup."""
        parts = [explanation.summary]
        fired = sum(1 for evaluation in evaluations if evaluation.fired)
        parts.append(
            f"Strategy panel: {fired} of {len(evaluations)} fired."
        )
        if setup is not None:
            parts.append(
                f"Setup from '{setup.strategy_name}' ({setup.strategy_id}): "
                f"{setup.reasoning}"
            )
        elif report.direction in (Direction.UP, Direction.DOWN):
            parts.append(
                "No strategy setup agreed with the report's side, so the "
                "decision carries no setup -- the call rests on the fused "
                "evidence alone."
            )
        else:
            parts.append(
                "No tradable side resolved; this is an explicit no-decision."
            )
        if report.recommendation is ReportRecommendation.NO_TRADE:
            parts.append(
                "Recommendation is NO_TRADE: insufficient or unreliable "
                "evidence, and the spec prefers no trade to a fabricated one."
            )
        return " ".join(parts)

    @staticmethod
    def _uncertainty(
        report: TradingReport,
        explanation: Explanation,
        setup: StrategySetup | None,
        hybrid: HybridChartContext | None,
    ) -> list[str]:
        """What could still be wrong, in plain language."""
        items: list[str] = []
        if explanation.opposing:
            items.append(
                f"{len(explanation.opposing)} reliable item(s) oppose the call "
                f"(weight {explanation.opposing_weight:g}); see contradictory "
                "evidence."
            )
        if setup is None and report.direction in (Direction.UP, Direction.DOWN):
            items.append(
                "No strategy setup confirmed the side; the call is evidence- "
                "weighted, not setup-validated."
            )
        if not report.is_actionable:
            items.append(
                "The report is not actionable (data quality, the critic, or "
                "the risk plan held it back); acting would contradict the "
                "validation layer."
            )
        if report.probability is None:
            items.append(
                "No calibrated probability is available; the decision carries "
                "direction and confidence, not odds."
            )
        if hybrid is not None:
            cross = hybrid.visual_state.get("cross_check", {})
            if cross.get("conflict"):
                items.append(f"Visual/numerical conflict: {cross['conflict']}")
            elif hybrid.visual_state.get("screenshot") is None:
                items.append(
                    "No chart screenshot was available; the decision rests on "
                    "numbers alone."
                )
        for line in report.limitations[:3]:
            if line not in items:
                items.append(line)
        return items

    @staticmethod
    def _visual_note(
        report: TradingReport, hybrid: HybridChartContext | None
    ) -> str | None:
        """The visual read as a note -- a guess, never a number."""
        if hybrid is None:
            return None
        observations = hybrid.visual_state.get("observations", [])
        texts = [
            obs.get("label")
            for obs in observations
            if isinstance(obs, dict) and obs.get("kind") == "text"
        ]
        if hybrid.visual_state.get("screenshot") is None:
            return "No screenshot captured; no visual read."
        if not texts:
            return "Screenshot captured but vision found nothing readable."
        cross = hybrid.visual_state.get("cross_check", {})
        verdict = (
            "matches the analysed instrument"
            if cross.get("symbol_match")
            else "does not confirm the analysed instrument"
        )
        shown = ", ".join(str(text) for text in texts[:5])
        return (
            f"Chart shows [{shown}] -- {verdict}. Visual reads are UNCERTAIN "
            "and never outweigh the measured numbers."
        )

    def to_dict_context(self, decision: TradingDecision) -> dict[str, Any]:
        """The decision payload plus the trust framing any LLM reader needs."""
        payload = decision.to_dict()
        payload["trust"] = {
            "numbers_govern": (
                "Direction, confidence, geometry and weights are lifted "
                "verbatim from the deterministic report; narration must not "
                "alter them."
            ),
            "visual_is_advisory": (
                "The visual note is an UNCERTAIN read; it never equals a "
                "measured fact and never lifts the decision."
            ),
            "no_execution": (
                "This record cannot reach a broker; execution stays "
                "deterministic and policy-controlled."
            ),
        }
        return payload
