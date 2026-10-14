"""
The verifier — one entry point for every read-back in the desktop subsystem.

Tools do not instantiate strategies. They hand the verifier a
:class:`~aetheros.desktop.verification.strategy.VerificationRequest` and receive a
:class:`~aetheros.desktop.verification.result.VerificationResult`. Routing through
a single object buys three things that matter:

* ``DESKTOP_VERIFY_ACTIONS`` is honoured in exactly one place, so switching
  verification off cannot accidentally leave a tool claiming an unchecked
  success — every result becomes ``SKIPPED``, which reports ``verified: false``.
* :meth:`Verifier.wait_until` gives all the ``wait_for_*`` tools one bounded
  polling loop instead of eight hand-rolled ones, each with its own chance of
  looping forever.
* An unknown method name fails loudly and once, rather than being silently
  treated as "nothing to check".
"""

from __future__ import annotations

import asyncio
import time

from ...config.config_loader import get_settings
from ...core.errors.desktop_error import DesktopError
from ...core.logging import get_logger
from .result import VerificationResult, VerificationStatus
from .strategy import STRATEGIES, MatchMode, VerificationRequest, VerificationStrategy


class Verifier:
    """
    Dispatches verification requests to the strategy that implements them.

    Strategies are instantiated once and reused. They hold no per-check state —
    every service lookup happens inside ``check`` — so sharing them is safe and
    avoids rebuilding eight objects on every mouse move.
    """

    def __init__(self) -> None:
        self._logger = get_logger("desktop.verifier")
        self._strategies: dict[str, VerificationStrategy] = {
            name: cls() for name, cls in STRATEGIES.items()
        }

    # ==========================================================
    # Introspection
    # ==========================================================

    @property
    def methods(self) -> tuple[str, ...]:
        return tuple(sorted(self._strategies))

    def describe_methods(self) -> dict[str, str]:
        """
        Method name to one-line description.

        Used by the health check and by the ``verify_action`` tool's schema, so
        the list the model sees cannot drift from the strategies that exist.
        """

        return {
            name: strategy.description
            for name, strategy in sorted(self._strategies.items())
        }

    # ==========================================================
    # Single check
    # ==========================================================

    async def verify(
        self,
        request: VerificationRequest,
        *,
        force: bool = False,
    ) -> VerificationResult:
        """
        Run one verification.

        :param force: Ignore ``DESKTOP_VERIFY_ACTIONS``. Used by the explicit
            ``verify_action`` tool and the health check, where the caller asked
            for a check directly rather than getting one as a side effect of an
            action — switching off automatic verification should not disable the
            tool whose entire purpose is to verify.
        """

        if not force and not get_settings().DESKTOP_VERIFY_ACTIONS:
            return VerificationResult.skipped(
                request.describe(),
                detail="DESKTOP_VERIFY_ACTIONS is disabled.",
            )

        strategy = self._strategy(request.method)

        return await strategy.check(request)

    # ==========================================================
    # Polling
    # ==========================================================

    async def wait_until(
        self,
        request: VerificationRequest,
        *,
        timeout_seconds: float | None = None,
        interval_seconds: float | None = None,
    ) -> VerificationResult:
        """
        Poll a condition until it holds, or until the deadline passes.

        The single implementation behind every ``wait_for_*`` tool. Bounded three
        ways, on purpose:

        * the caller's ``timeout_seconds``,
        * ``DESKTOP_MAX_WAIT_SECONDS``, which caps whatever the caller asked for
          so a model passing ``timeout=86400`` cannot wedge a tool for a day,
        * and the executor's own budget above that.

        Returns the *last* result rather than a synthetic timeout so the caller
        sees what was actually observed on the final poll — "actual: no matching
        window" is diagnosable; "timed out" is not.
        """

        settings = get_settings()
        ceiling = settings.DESKTOP_MAX_WAIT_SECONDS

        budget = ceiling if timeout_seconds is None else min(timeout_seconds, ceiling)
        budget = max(budget, 0.0)

        interval = (
            settings.DESKTOP_POLL_INTERVAL_SECONDS
            if interval_seconds is None
            else max(interval_seconds, 0.01)
        )

        strategy = self._strategy(request.method)

        deadline = time.monotonic() + budget
        attempts = 0

        # do/while: always check at least once, so a zero timeout is an immediate
        # check rather than an instant failure.
        while True:

            attempts += 1
            result = await strategy.check(request)

            if result.verified:
                return self._with_detail(
                    result,
                    f"satisfied after {attempts} check(s)",
                )

            if result.status is VerificationStatus.ERROR:
                # A broken check will stay broken; polling it 250 times only
                # delays an honest answer.
                return self._with_detail(
                    result,
                    f"{result.detail or 'verification error'} "
                    f"(gave up after {attempts} check(s))",
                )

            remaining = deadline - time.monotonic()

            if remaining <= 0:
                return self._with_detail(
                    result,
                    f"not satisfied within {budget:g}s "
                    f"({attempts} check(s))",
                )

            await asyncio.sleep(min(interval, remaining))

    # ==========================================================
    # Convenience builders
    # ==========================================================

    async def verify_state(
        self,
        condition: str,
        *,
        observed: str | None,
        expected: str,
        mode: MatchMode = MatchMode.EQUALS,
    ) -> VerificationResult:
        """
        Shorthand for the common case: a service already read its own state back.
        """

        return await self.verify(
            VerificationRequest(
                method="state",
                mode=mode,
                expected=expected,
                target=observed,
                condition=condition,
            )
        )

    # ==========================================================
    # Internals
    # ==========================================================

    def _strategy(self, method: str) -> VerificationStrategy:

        strategy = self._strategies.get(method)

        if strategy is None:
            known = ", ".join(self.methods)

            raise DesktopError(
                code="VERIFICATION_METHOD_UNKNOWN",
                message=f"No verification method named '{method}'.",
                hint=f"Available methods: {known}.",
            )

        return strategy

    def _with_detail(
        self,
        result: VerificationResult,
        detail: str,
    ) -> VerificationResult:
        """
        Append polling context to a result without losing what it observed.
        """

        return VerificationResult(
            status=result.status,
            condition=result.condition,
            method=result.method,
            expected=result.expected,
            actual=result.actual,
            detail=detail,
        )


verifier = Verifier()
"""
Process-wide verifier.

A module-level singleton rather than a container registration because it has no
dependencies of its own — the strategies resolve their services lazily — and
because tools import it at module scope, before the container is populated.
"""
