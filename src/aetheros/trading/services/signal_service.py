"""
Signal service: the Signal Engine's assembly point (spec Phase 8).

Composes the layers that already exist into candidates, then lets
:mod:`aetheros.trading.signals.gates` decide which become proposals. For each
strategy that produced a setup in the panel:

    StrategySetup  ──►  RiskService.assess(direction)  ──►  RiskAssessment
                                                                  │
    CriticService.critique(analysis, risk, ...) ──► CriticReport   │
                              │                                   │
                              └────────► gates ──► TradeSignal | None

The service holds no analytical judgement of its own -- every number is either
the risk engine's deterministic output or the critic's deterministic verdict,
and the only choice made here is *composition*. That is the §9 path in
miniature: strategy (the reading) → risk (the geometry) → validation (the
gate) → proposal. Nothing here places, sizes or submits an order; the
execution engine is a later phase and no code path in this module can reach a
broker.

Strategies whose evaluation declined produce no candidate at all -- a
candidate exists only where there was a directional reading to judge -- and
their ids are recorded in ``limitations`` so a panel run answers "which
strategies stayed out?" as well as "which fired?".

No event is published per candidate; ``SignalGenerated`` is published once
per fired signal, after all gates have passed, because that is the state
change the rest of the system could care about. (A rejected candidate changes
nothing.)
"""

from __future__ import annotations

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.analysis import TradingAnalysis
from ..domain.market_data import MarketData
from ..domain.lifecycle import SignalState
from ..domain.signal import SignalCandidate, SignalEvaluation
from ..domain.strategy import StrategySetup
from ..domain.trade import TradeSignal
from ..errors import SignalError
from ..events import SignalGenerated
from ..signals.gates import evaluate_candidate
from .critic_service import CriticService
from ..production.lifecycle_service import SignalLifecycleService
from .market_data_service import MarketDataService
from .risk_service import RiskService
from .strategy_service import StrategyService

logger = get_logger("trading.signals")


