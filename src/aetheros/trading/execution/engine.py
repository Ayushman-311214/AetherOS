"""
Execution engine (spec Phase 9 -- validate orders, submit, modify, cancel,
retry failed requests; market/limit/stop/stop-limit support).

The engine sits between the judged proposal and the venue, and enforces the
§9 path's last two steps -- *execution validation* then *broker*:

    TradeSignal + RiskAssessment + Setup + quantity
        ──► ExecutionRequest (§9 record: everything present or nothing moves)
        ──► validate()      structural + risk-limit admission
        ──► submit()        broker, with bounded retry on transport faults
        ──► ExecutionResult (what the venue actually did)

**Retry is bounded and honest.** Only :class:`BrokerError` -- a transport or
venue fault, where the request's fate is *unknown* -- is retried, at most
``max_retries`` times with exponential backoff. A REJECTED result is a
decision the venue made about the order; retrying a rejection is trying to
wear the venue down, so it is returned immediately and verbatim. A FILLED
result, obviously, is never retried.

**Order types.** The request carries the order type and its trigger price(s):
a MARKET order fills on arrival, while LIMIT/STOP/STOP_LIMIT orders rest at
the venue until the trigger is met, and an untriggered order is reported as
SUBMITTED with no fill. The engine routes them all identically -- validation,
submission, retry -- because the venue is what knows when a trigger has been
met.

**No LLM ever reaches this module.** The only accepted input is a fully
populated :class:`ExecutionRequest` built from a fired
:class:`TradeSignal`; there is no string in, no judgement in, and no path
that could originate from a model's free text.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from ...config.settings import Settings
from ...core.logging import get_logger
from ...runtime.events.event_bus import EventBus
from ..brokers.base import BrokerProvider
from ..domain.enums import OrderStatus
from ..domain.execution import ExecutionRequest, ExecutionResult
from ..domain.kill_switch import KillSwitch
from ..domain.lifecycle import SignalState
from ..domain.policy import PolicyVerdict
from ..domain.risk_limits import AccountSnapshot, RiskLimitsVerdict
from ..errors import BrokerError, ExecutionError
from ..events import OrderFilled, OrderSubmitted
from ..policy.policy_service import ExecutionPolicyService
from ..production.kill_switch_service import KillSwitchService
from ..production.lifecycle_service import SignalLifecycleService
from ..risk.limits_service import RiskLimitsService

logger = get_logger("trading.execution")

#: Default ceiling on transport retries for one submission.
DEFAULT_MAX_RETRIES = 2

#: Base delay for retry backoff, seconds. Doubled per attempt.
DEFAULT_RETRY_BACKOFF_SECONDS = 0.1


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Why an request did or did not pass the engine's own validation."""

    ok: bool
    reason: str
    risk_limits: RiskLimitsVerdict | None = None
    policy: PolicyVerdict | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "risk_limits": self.risk_limits.to_dict() if self.risk_limits else None,
            "policy": self.policy.to_dict() if self.policy else None,
        }


