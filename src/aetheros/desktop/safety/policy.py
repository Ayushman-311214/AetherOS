"""
The risk policy that gates every desktop action.

The rule this module exists to enforce: the language model must not be able to
power off the machine, wipe a directory, or run an arbitrary shell command
because it misread a prompt. Those actions stay available — an automation system
that cannot close a window is not useful — but each one has to pass a gate that
the model alone cannot open.

Two independent gates, deliberately:

Operator consent
    A configuration flag (``DESKTOP_ALLOW_POWER_ACTIONS``, ``ALLOW_SHELL``,
    ``ALLOW_DELETE``). Set once per install, out of the model's reach.

Caller intent
    An explicit ``confirm=True`` argument on the tool itself. In the schema, so
    the model has to actively choose it, and visible in the audit log as a
    distinct fact from "the tool was called".

The most dangerous class (:attr:`RiskLevel.CRITICAL` — shutdown, restart, log
off) requires *both*. Neither one alone is enough: a config flag alone means any
stray call fires, and a confirm flag alone means the model gates itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...config.config_loader import get_settings
from ...core.errors.desktop_error import DesktopError
from ...core.logging import get_logger


class RiskLevel(str, Enum):
    """
    How much damage the action can do if it fires when it should not.

    Graded by *consequence of a mistake*, not by how privileged the call is.
    ``read_file`` needs no privilege and is SAFE; ``delete_folder`` needs no
    privilege either and is HIGH_RISK, because the mistake is unrecoverable.
    """

    SAFE = "safe"
    """Read-only. Screen size, mouse position, process list, file listing."""

    LOW_RISK = "low_risk"
    """Observable side effects, trivially undone. Mouse moves, scrolls, focus."""

    MEDIUM_RISK = "medium_risk"
    """
    Changes state a user would notice and might not be able to undo. Typing into
    an unknown window, overwriting a file, closing a window with unsaved work.
    """

    HIGH_RISK = "high_risk"
    """
    Destroys data or kills work in progress. Deleting files, terminating a
    process, running an arbitrary command. Always requires ``confirm``.
    """

    CRITICAL = "critical"
    """
    Ends the session or the machine. Shutdown, restart, sleep, log off.
    Requires operator consent *and* ``confirm``, and is refused by default.
    """


class Decision(str, Enum):
    """What the policy decided to do about a request."""

    EXECUTE = "execute"
    CONFIRM = "confirm"
    """Permitted in principle, but the caller did not pass ``confirm=True``."""

    REJECT = "reject"
    """Not permitted at all in this configuration. Confirming will not help."""


class Capability(str, Enum):
    """
    A configuration-gated class of operation.

    Separate from :class:`RiskLevel` because the two answer different questions.
    Risk asks "how bad is a mistake?"; capability asks "has this deployment
    opted in to this kind of operation at all?" A locked-down install can
    disable ``SHELL`` while still allowing the HIGH_RISK file deletes it needs.
    """

    POWER = "power"
    SHELL = "shell"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """
    The policy's answer, as data.

    Returned rather than raised so ``dry_run`` and the health check can ask what
    *would* happen, and so the reason reaches the model verbatim instead of
    being flattened into a generic refusal it cannot act on.
    """

    action: str
    risk: RiskLevel
    decision: Decision
    reason: str
    capability: Capability | None = None

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.EXECUTE

    def to_dict(self) -> dict[str, object]:

        return {
            "action": self.action,
            "risk": self.risk.value,
            "decision": self.decision.value,
            "reason": self.reason,
            "capability": self.capability.value if self.capability else None,
        }


class SafetyPolicy:
    """
    Evaluates desktop actions against configuration and caller intent.

    Stateless. Reads configuration per call so an operator change takes effect
    without a restart, and so tests can vary policy without rebuilding the
    object graph.
    """

    def __init__(self) -> None:
        self._logger = get_logger("desktop.safety")

    # ==========================================================
    # Evaluation
    # ==========================================================

    def evaluate(
        self,
        action: str,
        risk: RiskLevel,
        *,
        confirmed: bool = False,
        capability: Capability | None = None,
    ) -> PolicyDecision:
        """
        Decide whether ``action`` may run.

        Parameters
        ----------
        action:
            Tool name, for the audit log and the refusal message.
        risk:
            How bad a mistake would be.
        confirmed:
            Whether the caller passed an explicit confirmation flag. Never
            defaulted to True anywhere in the codebase.
        capability:
            The configuration gate this action needs, if any.
        """

        settings = get_settings()

        # ------------------------------------------------------
        # Capability gate, before risk
        # ------------------------------------------------------

        # Checked first because a disabled capability is a REJECT, and reporting
        # "needs confirmation" for something that is switched off entirely would
        # send the caller round a loop it cannot win.
        if capability is not None and not self._capability_enabled(capability):

            return self._reject(
                action,
                risk,
                capability,
                reason=(
                    f"the '{capability.value}' capability is disabled "
                    f"({self._capability_setting(capability)}=false)"
                ),
            )

        # ------------------------------------------------------
        # Risk gate
        # ------------------------------------------------------

        if risk in (RiskLevel.SAFE, RiskLevel.LOW_RISK):
            return self._execute(
                action,
                risk,
                capability,
                reason="action is read-only or trivially reversible",
            )

        if risk is RiskLevel.MEDIUM_RISK:

            if not settings.DESKTOP_REQUIRE_CONFIRM_MEDIUM_RISK:
                return self._execute(
                    action,
                    risk,
                    capability,
                    reason="medium-risk actions do not require confirmation in this configuration",
                )

            return self._require_confirmation(
                action,
                risk,
                capability,
                confirmed=confirmed,
                reason="DESKTOP_REQUIRE_CONFIRM_MEDIUM_RISK is enabled",
            )

        if risk is RiskLevel.HIGH_RISK:
            return self._require_confirmation(
                action,
                risk,
                capability,
                confirmed=confirmed,
                reason="the action destroys data or terminates work in progress",
            )

        # ------------------------------------------------------
        # CRITICAL — both gates
        # ------------------------------------------------------

        if not settings.DESKTOP_ALLOW_POWER_ACTIONS:
            return self._reject(
                action,
                risk,
                capability,
                reason=(
                    "power-state changes are disabled "
                    "(DESKTOP_ALLOW_POWER_ACTIONS=false)"
                ),
            )

        return self._require_confirmation(
            action,
            risk,
            capability,
            confirmed=confirmed,
            reason="the action ends the session or powers off the machine",
        )

    def require(
        self,
        action: str,
        risk: RiskLevel,
        *,
        confirmed: bool = False,
        capability: Capability | None = None,
    ) -> PolicyDecision:
        """
        Evaluate and raise unless the decision is EXECUTE.

        The entry point every gated tool uses, so a refusal happens before any
        side effect rather than partway through one.

        Raises
        ------
        DesktopError
            With a distinct code per decision: ``DESKTOP_CONFIRMATION_REQUIRED``
            is recoverable by retrying with ``confirm=True``,
            ``DESKTOP_ACTION_REJECTED`` is not, and the model needs to be able to
            tell those apart.
        """

        decision = self.evaluate(
            action,
            risk,
            confirmed=confirmed,
            capability=capability,
        )

        if decision.allowed:
            return decision

        if decision.decision is Decision.CONFIRM:
            raise DesktopError(
                code="CONFIRMATION_REQUIRED",
                message=(
                    f"'{action}' is a {risk.value} action and was not confirmed: "
                    f"{decision.reason}."
                ),
                hint=(
                    "Re-issue the call with confirm=true once you are certain "
                    "this is intended. Check the target first."
                ),
            )

        raise DesktopError(
            code="ACTION_REJECTED",
            message=f"'{action}' is not permitted: {decision.reason}.",
            hint=(
                "This is a configuration decision, not a missing confirmation. "
                "Confirming will not change the outcome."
            ),
        )

    # ==========================================================
    # Decision constructors
    # ==========================================================

    def _execute(
        self,
        action: str,
        risk: RiskLevel,
        capability: Capability | None,
        *,
        reason: str,
    ) -> PolicyDecision:

        return PolicyDecision(
            action=action,
            risk=risk,
            decision=Decision.EXECUTE,
            reason=reason,
            capability=capability,
        )

    def _require_confirmation(
        self,
        action: str,
        risk: RiskLevel,
        capability: Capability | None,
        *,
        confirmed: bool,
        reason: str,
    ) -> PolicyDecision:

        if confirmed:

            # Logged at info, not debug: an audit trail that only records the
            # tool call and not the confirmation cannot answer "who authorised
            # deleting that directory?".
            self._logger.bind(
                action=action,
                risk=risk.value,
                capability=capability.value if capability else None,
            ).info("Confirmed high-risk desktop action authorised.")

            return self._execute(
                action,
                risk,
                capability,
                reason="caller supplied explicit confirmation",
            )

        self._logger.bind(
            action=action,
            risk=risk.value,
        ).warning("Desktop action withheld pending confirmation.")

        return PolicyDecision(
            action=action,
            risk=risk,
            decision=Decision.CONFIRM,
            reason=reason,
            capability=capability,
        )

    def _reject(
        self,
        action: str,
        risk: RiskLevel,
        capability: Capability | None,
        *,
        reason: str,
    ) -> PolicyDecision:

        self._logger.bind(
            action=action,
            risk=risk.value,
            capability=capability.value if capability else None,
        ).warning("Desktop action rejected by policy.")

        return PolicyDecision(
            action=action,
            risk=risk,
            decision=Decision.REJECT,
            reason=reason,
            capability=capability,
        )

    # ==========================================================
    # Capability lookup
    # ==========================================================

    def _capability_enabled(self, capability: Capability) -> bool:

        settings = get_settings()

        return {
            Capability.POWER: settings.DESKTOP_ALLOW_POWER_ACTIONS,
            Capability.SHELL: settings.DESKTOP_ALLOW_SHELL,
            Capability.DELETE: settings.DESKTOP_ALLOW_DELETE,
        }[capability]

    def _capability_setting(self, capability: Capability) -> str:
        """
        The setting name behind a capability, so a refusal tells the operator
        which flag to change instead of making them grep for it.
        """

        return {
            Capability.POWER: "DESKTOP_ALLOW_POWER_ACTIONS",
            Capability.SHELL: "DESKTOP_ALLOW_SHELL",
            Capability.DELETE: "DESKTOP_ALLOW_DELETE",
        }[capability]


safety_policy = SafetyPolicy()
"""Process-wide policy. Stateless, so a single instance is safe to share."""