class SignalService:
    """Deterministic signal generation over a strategy panel."""

    def __init__(
        self,
        strategy: StrategyService,
        risk: RiskService,
        critic: CriticService,
        market_data: MarketDataService,
        settings: Settings,
        *,
        event_bus: EventBus | None = None,
        lifecycle: SignalLifecycleService | None = None,
    ) -> None:
        self._strategy = strategy
        self._risk = risk
        self._critic = critic
        self._market_data = market_data
        self._settings = settings
        self._event_bus = event_bus
        # Optional lifecycle tracker: when wired, each candidate advances a
        # signal's state so the CREATED → VALIDATING → APPROVED/INVALIDATED
        # trail is a first-class, audited record rather than an implicit one.
        self._lifecycle = lifecycle

    # ------------------------------------------------------------------
    # Panel run
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        symbol: str,
        *,
        timeframe: str | None = None,
        limit: int | None = None,
        account_equity: float | None = None,
        risk_pct: float | None = None,
        strategy_ids: list[str] | None = None,
    ) -> SignalEvaluation:
        """
        Run the full panel over one symbol's live data.

        Raises :class:`SignalError` when the panel could not run at all (no
        strategies registered, or the market data failed) -- a failure to
        evaluate is distinct from an honest empty result, and only the former
        is an exception.
        """
        ids = self._panel_ids(strategy_ids)

        # Fetch once and build the shared context: every candidate below
        # interprets the same reads, so any disagreement is about reading,
        # not inputs.
        data = await self._market_data.get_candles(symbol, timeframe, limit=limit)
        return await self.evaluate_data(
            data,
            account_equity=account_equity,
            risk_pct=risk_pct,
            strategy_ids=ids,
        )

    async def evaluate_data(
        self,
        data: MarketData,
        *,
        account_equity: float | None = None,
        risk_pct: float | None = None,
        strategy_ids: list[str] | None = None,
    ) -> SignalEvaluation:
        """
        Run the full panel over a *supplied* series.

        This is the symbol-free half of :meth:`evaluate`, and the reason it
        exists is that a replayed session must be able to ask the signal
        engine about a historical window it already holds. A caller that hands
        in a past-only slice gets exactly the judgement the live path gets --
        same context, same gates, same limits -- rather than a second,
        subtly different implementation of the panel loop living in the
        simulator.
        """
        registry = self._strategy.registry
        ids = self._panel_ids(strategy_ids)

        context = await self._strategy.build_context(data)
        analysis = context.analysis

        candidates: list[SignalCandidate] = []
        fired_signals: list[TradeSignal] = []
        limitations: list[str] = []

        for strategy_id in ids:
            evaluation = registry.require(strategy_id).evaluate(context)
            if evaluation.setup is None:
                limitations.append(
                    f"Strategy '{strategy_id}' produced no setup on this "
                    f"context: {evaluation.limitations[0] if evaluation.limitations else 'unspecified reason.'}"
                )
                continue

            setup = evaluation.setup
            candidate = await self._candidate(
                analysis,
                setup,
                account_equity=account_equity,
                risk_pct=risk_pct,
            )
            candidates.append(candidate)
            self._track_lifecycle(candidate)
            if candidate.signal is not None:
                fired_signals.append(candidate.signal)

        if not candidates:
            limitations.append(
                "No strategy in the panel produced a setup, so no signal "
                "candidate exists; this is the system's insufficient-evidence "
                "result, not a failure."
            )

        return SignalEvaluation(
            instrument_key=analysis.instrument.key,
            timeframe=analysis.timeframe_value,
            candidates=tuple(candidates),
            signals=tuple(fired_signals),
            provenance=analysis.provenance,
            quality=analysis.quality,
            limitations=tuple(limitations),
        )

    def _panel_ids(self, strategy_ids: list[str] | None) -> list[str]:
        """The strategies to evaluate, or an explicit error when there are none."""
        if strategy_ids is None:
            ids = list(self._strategy.registry.ids())
        else:
            ids = list(strategy_ids)
        if not ids:
            raise SignalError(
                "No strategies registered to evaluate for signal generation.",
                hint="Register strategies on the StrategyService registry first.",
            )
        return ids

    # ------------------------------------------------------------------

    async def _candidate(
        self,
        analysis: TradingAnalysis,
        setup: StrategySetup,
        *,
        account_equity: float | None,
        risk_pct: float | None,
    ) -> SignalCandidate:
        """
        One strategy's candidate: risk geometry, critic verdict, gate decision.

        The risk and critic calls are not wrapped in try/except: both fail
        loudly on bad inputs, and a silently degraded candidate would be worse
        than an exception -- the whole point of the gate sequence is that every
        proposal is fully judged before it exists.
        """
        risk = await self._risk.assess(
            analysis,
            direction=setup.direction,
            account_equity=account_equity,
            risk_pct=risk_pct,
        )
        critique = await self._critic.critique(analysis, risk=risk)

        signal, rejections = evaluate_candidate(
            setup,
            risk,
            critique,
            min_reward=self._settings.TRADING_RISK_MIN_REWARD,
        )
        candidate = SignalCandidate(
            strategy_id=setup.strategy_id,
            strategy_name=setup.strategy_name,
            category=setup.category,
            timeframe=setup.timeframe,
            direction=setup.direction,
            signal=signal,
            risk=risk,
            critique=critique,
            setup=setup,
            rejections=rejections,
            provenance=analysis.provenance,
            quality=analysis.quality,
        )
        if signal is not None:
            await self._emit(signal)
        return candidate

    def _track_lifecycle(self, candidate: SignalCandidate) -> None:
        """
        Advance the candidate's lifecycle through the gates it just passed.

        Every candidate is CREATED and moved to VALIDATING the moment it is
        judged; a fired signal then advances to APPROVED (it cleared every
        gate), while a candidate the gates stopped is INVALIDATED with the
        gate's own reason. Best-effort: a lifecycle edge case logs, never
        breaks the panel run.
        """
        if self._lifecycle is None:
            return
        instrument_key = candidate.instrument.key
        # The signal_id is the stable identity the whole lifecycle shares. A
        # fired candidate uses its TradeSignal's id; a non-fired candidate's
        # content-addressed candidate_id stands in so the trail still tracks.
        signal_id = (
            candidate.signal.signal_id
            if candidate.signal is not None
            else candidate.candidate_id
        )
        self._lifecycle.open(
            signal_id, instrument_key=instrument_key, reason="signal generated"
        )
        self._lifecycle.try_advance(
            signal_id,
            SignalState.VALIDATING,
            reason="candidate judged through the gate sequence",
            instrument_key=instrument_key,
        )
        if candidate.signal is not None:
            self._lifecycle.try_advance(
                signal_id,
                SignalState.APPROVED,
                reason="passed every signal gate",
                instrument_key=instrument_key,
            )
        else:
            self._lifecycle.try_advance(
                signal_id,
                SignalState.INVALIDATED,
                reason="; ".join(candidate.rejections)
                or "the gate sequence declined the proposal",
                instrument_key=instrument_key,
            )

    async def _emit(self, signal) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                SignalGenerated(
                    signal_id=signal.signal_id,
                    instrument_key=signal.instrument.key,
                    action=signal.action.value,
                    direction=signal.direction.value,
                    confidence=signal.confidence.value,
                    risk=signal.risk.value,
                )
            )
        except Exception:
            logger.exception("Failed to publish SignalGenerated")
