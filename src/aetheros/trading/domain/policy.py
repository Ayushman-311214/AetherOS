"""
Execution-policy value objects (spec Phase 26 -- "Policy + Execution Safety").

These models express whether a fully-formed :class:`ExecutionRequest` is
*permitted* to move toward a venue, judged *before* the execution engine's
account-level risk gate ever runs. They answer a different question from the
risk layer: risk asks "is this account inside its limits?"; policy asks "is
this kind of order, to this venue, in this mode, allowed at all?".

The spec's required flow is::

    Decision ─► Policy ─► Risk Validation ─► Execution Validation ─► Broker

so policy is the first gate and the one with the widest blast radius: an
analysis-only mode blocks everything; paper mode blocks live venues; a live
order needs an explicit confirmation. Every refusal is deterministic and
carries the rule it broke, so a block can be audited by hand.

Like the risk-limit models these are pure records: a :class:`PolicyCheck` is
one rule's verdict with the value it was judged from, and a
:class:`PolicyVerdict` is the conjunction -- one failed check denies the whole
request, and which rule failed is in :attr:`PolicyVerdict.violations`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import TradingMode


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PolicyCheck:
    """
    One policy rule's verdict, with the reason it passed or failed.

    ``name`` is the rule ("mode", "max_risk_per_trade", "allowed_broker",
    "allowed_instrument", "allowed_strategy", "live_confirmation"); ``reason``
    states the judgement in plain language so a refusal can be read without the
    code. A SKIPPED-style "not applicable" rule is reported as passed with a
    reason that says so, never silently omitted.
    """

    name: str
    passed: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("A policy check needs a name.")
        if not self.reason.strip():
            raise ValueError("A policy check needs its reason.")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class PolicyVerdict:
    """
    Every policy rule's verdict for one request, and whether it may proceed.

    ``allowed`` is the conjunction of all checks: a single failed rule denies
    the request, and the failed rules are in :attr:`violations`. The mode the
    request was judged under and the venue it was aimed at are carried so the
    verdict is self-describing in a log or tool result.
    """

    allowed: bool
    mode: TradingMode
    broker_name: str
    checks: tuple[PolicyCheck, ...]
    captured_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.checks:
            raise ValueError("A policy verdict must carry at least one check.")
        # ``allowed`` must be the honest conjunction of the checks, never a
        # value a caller passed independently -- a verdict that disagrees with
        # its own evidence is not auditable.
        truth = all(check.passed for check in self.checks)
        if self.allowed != truth:
            raise ValueError(
                "A policy verdict's `allowed` must equal the conjunction of "
                "its checks."
            )

    @property
    def violations(self) -> tuple[PolicyCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)

    @property
    def reason(self) -> str:
        """A single-line summary: the violations when denied, else an allow."""
        if self.allowed:
            return f"Permitted under {self.mode.value} mode for '{self.broker_name}'."
        return "; ".join(check.reason for check in self.violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "mode": self.mode.value,
            "broker_name": self.broker_name,
            "reason": self.reason,
            "checks": [check.to_dict() for check in self.checks],
            "violations": [check.to_dict() for check in self.violations],
            "captured_at": self.captured_at.isoformat(),
        }
