"""
Kill-switch service (spec Phase 2 -- kill switches).

Holds the set of tripped :class:`KillSwitch` halts and answers the one question
the execution engine asks before any order reaches a venue: *is this request
blocked?* Four scopes compose -- a global halt blocks everything; a strategy,
broker or symbol halt blocks the slice it names. Any matching switch blocks.

Three rules are structural (spec Phase 2, CLAUDE.md sections 5, 28):

* **Blocking is admission-only and non-destructive.** ``is_blocked`` decides
  whether a *new* order may proceed; tripping a switch never clears the book,
  closes positions, or fabricates a cancel. Optionally, ``cancel_resting``
  will cancel orders a switch covers -- but only resting ones, and only when
  explicitly asked.
* **A trip is observable.** ``trip`` publishes ``KillSwitchTripped`` so the
  halt is never silent; ``clear`` publishes ``KillSwitchCleared``.
* **Recovery is explicit.** ``clear`` removes exactly the switch named and
  returns ``False`` (never fabricates a recovery) when no such switch exists;
  nothing clears on its own.

The service holds no broker and submits nothing -- it is a gate the engine
consults, plus an optional cancel helper it can call on the orders a switch
covers.
"""

from __future__ import annotations

import asyncio

from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..domain.enums import OrderStatus
from ..domain.execution import ExecutionRequest
from ..domain.kill_switch import KillScope, KillSwitch
from ..events import KillSwitchCleared, KillSwitchTripped

logger = get_logger("trading.kill_switch")


class KillSwitchService:
    """Scoped, observable order-admission halts."""

    def __init__(self, *, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        self._switches: dict[str, KillSwitch] = {}

    # ------------------------------------------------------------------
    # Trip / clear
    # ------------------------------------------------------------------

    def trip(self, switch: KillSwitch) -> KillSwitch:
        """
        Arm a halt. Returns the armed switch (idempotent -- re-tripping an
        already-tripped key replaces its record, never duplicates it).
        """
        key = switch.scope_key
        self._switches[key] = switch
        logger.warning("Kill switch tripped: %s -- %s", key, switch.reason)
        self._emit_tripped(switch)
        return switch

    def clear(self, scope: KillScope, target: str = "") -> bool:
        """
        Remove the switch at ``scope``/``target``. Returns True when one was
        actually cleared, False when none was armed -- a recovery is never
        fabricated for a switch that does not exist.
        """
        key = _scope_key(scope, target)
        switch = self._switches.pop(key, None)
        if switch is None:
            return False
        logger.info("Kill switch cleared: %s", key)
        self._emit_cleared(switch)
        return True

    def clear_all(self) -> int:
        """Clear every armed switch (an explicit operator reset). Returns the count."""
        keys = list(self._switches)
        for key in keys:
            switch = self._switches.pop(key)
            self._emit_cleared(switch)
        return len(keys)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def is_blocked(self, request: ExecutionRequest, broker_name: str) -> KillSwitch | None:
        """
        The switch that blocks this request, or None when admission is free.

        A request is blocked by a global halt, by a strategy halt matching its
        ``strategy_id``, by a broker halt matching the venue, or by a symbol
        halt matching its instrument key or bare symbol. The first matching
        switch is returned so the refusal names exactly what halted it.
        """
        if "global" in self._switches:
            return self._switches["global"]
        strategy_key = f"strategy:{request.strategy_id.strip().upper()}"
        if strategy_key in self._switches:
            return self._switches[strategy_key]
        broker_key = f"broker:{broker_name.strip().upper()}"
        if broker_key in self._switches:
            return self._switches[broker_key]
        for symbol_key in (
            f"symbol:{request.instrument.key.strip().upper()}",
            f"symbol:{request.instrument.symbol.strip().upper()}",
        ):
            if symbol_key in self._switches:
                return self._switches[symbol_key]
        return None

    def active(self) -> tuple[KillSwitch, ...]:
        """Every armed switch, in insertion order."""
        return tuple(self._switches.values())

    def covers(self, scope: KillScope, target: str = "") -> bool:
        """Whether a specific switch is armed."""
        return _scope_key(scope, target) in self._switches

    # ------------------------------------------------------------------
    # Optional order cancellation
    # ------------------------------------------------------------------

    async def cancel_resting(self, broker, switch: KillSwitch) -> int:
        """
        Cancel the resting orders a switch covers at ``broker``.

        Only orders still ``SUBMITTED`` (resting, unfilled) are cancelled --
        a filled or already-terminal order is left alone, and a venue that
        declines a cancel surfaces its own result. Returns how many resting
        orders were cancelled. Never touches positions or the book.
        """
        cancelled = 0
        orders = broker.venue_orders() if hasattr(broker, "venue_orders") else {}
        requests = broker.venue_requests() if hasattr(broker, "venue_requests") else {}
        for order_id, order in orders.items():
            if order.status is not OrderStatus.SUBMITTED:
                continue
            request = requests.get(order_id)
            if request is not None and not self._matches(switch, request, broker.name):
                continue
            try:
                result = await broker.cancel(order_id)
                if result.status is OrderStatus.CANCELLED:
                    cancelled += 1
            except Exception:
                logger.exception("Kill-switch cancel failed for %s", order_id)
        return cancelled

    @staticmethod
    def _matches(switch: KillSwitch, request: ExecutionRequest, broker_name: str) -> bool:
        """Whether one resting order falls under a given switch."""
        if switch.scope is KillScope.GLOBAL:
            return True
        if switch.scope is KillScope.STRATEGY:
            return request.strategy_id.strip().upper() == switch.target.strip().upper()
        if switch.scope is KillScope.BROKER:
            return broker_name.strip().upper() == switch.target.strip().upper()
        if switch.scope is KillScope.SYMBOL:
            target = switch.target.strip().upper()
            return target in (
                request.instrument.key.strip().upper(),
                request.instrument.symbol.strip().upper(),
            )
        return False

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _emit_tripped(self, switch: KillSwitch) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    KillSwitchTripped(
                        scope=switch.scope.value,
                        target=switch.target,
                        reason=switch.reason,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish KillSwitchTripped")

    def _emit_cleared(self, switch: KillSwitch) -> None:
        if self._event_bus is None:
            return
        try:
            asyncio.get_running_loop().create_task(
                self._event_bus.publish(
                    KillSwitchCleared(
                        scope=switch.scope.value,
                        target=switch.target,
                    )
                )
            )
        except RuntimeError:
            pass
        except Exception:
            logger.exception("Failed to publish KillSwitchCleared")


def _scope_key(scope: KillScope, target: str) -> str:
    if scope is KillScope.GLOBAL:
        return "global"
    return f"{scope.value}:{target.strip().upper()}"
