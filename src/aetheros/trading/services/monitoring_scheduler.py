"""
Monitoring scheduler -- the bounded autonomous loop around the sweep.

The spec allows autonomous operation but demands it stay bounded and opt-in
(CLAUDE.md section 29). This scheduler is exactly that and nothing more: when
*explicitly enabled*, it runs one :class:`MonitoringService` sweep, waits a
configured interval, and repeats -- a thin, cancellable loop around the already-
bounded sweep. It is OFF by default and never starts on its own.

Safety properties:

* **Opt-in.** It only runs when ``TRADING_MONITOR_ENABLED`` is set; the default
  build never starts a background task.
* **Cancellable.** ``start`` launches a single asyncio task; ``stop`` cancels it
  and awaits its exit, so shutdown is clean and there is no runaway thread.
* **Fault-isolated.** A failing sweep is logged and the loop continues to the
  next interval rather than dying -- one bad pass never kills the monitor.
* **Composition only.** It introduces no new analysis; it just repeats the
  deterministic sweep, which keeps all its own honesty guarantees.
"""

from __future__ import annotations

import asyncio

from ...config.settings import Settings
from ...core.logging import get_logger
from .monitoring_service import MonitoringService

logger = get_logger("trading.monitoring_scheduler")


class MonitoringScheduler:
    """A cancellable, opt-in loop that repeats the bounded monitoring sweep."""

    def __init__(
        self,
        monitoring: MonitoringService,
        settings: Settings,
    ) -> None:
        self._monitoring = monitoring
        self._settings = settings
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def enabled(self) -> bool:
        return self._settings.TRADING_MONITOR_ENABLED

    @property
    def interval_seconds(self) -> float:
        return self._settings.TRADING_MONITOR_INTERVAL_SECONDS

    async def start(self) -> bool:
        """Start the loop if enabled and not already running. Returns started?."""
        if not self._settings.TRADING_MONITOR_ENABLED:
            logger.info("Monitoring loop disabled (TRADING_MONITOR_ENABLED off).")
            return False
        if self.is_running:
            return False
        self._stop.clear()
        self._task = asyncio.create_task(self._run())
        logger.info(
            "Monitoring loop started (interval %.0fs).",
            self._settings.TRADING_MONITOR_INTERVAL_SECONDS,
        )
        return True

    async def stop(self) -> None:
        """Cancel the loop and await its clean exit (idempotent)."""
        self._stop.set()
        task, self._task = self._task, None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    async def run_once_now(self):
        """Run a single sweep immediately (bypasses the schedule)."""
        return await self._monitoring.run_once()

    # ------------------------------------------------------------------

    async def _run(self) -> None:
        interval = self._settings.TRADING_MONITOR_INTERVAL_SECONDS
        while not self._stop.is_set():
            try:
                await self._monitoring.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Monitoring sweep failed; continuing the loop")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue
