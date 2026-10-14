"""
Policy decisions: the vocabulary the agent policy layer answers in.

Three outcomes, and only three. The policy engine is asked "may this tool run?"
before anything runs, and it answers :class:`PolicyDecision.ALLOW`,
:class:`PolicyDecision.DENY`, or :class:`PolicyDecision.REQUIRE_CONFIRMATION`.
It never runs the tool itself -- deciding and doing are separate layers, which
is what lets the same decision be logged, shown to a user, or replayed without a
side effect riding along.

This mirrors the desktop layer's ``Decision`` (EXECUTE / CONFIRM / REJECT) in
spirit, but stays a distinct type: that one gates a single desktop tool from
inside it, this one gates *any* agent tool call from above the executor, and
collapsing them would tie the agent's contract to the desktop package.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

# Audit codes. One per reason a decision was reached, so a refusal in the log or
# the transcript says *why* rather than just "denied", and a rename has one home.
POLICY_ALLOWED = "policy_allowed"
POLICY_DENIED_TOOL = "policy_denied_tool"
POLICY_NOT_ALLOWED = "policy_not_allowed"
POLICY_CONFIRMATION_REQUIRED = "policy_confirmation_required"
POLICY_EMERGENCY_STOP = "policy_emergency_stop"
POLICY_ITERATION_LIMIT = "policy_iteration_limit"
POLICY_INVALID_ARGUMENTS = "policy_invalid_arguments"
POLICY_FAILURE = "policy_failure"


class PolicyDecision(str, Enum):
    """What the policy decided about one requested tool call.

    ``str``-valued so a serialized decision reads as ``{"decision": "allow"}``,
    matching ``AgentStatus`` and ``ExecutionStatus``.
    """

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    """The policy's answer to one request, as data.

    Returned rather than raised so a caller can ask what *would* happen (a dry
    run, a confirmation prompt) without a refusal exploding mid-round, and so
    the ``reason`` reaches the model verbatim instead of being flattened into a
    generic denial it cannot act on.
    """

    tool: str
    decision: PolicyDecision
    reason: str
    code: str
    iteration: int = 0

    #: Advisory execution budget for this call. The policy does not enforce it
    #: -- it holds no clock and runs nothing -- it reports the ceiling the
    #: executor should apply, so the timeout policy lives in one place.
    timeout_seconds: float | None = None

    @property
    def allowed(self) -> bool:
        return self.decision is PolicyDecision.ALLOW

    @property
    def denied(self) -> bool:
        return self.decision is PolicyDecision.DENY

    @property
    def requires_confirmation(self) -> bool:
        return self.decision is PolicyDecision.REQUIRE_CONFIRMATION

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "decision": self.decision.value,
            "reason": self.reason,
            "code": self.code,
            "iteration": self.iteration,
            "timeout_seconds": self.timeout_seconds,
        }


__all__ = [
    "POLICY_ALLOWED",
    "POLICY_CONFIRMATION_REQUIRED",
    "POLICY_DENIED_TOOL",
    "POLICY_EMERGENCY_STOP",
    "POLICY_FAILURE",
    "POLICY_INVALID_ARGUMENTS",
    "POLICY_ITERATION_LIMIT",
    "POLICY_NOT_ALLOWED",
    "PolicyDecision",
    "PolicyEvaluation",
]