class ExecutionEngine:
    """Validated, retry-bounded order submission to one broker."""

    def __init__(
        self,
        broker: BrokerProvider,
        risk_limits: RiskLimitsService,
        settings: Settings,
        *,
        policy: ExecutionPolicyService | None = None,
        kill_switches: KillSwitchService | None = None,
        lifecycle: SignalLifecycleService | None = None,
        event_bus: EventBus | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative.")
        if retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative.")
        self._broker = broker
        self._risk_limits = risk_limits
        self._settings = settings
        # The policy gate is the first admission check (spec Phase 26). When a
        # caller does not supply one, the engine builds the default gate from
        # its own settings, so there is never a path that skips policy by
        # simply forgetting to pass it.
        self._policy = policy or ExecutionPolicyService(settings)
        # The kill-switch gate runs immediately after policy (spec Phase 2): a
        # tripped switch blocks the order before the broker is ever consulted.
        # When none is injected the engine admits freely -- an absent gate
        # defaults to open, exactly as an absent risk snapshot does.
        self._kill_switches = kill_switches or KillSwitchService()
        # Lifecycle tracker: advancing the signal's state as orders move makes
        # the CREATED → ... → EXECUTED/CLOSED trail a first-class record.
        self._lifecycle = lifecycle or SignalLifecycleService(event_bus=event_bus)
        self._event_bus = event_bus
        self._max_retries = max_retries
        self._backoff = retry_backoff_seconds

    @property
    def broker(self) -> BrokerProvider:
        """The broker this engine submits to (paper venue by default)."""
        return self._broker

    @property
    def policy(self) -> ExecutionPolicyService:
        """The execution-policy gate this engine enforces."""
        return self._policy

    @property
    def kill_switches(self) -> KillSwitchService:
        """The kill-switch gate this engine honours before any order."""
        return self._kill_switches

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate(
        self,
        request: ExecutionRequest,
        *,
        account_snapshot: AccountSnapshot | None = None,
        confirmed: bool = False,
    ) -> ValidationReport:
        """
        The execution-validation step: policy, then structural, then risk.

        The *policy* gate (spec Phase 26) runs first and is the widest: it
        decides whether this kind of order, to this venue, in the configured
        trading mode, is permitted at all. A policy denial short-circuits --
        the account-level risk limits are not even consulted, because a trade
        the deployment forbids never gets as far as asking whether the account
        could afford it.

        Structural validation is already enforced by the
        :class:`ExecutionRequest` model itself, so the check here is
        belt-and-braces and reports it as such. The substantive risk check is
        the account-level risk limits gate: when a snapshot is supplied, the
        account must be inside its daily-loss and exposure boundaries before a
        new position is opened. No snapshot means the account gate is skipped
        and the reason says so -- the caller opted out, the engine did not
        forget.
        """
        policy_verdict = self._policy.evaluate(
            request, self._broker, confirmed=confirmed
        )
        if not policy_verdict.allowed:
            return ValidationReport(
                ok=False,
                reason=f"Blocked by execution policy: {policy_verdict.reason}",
                policy=policy_verdict,
            )
        switch = self._kill_switches.is_blocked(request, self._broker.name)
        if switch is not None:
            # Optionally cancel the resting orders the switch covers, so a halt
            # does not leave a live order working against it (spec Phase 2).
            if self._settings.TRADING_KILL_CANCEL_RESTING:
                try:
                    await self._kill_switches.cancel_resting(self._broker, switch)
                except Exception:
                    logger.exception(
                        "Kill-switch resting cancel failed for %s",
                        switch.scope_key,
                    )
            return ValidationReport(
                ok=False,
                reason=(
                    f"Blocked by kill switch ({switch.scope_key}): "
                    f"{switch.reason}"
                ),
                policy=policy_verdict,
            )
        if account_snapshot is None:
            return ValidationReport(
                ok=True,
                reason=(
                    "Policy permits it; structurally valid; no account snapshot "
                    "was supplied so the account-level limits were not checked."
                ),
                policy=policy_verdict,
            )
        verdict = self._risk_limits.check(account_snapshot)
        if verdict.allowed:
            return ValidationReport(
                ok=True,
                reason=(
                    "Policy permits it; structurally valid and the account is "
                    "inside its limits."
                ),
                risk_limits=verdict,
                policy=policy_verdict,
            )
        breached = "; ".join(o.reason for o in verdict.breached)
        return ValidationReport(
            ok=False,
            reason=f"Account-level risk limits breached: {breached}",
            risk_limits=verdict,
            policy=policy_verdict,
        )

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    async def submit(
        self,
        request: ExecutionRequest,
        *,
        account_snapshot: AccountSnapshot | None = None,
        validate: bool = True,
        confirmed: bool = False,
    ) -> ExecutionResult:
        """
        Validate, then submit to the broker with bounded retry.

        A failed validation returns a REJECTED result naming the breach; the
        broker is never reached. A :class:`BrokerError` after the retry
        budget is exhausted surfaces as an :class:`ExecutionError` (the
        request's fate may be unknown and the caller must know that), never
        as a fabricated result.

        ``validate=False`` is for callers that already ran the account-level
        risk gate upstream (e.g. the simulation replay). It opts out of *that*
        gate only -- the execution **policy** gate (spec Phase 26) is never
        optional and runs on every path, so no caller can reach a venue in a
        forbidden mode or to a disallowed broker by passing ``validate=False``.
        """
        if validate:
            report = await self.validate(
                request, account_snapshot=account_snapshot, confirmed=confirmed
            )
            if not report.ok:
                logger.warning(
                    "Execution rejected before submission: %s", report.reason
                )
                return ExecutionResult(
                    request_id=request.request_id,
                    status=OrderStatus.REJECTED,
                    reason=report.reason,
                )
        else:
            # The risk gate was opted out, but policy is never optional: a
            # forbidden order must not reach a venue merely because its risk
            # was judged elsewhere.
            policy_verdict = self._policy.evaluate(
                request, self._broker, confirmed=confirmed
            )
            if not policy_verdict.allowed:
                logger.warning(
                    "Execution blocked by policy (validate opted out): %s",
                    policy_verdict.reason,
                )
                return ExecutionResult(
                    request_id=request.request_id,
                    status=OrderStatus.REJECTED,
                    reason=f"Blocked by execution policy: {policy_verdict.reason}",
                )
            switch = self._kill_switches.is_blocked(request, self._broker.name)
            if switch is not None:
                logger.warning(
                    "Execution blocked by kill switch (validate opted out): %s",
                    switch.scope_key,
                )
                return ExecutionResult(
                    request_id=request.request_id,
                    status=OrderStatus.REJECTED,
                    reason=(
                        f"Blocked by kill switch ({switch.scope_key}): "
                        f"{switch.reason}"
                    ),
                )

        attempts = self._max_retries + 1
        last_error: BrokerError | None = None
        for attempt in range(1, attempts + 1):
            try:
                result = await self._broker.submit(request)
            except BrokerError as exc:
                last_error = exc
                logger.warning(
                    "Broker fault on attempt %d/%d for %s: %s",
                    attempt,
                    attempts,
                    request.request_id,
                    exc.message,
                )
                if attempt < attempts:
                    await asyncio.sleep(self._backoff * (2 ** (attempt - 1)))
                continue
            await self._emit_submitted(request, result)
            await self._emit_filled(request, result)
            self._advance_lifecycle(request, result)
            return result

        assert last_error is not None
        raise ExecutionError(
            f"The broker could not be reached after {attempts} attempts; "
            f"the request's fate is unknown: {last_error.message}",
            context={"request_id": request.request_id, "broker": self._broker.name},
            cause=last_error,
        )

    async def cancel(self, order_id: str) -> ExecutionResult:
        """Cancel an order at the broker; venue errors surface as ExecutionError."""
        try:
            return await self._broker.cancel(order_id)
        except BrokerError as exc:
            raise ExecutionError(
                f"Could not cancel order '{order_id}': {exc.message}",
                context={"order_id": order_id, "broker": self._broker.name},
                cause=exc,
            ) from exc

    async def modify(
        self,
        order_id: str,
        request: ExecutionRequest,
        *,
        account_snapshot: AccountSnapshot | None = None,
        validate: bool = True,
        confirmed: bool = False,
    ) -> ExecutionResult:
        """
        Replace a resting order's terms, under the same admission gate.

        An amendment is a new commitment of capital, so it passes the same
        validation a fresh submission would; the venue refuses to amend
        anything that is no longer live, and reports the terminal status
        instead of quietly re-opening it. As with :meth:`submit`,
        ``validate=False`` opts out of the account-level risk gate only -- the
        execution policy gate (spec Phase 26) is enforced on every path.
        """
        if validate:
            report = await self.validate(
                request, account_snapshot=account_snapshot, confirmed=confirmed
            )
            if not report.ok:
                logger.warning(
                    "Amendment rejected before submission: %s", report.reason
                )
                return ExecutionResult(
                    request_id=request.request_id,
                    status=OrderStatus.REJECTED,
                    reason=report.reason,
                    order_id=order_id,
                )
        else:
            policy_verdict = self._policy.evaluate(
                request, self._broker, confirmed=confirmed
            )
            if not policy_verdict.allowed:
                logger.warning(
                    "Amendment blocked by policy (validate opted out): %s",
                    policy_verdict.reason,
                )
                return ExecutionResult(
                    request_id=request.request_id,
                    status=OrderStatus.REJECTED,
                    reason=f"Blocked by execution policy: {policy_verdict.reason}",
                    order_id=order_id,
                )
            switch = self._kill_switches.is_blocked(request, self._broker.name)
            if switch is not None:
                logger.warning(
                    "Amendment blocked by kill switch (validate opted out): %s",
                    switch.scope_key,
                )
                return ExecutionResult(
                    request_id=request.request_id,
                    status=OrderStatus.REJECTED,
                    reason=(
                        f"Blocked by kill switch ({switch.scope_key}): "
                        f"{switch.reason}"
                    ),
                    order_id=order_id,
                )
        try:
            return await self._broker.modify(order_id, request)
        except BrokerError as exc:
            raise ExecutionError(
                f"Could not modify order '{order_id}': {exc.message}",
                context={"order_id": order_id, "broker": self._broker.name},
                cause=exc,
            ) from exc

    async def status(self, order_id: str) -> ExecutionResult:
        """The broker's current state for an order."""
        try:
            return await self._broker.status(order_id)
        except BrokerError as exc:
            raise ExecutionError(
                f"Could not read order '{order_id}': {exc.message}",
                context={"order_id": order_id, "broker": self._broker.name},
                cause=exc,
            ) from exc

    # ------------------------------------------------------------------

    async def _emit_submitted(
        self, request: ExecutionRequest, result: ExecutionResult
    ) -> None:
        if self._event_bus is None:
            return
        try:
            await self._event_bus.publish(
                OrderSubmitted(
                    order_id=result.order_id or "",
                    instrument_key=request.instrument.key,
                    direction=request.direction.value,
                    order_type=request.order_type.value,
                    quantity=request.quantity,
                    provider=self._broker.name,
                )
            )
        except Exception:
            logger.exception("Failed to publish OrderSubmitted")

    async def _emit_filled(
        self, request: ExecutionRequest, result: ExecutionResult
    ) -> None:
        """Announce a fill so the book/journal/lifecycle layers can observe it."""
        if self._event_bus is None:
            return
        if result.status not in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            return
        try:
            await self._event_bus.publish(
                OrderFilled(
                    order_id=result.order_id or "",
                    instrument_key=request.instrument.key,
                    filled_quantity=result.filled_quantity,
                    fill_price=result.average_fill_price or request.entry,
                    fully_filled=result.status is OrderStatus.FILLED,
                )
            )
        except Exception:
            logger.exception("Failed to publish OrderFilled")

    def _advance_lifecycle(
        self, request: ExecutionRequest, result: ExecutionResult
    ) -> None:
        """
        Advance the signal's lifecycle from the venue's verdict.

        A FILLED result moves the signal to EXECUTED; PARTIALLY_FILLED to
        PARTIALLY_FILLED; a resting SUBMITTED order to ACTIVE (the order is
        working at the venue). A REJECTED result invalidates the signal. Best
        effort: a lifecycle edge case logs, never fails the submission.
        """
        signal_id = request.signal_id
        instrument_key = request.instrument.key
        if result.status is OrderStatus.FILLED:
            self._lifecycle.try_advance(
                signal_id,
                SignalState.EXECUTED,
                reason="order filled at the venue",
                instrument_key=instrument_key,
            )
        elif result.status is OrderStatus.PARTIALLY_FILLED:
            self._lifecycle.try_advance(
                signal_id,
                SignalState.PARTIALLY_FILLED,
                reason="order partially filled at the venue",
                instrument_key=instrument_key,
            )
        elif result.status is OrderStatus.SUBMITTED:
            self._lifecycle.try_advance(
                signal_id,
                SignalState.ACTIVE,
                reason="order resting at the venue",
                instrument_key=instrument_key,
            )
        elif result.status is OrderStatus.REJECTED:
            self._lifecycle.try_advance(
                signal_id,
                SignalState.INVALIDATED,
                reason=f"order rejected: {result.reason}",
                instrument_key=instrument_key,
            )
