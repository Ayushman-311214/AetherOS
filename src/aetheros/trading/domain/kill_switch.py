"""
Kill-switch value objects (spec Phase 2 -- kill switches).

A kill switch is the emergency brake on order admission: a scoped halt that
blocks new orders from reaching a venue until an operator explicitly clears
it. Four scopes cover the required granularity:

* ``GLOBAL``   -- halt every order, to every venue.
* ``STRATEGY`` -- halt orders one strategy id originates.
* ``BROKER``   -- halt orders bound for one venue by name.
* ``SYMBOL``   -- halt orders on one instrument.

A :class:`KillSwitch` records one tripped switch: its scope, the target it
names (a strategy id, a broker name, an instrument key -- empty for GLOBAL,
which has no target), the reason, and when it was tripped. The state is
preserved, not destructive: tripping a switch does not clear the book, close
positions, or cancel orders unless the caller separately asks for that -- the
halt is on *new admission*, which is the conservative, reversible action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(UTC)


class KillScope(str, Enum):
    """The granularity a kill switch halts at."""

    GLOBAL = "global"
    STRATEGY = "strategy"
    BROKER = "broker"
    SYMBOL = "symbol"


@dataclass(frozen=True, slots=True)
class KillSwitch:
    """One tripped halt: scope, target, reason and when."""

    scope: KillScope
    reason: str
    target: str = ""
    tripped_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("A kill switch must record why it was tripped.")
        if self.scope is KillScope.GLOBAL:
            if self.target.strip():
                raise ValueError("A global kill switch has no target.")
        elif not self.target.strip():
            raise ValueError(f"A {self.scope.value} kill switch requires a target.")
        if self.tripped_at.tzinfo is None or self.tripped_at.utcoffset() is None:
            raise ValueError("A kill switch timestamp must be aware.")

    @property
    def scope_key(self) -> str:
        """The storage key this switch occupies ('global', 'strategy:x', ...)."""
        if self.scope is KillScope.GLOBAL:
            return "global"
        return f"{self.scope.value}:{self.target.strip().upper()}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope.value,
            "target": self.target,
            "reason": self.reason,
            "tripped_at": self.tripped_at.isoformat(),
        }
