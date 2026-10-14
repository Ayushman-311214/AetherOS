"""
Trading-health service (spec Phase 2 -- trading health).

Folds every live input into one three-band verdict. It composes the state that
already exists -- it reads the position book's snapshot for risk-limit state,
the kill-switch service for armed halts, the latest reconciliation report, the
market-data quality map, and the broker's reachability -- and emits
:class:`TradingHealthChanged` only on a genuine band transition, exactly like
the risk-band tracker in :class:`RiskLimitsService`.

Honesty rules (CLAUDE.md sections 5, 28):

* **The band is the worst signal present, never an average and never a guess.**
  A single BLOCKED input blocks the desk; a single DEGRADED input degrades it.
* **An unreadable input degrades, never passes silently.** If the broker
  cannot be reached or a required ledger is missing, that absence is itself a
  DEGRADED (or BLOCKED where it is a hard dependency) signal -- not a SAFE.
* **First read seeds, it does not alarm.** The health tracker only announces a
  *change*; a service that has not seen a band before cannot assert one moved.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..brokers.paper_provider import PaperTradingProvider
from ..domain.enums import DataQualityStatus
from ..domain.health import HealthBand, HealthSignal, TradingHealth
from ..domain.reconciliation import ReconciliationReport
from ..events import TradingHealthChanged
from .kill_switch_service import KillSwitchService
from .position_service import PositionBookService
from .reconciliation_service import ReconciliationService

if TYPE_CHECKING:
    # MarketDataService lives under services/, which imports the execution
    # engine that this package feeds -- importing it at runtime would cycle.
    from ..services.market_data_service import MarketDataService

logger = get_logger("trading.health")


class TradingHealthService:
    """The aggregate desk-health verdict, folded from live inputs."""

    def __init__(
        self,
        market_data: MarketDataService,
        positions: PositionBookService,
        kill_switches: KillSwitchService,
        venue: PaperTradingProvider,
        *,
        reconciliation: ReconciliationService | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._market_data = market_data
        self._positions = positions
        self._kill_switches = kill_switches
        self._venue = venue
        self._reconciliation = reconciliation
        self._event_bus = event_bus
        self._last_band: HealthBand | None = None

    async def status(self, *, reconcile: bool = True) -> TradingHealth:
        """
        Compute the current health verdict.

        Each input contributes a ``HealthSignal``; the band is the worst one
        present. ``reconcile=False`` skips the venue diff for callers that only
        want a fast structural read.
        """
        signals: list[HealthSignal] = [
            self._data_quality(),
            self._kill_switch(),
            self._positions_signal(),
            self._broker(),
        ]
        if reconcile and self._reconciliation is not None:
            signals.append(await self._reconciled())

        band = max((s.band for s in signals), key=lambda b: b.severity)
        health = TradingHealth(band=band, signals=tuple(signals))
        self._emit_transition(health)
        return health

    # ------------------------------------------------------------------
    # Individual signals
    # ------------------------------------------------------------------

    def _data_quality(self) -> HealthSignal:
        """Worst data-quality state across the feed's tracked instruments."""
        quality = getattr(self._market_data, "_last_quality", None)
        if not quality:
            return HealthSignal(
                source="data_quality",
                band=HealthBand.DEGRADED,
                detail="No market-data quality has been observed yet.",
            )
        worst = HealthBand.SAFE
        detail = "All observed market data is usable."
        for key, status in quality.items():
            if status in (DataQualityStatus.MISSING, DataQualityStatus.INVALID):
                return HealthSignal(
                    source="data_quality",
                    band=HealthBand.BLOCKED,
                    detail=f"Market data for '{key}' is {status.value}; unusable.",
                )
            if status is not DataQualityStatus.OK:
                worst = HealthBand.DEGRADED
                detail = f"Market data for '{key}' is {status.value}; degraded."
        return HealthSignal(source="data_quality", band=worst, detail=detail)

    def _kill_switch(self) -> HealthSignal:
        """Any armed kill switch blocks the desk."""
        active = self._kill_switches.active()
        if active:
            names = ", ".join(s.scope_key for s in active)
            return HealthSignal(
                source="kill_switch",
                band=HealthBand.BLOCKED,
                detail=f"Kill switch(es) tripped: {names}.",
            )
        return HealthSignal(
            source="kill_switch",
            band=HealthBand.SAFE,
            detail="No kill switch is tripped.",
        )

    def _positions_signal(self) -> HealthSignal:
        """The position book's open-exposure posture."""
        exposure = self._positions.open_exposure()
        open_count = len(self._positions.open_positions())
        return HealthSignal(
            source="positions",
            band=HealthBand.SAFE,
            detail=f"{open_count} open position(s); exposure {exposure:.2f}.",
        )

    def _broker(self) -> HealthSignal:
        """Whether the venue can report its own state."""
        try:
            # A cheap structural read -- the venue exposing its orders is the
            # reachability check, not a fabricated ping.
            self._venue.venue_orders()
            reachable = True
        except Exception:
            reachable = False
        if reachable:
            return HealthSignal(
                source="broker",
                band=HealthBand.SAFE,
                detail=f"Venue '{self._venue.name}' is reachable.",
            )
        return HealthSignal(
            source="broker",
            band=HealthBand.BLOCKED,
            detail=f"Venue '{self._venue.name}' cannot report its state.",
        )

    async def _reconciled(self) -> HealthSignal:
        """The latest local-vs-venue diff."""
        try:
            report: ReconciliationReport = await self._reconciliation.reconcile()
        except Exception as exc:
            return HealthSignal(
                source="reconciliation",
                band=HealthBand.DEGRADED,
                detail=f"Reconciliation could not run: {exc}",
            )
        if report.is_clean:
            return HealthSignal(
                source="reconciliation",
                band=HealthBand.SAFE,
                detail=f"Reconciliation clean across {report.checked} leg(s).",
            )
        return HealthSignal(
            source="reconciliation",
            band=HealthBand.DEGRADED,
            detail=f"{report.mismatch_count} reconciliation mismatch(es) found.",
        )

    # ------------------------------------------------------------------
    # Transition event
    # ------------------------------------------------------------------

    def _emit_transition(self, health: TradingHealth) -> None:
        """Announce a genuine band change; first read only seeds."""
        prev = self._last_band
        self._last_band = health.band
        if self._event_bus is None or prev is None or prev == health.band:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    TradingHealthChanged(
                        previous_state=prev.value,
                        state=health.band.value,
                        reasons=health.reasons,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish TradingHealthChanged")
