"""
The policy engine: evaluates a requested tool call, and never runs it.

This is the gate that sits before ``ToolExecutor``. Given a tool name, its
arguments, the current iteration and whether the caller confirmed, it returns a
:class:`PolicyEvaluation` carrying ALLOW, DENY or REQUIRE_CONFIRMATION. It holds
no executor and calls nothing -- the single side effect it owns is its own
emergency-stop flag.

Fail closed. The whole point of a safety gate is that its own failure must not
open it: an argument validator that raises is treated as a denial, not waved
through, and the emergency stop denies everything until it is explicitly
cleared.

Order of checks (first match wins)
----------------------------------
1. Emergency stop -- denies everything, regardless of the other rules.
2. Iteration ceiling -- a run past its policy budget is denied before argument
   work, since no tool at this iteration can be allowed.
3. Denylist -- an explicit deny is never overridden by an allow.
4. Allowlist -- when non-empty, a tool absent from it is denied.
5. Argument validators -- an invalid argument is a denial; a validator that
   raises is a *policy failure*, also a denial, with a distinct code.
6. Confirmation -- a confirmation-required tool with no confirmation yields
   REQUIRE_CONFIRMATION.
7. Otherwise ALLOW.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...config.config_loader import get_settings
from ...core.logging import get_logger
from .config import PolicyConfig
from .decision import (
    POLICY_ALLOWED,
    POLICY_CONFIRMATION_REQUIRED,
    POLICY_DENIED_TOOL,
    POLICY_EMERGENCY_STOP,
    POLICY_FAILURE,
    POLICY_INVALID_ARGUMENTS,
    POLICY_ITERATION_LIMIT,
    POLICY_NOT_ALLOWED,
    PolicyDecision,
    PolicyEvaluation,
)


class PolicyEngine:
    """Decides whether one requested tool call may run. Runs nothing.

    Stateful in exactly one respect: the emergency stop. Everything else is a
    pure function of the :class:`PolicyConfig` and the call being asked about,
    so two engines with the same config and the same stop state answer
    identically. The config is read on every call rather than cached into
    decisions, so a deployment that hands over a new config gets a new engine
    -- the config is frozen and never edited in place.
    """

    __slots__ = ("_config", "_logger", "_emergency_stopped")

    def __init__(self, config: PolicyConfig | None = None) -> None:
        # An engine with no config restricts nothing by name and sets no
        # iteration cap of its own -- it still fails closed on validator errors
        # and still honours the emergency stop.
        self._config = config or PolicyConfig()
        # get_logger installs the file sinks on first use.
        self._logger = get_logger("agents.policy")
        self._emergency_stopped = False

    @property
    def config(self) -> PolicyConfig:
        return self._config

    @property
    def is_emergency_stopped(self) -> bool:
        return self._emergency_stopped

    # -- emergency stop ---------------------------------------------------

    def trigger_emergency_stop(self, reason: str = "") -> None:
        """Latch the stop. Every subsequent :meth:`evaluate` denies until it is
        cleared -- a kill switch, not a rate limit."""

        self._emergency_stopped = True
        self._logger.bind(reason=reason or "unspecified").warning(
            "Policy emergency stop engaged; all tool calls will be denied."
        )

    def clear_emergency_stop(self) -> None:
        """Release the stop. Deliberately explicit: nothing clears it on the
        engine's behalf, so a stop survives until a human (or an operator path)
        decides the cause is resolved."""

        if self._emergency_stopped:
            self._logger.info("Policy emergency stop cleared.")
        self._emergency_stopped = False

    # -- evaluation -------------------------------------------------------

    def evaluate(
        self,
        tool: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        iteration: int = 0,
        confirmed: bool = False,
    ) -> PolicyEvaluation:
        """Answer ALLOW / DENY / REQUIRE_CONFIRMATION for one call.

        First match wins, in the order documented at the top of this module.
        The tool is never run, and ``arguments`` is only read -- a validator
        that tries to mutate it is a bug in that validator, not something this
        method relies on.
        """

        args: Mapping[str, Any] = arguments or {}

        # 1. Emergency stop -- overrides every rule, including an allowlist.
        if self._emergency_stopped:
            return self._deny(
                tool,
                iteration,
                POLICY_EMERGENCY_STOP,
                "Emergency stop is engaged; no tool may run.",
            )

        # 2. Iteration ceiling -- a spent budget denies before argument work,
        #    matching AgentState's own `iteration >= max_iterations` rule.
        cap = self._config.max_iterations
        if cap is not None and iteration >= cap:
            return self._deny(
                tool,
                iteration,
                POLICY_ITERATION_LIMIT,
                (
                    f"Iteration {iteration} has reached the policy budget of "
                    f"{cap}."
                ),
            )

        # 3. Denylist -- an explicit deny is never overridden by an allow.
        if tool in self._config.denied_tools:
            return self._deny(
                tool,
                iteration,
                POLICY_DENIED_TOOL,
                f"Tool '{tool}' is on the policy denylist.",
            )

        # 4. Allowlist -- only consulted when non-empty; empty means no
        #    allowlist, not "deny everything".
        if self._config.allowed_tools and tool not in self._config.allowed_tools:
            return self._deny(
                tool,
                iteration,
                POLICY_NOT_ALLOWED,
                f"Tool '{tool}' is not on the policy allowlist.",
            )

        # 5. Argument validators -- invalid args deny; a raising validator is a
        #    policy failure, also a denial, with its own code (fail-closed).
        invalid = self._validate_arguments(tool, args)
        if invalid is not None:
            code, reason = invalid
            return self._deny(tool, iteration, code, reason)

        # 6. Confirmation -- a confirmation-required tool with no confirmation
        #    is held, not run.
        if tool in self._config.confirmation_tools and not confirmed:
            return self._require_confirmation(tool, iteration)

        # 7. Nothing objected.
        return self._allow(tool, iteration)

    # -- argument validation ----------------------------------------------

    def _validate_arguments(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> tuple[str, str] | None:
        """Run global validators then the per-tool one; first objection wins.

        Returns ``None`` when every validator is satisfied, or a
        ``(code, reason)`` pair when one objects. A validator that *raises* does
        not propagate: the gate treats its own failure as a denial
        (``POLICY_FAILURE``) rather than letting the call slip through while the
        check is broken.
        """

        validators = list(self._config.global_argument_validators)
        per_tool = self._config.argument_validators.get(tool)
        if per_tool is not None:
            validators.append(per_tool)

        for validator in validators:
            try:
                verdict = validator(tool, arguments)

            except Exception as exc:  # noqa: BLE001 -- fail closed on any error.
                # The validator's own values may echo argument content, so log
                # the exception type only, never its message or the arguments.
                self._logger.bind(
                    tool=tool,
                    validator=getattr(validator, "__name__", repr(validator)),
                    error_type=type(exc).__name__,
                ).error("An argument validator raised; denying the call.")

                return (
                    POLICY_FAILURE,
                    (
                        "An argument validator failed while checking tool "
                        f"'{tool}'; the call is denied."
                    ),
                )

            # Truthy non-True == a reason string naming what is wrong.
            if verdict and verdict is not True:
                return (
                    POLICY_INVALID_ARGUMENTS,
                    f"Arguments for tool '{tool}' were rejected: {verdict}",
                )

        return None

    # -- decision constructors --------------------------------------------

    def _timeout(self) -> float:
        """Advisory per-call budget the evaluation reports. The engine holds no
        clock -- it names the ceiling the executor should apply, falling back to
        the configured default when the policy sets none."""

        if self._config.timeout_seconds is not None:
            return self._config.timeout_seconds
        return float(get_settings().TOOL_TIMEOUT_SECONDS)

    def _allow(self, tool: str, iteration: int) -> PolicyEvaluation:
        return PolicyEvaluation(
            tool=tool,
            decision=PolicyDecision.ALLOW,
            reason=f"Tool '{tool}' is permitted by policy.",
            code=POLICY_ALLOWED,
            iteration=iteration,
            timeout_seconds=self._timeout(),
        )

    def _deny(
        self,
        tool: str,
        iteration: int,
        code: str,
        reason: str,
    ) -> PolicyEvaluation:
        self._logger.bind(
            tool=tool,
            iteration=iteration,
            code=code,
        ).info("Policy denied a tool call.")

        return PolicyEvaluation(
            tool=tool,
            decision=PolicyDecision.DENY,
            reason=reason,
            code=code,
            iteration=iteration,
            timeout_seconds=self._timeout(),
        )

    def _require_confirmation(
        self,
        tool: str,
        iteration: int,
    ) -> PolicyEvaluation:
        self._logger.bind(
            tool=tool,
            iteration=iteration,
        ).info("Policy requires confirmation for a tool call.")

        return PolicyEvaluation(
            tool=tool,
            decision=PolicyDecision.REQUIRE_CONFIRMATION,
            reason=f"Tool '{tool}' requires explicit confirmation before it runs.",
            code=POLICY_CONFIRMATION_REQUIRED,
            iteration=iteration,
            timeout_seconds=self._timeout(),
        )


__all__ = ["PolicyEngine"]
