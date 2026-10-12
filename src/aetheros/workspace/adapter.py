"""
The intelligence -> workspace adapter.

Bridges the live trading-intelligence system into ``WorkspaceState`` so the
panels show *real* data. Three responsibilities, all writing state and never
producing intelligence:

* **Event -> EventRow** -- subscribe to the shared ``EventBus`` and turn each
  emitted event into a display row (name, instrument, detail, timestamp,
  ``is_mock``). The event payload is read verbatim; nothing is inferred.
* **Read -> state fields** -- store the latest ``to_dict()`` payloads from the
  report / signal assessment / market-intel / heatmap so the panels can read
  them. The adapter carries them verbatim; it computes nothing.
* **Logging -> LogLine** -- a ``logging.Handler`` that captures the *existing*
  log stream into the LOGS ring buffer. It does not create a second logging
  system; it taps the one that already exists.

The adapter is the same seam a future GUI plugs into: it produces
``WorkspaceState``, which the terminal renders -- and which any other renderer
could consume unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..runtime.events.event_bus import EventBus
from ..runtime.events.events import Event
from ..trading.events import LIQUIDITY_EVENT_TYPES
from .state import AgentRow, EventRow, LogLine, SystemMetric, WorkspaceState

logger = logging.getLogger("aetheros.workspace")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


#: The event names the EVENTS panel highlights (liquidity + pipeline events).
_INTERESTING = frozenset(
    {
        "LiquidityReplenished", "LiquiditySwept", "LiquidityAbsorbed",
        "LiquidityConsumed", "LiquidityZoneCreated", "LiquidityZoneWeakened",
        "LiquidityZoneInvalidated", "LiquidityImbalanceChanged",
        "MarketRegimeChanged", "MarketRegimeDetected",
        "SignalGenerated", "SignalCritiqued",
        "PredictionCreated", "PredictionResolved",
        "AnalysisCompleted", "ProbabilityEstimated",
        "MarketDataReceived", "CandleClosed",
    }
)


class WorkspaceAdapter:
    """
    Writes live intelligence into ``WorkspaceState``.

    ``event_bus`` is subscribed to so the events panel streams real events;
    when it is ``None`` the adapter only writes what the caller feeds it (the
    panels still render, honestly empty). Subscription is best-effort -- a bus
    that can't be subscribed to doesn't break the workspace.
    """

    def __init__(
        self,
        state: WorkspaceState,
        *,
        event_bus: EventBus | None = None,
    ) -> None:
        self._state = state
        self._event_bus = event_bus
        self._subscribed = False
        self._subscribed_types: tuple = ()

    async def start(self) -> None:
        """
        Subscribe to the shared event bus (best-effort).

        The bus dispatches by exact event type, so the adapter subscribes its
        handler to each concrete trading event class it wants to show -- the
        liquidity events, the pipeline events and the market-data events the
        EVENTS panel highlights.
        """
        if self._event_bus is None or self._subscribed:
            return
        try:
            from ..trading.events import (
                AnalysisCompleted,
                BacktestCompleted,
                CandleClosed,
                FundamentalsAnalyzed,
                LiquidityAbsorbed,
                LiquidityConsumed,
                LiquidityImbalanceChanged,
                LiquidityReplenished,
                LiquidityRemoved,
                LiquiditySwept,
                LiquidityZoneCreated,
                LiquidityZoneInvalidated,
                LiquidityZoneWeakened,
                MarketDataReceived,
                MarketDataUpdated,
                MarketEventsDetected,
                MarketRegimeChanged,
                MarketRegimeDetected,
                NewsSentimentAnalyzed,
                PositionClosed,
                PredictionCreated,
                PredictionPerformanceEvaluated,
                PredictionResolved,
                ProbabilityEstimated,
                RiskAssessed,
                SignalCritiqued,
                SignalGenerated,
                TradingReportGenerated,
            )
            types = (
                AnalysisCompleted, BacktestCompleted, CandleClosed,
                FundamentalsAnalyzed, LiquidityAbsorbed, LiquidityConsumed,
                LiquidityImbalanceChanged, LiquidityReplenished,
                LiquidityRemoved, LiquiditySwept, LiquidityZoneCreated,
                LiquidityZoneInvalidated, LiquidityZoneWeakened,
                MarketDataReceived, MarketDataUpdated, MarketEventsDetected,
                MarketRegimeChanged, MarketRegimeDetected,
                NewsSentimentAnalyzed, PositionClosed, PredictionCreated,
                PredictionPerformanceEvaluated, PredictionResolved,
                ProbabilityEstimated, RiskAssessed, SignalCritiqued,
                SignalGenerated, TradingReportGenerated,
            )
            for event_type in types:
                await self._event_bus.subscribe(event_type, self._on_event)
            self._subscribed_types = types
            self._subscribed = True
        except Exception:
            logger.debug("Could not subscribe the workspace to the event bus.")

    async def stop(self) -> None:
        """Unsubscribe exactly what ``start`` registered (never others')."""
        if self._event_bus is None or not self._subscribed:
            return
        try:
            for event_type in self._subscribed_types:
                try:
                    await self._event_bus.unsubscribe(event_type, self._on_event)
                except Exception:
                    pass
        except Exception:
            pass
        self._subscribed = False

    # ------------------------------------------------------------------
    # Event -> state
    # ------------------------------------------------------------------

    async def _on_event(self, event: Event) -> None:
        """Record one event row (all events; the panel filters visually)."""
        try:
            d = event.to_dict()
        except Exception:
            d = {}
        name = event.name
        detail = self._detail(name, d)
        self._state.add_event(
            EventRow(
                name=name,
                instrument_key=d.get("instrument_key", ""),
                detail=detail,
                timestamp=(d.get("timestamp") or _ts()),
                is_mock=bool(d.get("is_mock", False)),
            )
        )

    @staticmethod
    def _detail(name: str, d: dict) -> str:
        """A one-line human-readable summary of an event's key fields."""
        parts = []
        for key in (
            "regime", "direction", "recommendation", "verdict", "p_up",
            "directional_accuracy", "sentiment_score", "price", "close",
            "zone_id", "liquidity_score",
        ):
            v = d.get(key)
            if v not in (None, "", []):
                parts.append(f"{key}={v}")
        return " ".join(parts[:4])

    # ------------------------------------------------------------------
    # Latest intelligence payloads -> state
    # ------------------------------------------------------------------

    def set_report(self, report_dict: dict | None) -> None:
        self._state.report = report_dict
        if report_dict:
            sig = report_dict.get("signal") or {}
            self._state.set_agent(
                AgentRow("Trading Intelligence", "running",
                         f"report {report_dict.get('recommendation', '')}")
            )

    def set_assessment(self, assessment_dict: dict | None) -> None:
        self._state.assessment = assessment_dict

    def set_intel(self, intel_dict: dict | None) -> None:
        self._state.intel = intel_dict
        self._state.set_agent(
            AgentRow("Market Analysis", "running" if intel_dict else "idle")
        )

    def set_heatmap(self, surface_dict: dict | None, *, projection: str = "") -> None:
        """Store the heatmap surface + its terminal projection."""
        if surface_dict is None:
            self._state.heatmap = None
            return
        self._state.heatmap = {
            **surface_dict,
            "projection": projection,
        }
        self._state.set_agent(
            AgentRow("Liquidity Analyzer", "running",
                     f"{len(surface_dict.get('values', []))} rows")
        )

    def set_candles(self, candles: list[dict]) -> None:
        self._state.candles = list(candles)

    def set_prediction_monitor(self, running: bool) -> None:
        self._state.set_agent(
            AgentRow(
                "Prediction Monitor",
                "running" if running else "idle",
            )
        )

    def set_component(self, name: str, status: str, detail: str = "",
                      is_mock: bool = False) -> None:
        self._state.set_agent(AgentRow(name, status, detail, is_mock))

    def set_system(self, name: str, status: str, detail: str = "") -> None:
        self._state.set_system(SystemMetric(name, status, detail))


class WorkspaceLogHandler(logging.Handler):
    """
    A ``logging.Handler`` that captures the *existing* application log stream
    into the workspace's LOGS ring buffer.

    Attached to the root (or a chosen) logger once; it does not replace or
    duplicate logging -- it taps the stream that already flows through the
    configured handlers.
    """

    def __init__(self, state: WorkspaceState) -> None:
        super().__init__()
        self._state = state

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._state.add_log(
                LogLine(
                    level=record.levelname,
                    logger=record.name,
                    message=record.getMessage(),
                    timestamp=(
                        datetime.fromtimestamp(
                            record.created, tz=timezone.utc
                        ).isoformat()
                    ),
                )
            )
        except Exception:
            pass
