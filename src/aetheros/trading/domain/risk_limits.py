"""
Risk-governance value objects (spec Phase 9 -- "daily loss limits, maximum
exposure").

These are *limits*, not geometry: :class:`RiskService` already computes the
per-trade stop, target, ratio and size (the spec's other four Risk Manager
responsibilities), and :class:`PortfolioRiskService` already caps a basket's
total risk and gross exposure at *allocation* time. What neither of them can
do is answer, at decision time, "may this account open anything else right
now?" -- that needs a snapshot of where the account already stands, which is
what these models hold.

The rule is fail-closed: a limit whose inputs cannot be computed (an unknown
realised PnL, an unreadable equity) is reported as breached, never as passed.
A gate that cannot see its own inputs is not a gate (CLAUDE.md sections 5,
28).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import RiskBand


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """
    Where an account stands right now: the inputs the limit checks need.

    ``realised_pnl_today`` and ``open_exposure_notional`` are the caller's
    honest measurements -- typically from a portfolio/position layer. An
    unknown value is ``None``, and the limit checks treat it as a breach
    rather than a pass. ``equity`` must be known and positive or the checks
    cannot run at all.
    """

    equity: float
    realised_pnl_today: float | None = None
    open_exposure_notional: float | None = None
    captured_at: datetime = field(default_factory=_utcnow)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.equity) or self.equity <= 0:
            raise ValueError("Account equity must be a finite positive number.")
        for label, value in (
            ("realised_pnl_today", self.realised_pnl_today),
            ("open_exposure_notional", self.open_exposure_notional),
        ):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{label} must be finite when known.")


@dataclass(frozen=True, slots=True)
class RiskLimitOutcome:
    """
    One limit's verdict, with the numbers it was judged from.

    ``observed``/``limit`` are the compared values in the same unit (fraction
    of equity for both checks, so 0.02 means 2%); ``observed`` is None when
    the input was unknown and the check failed closed.
    """

    limit_name: str
    passed: bool
    reason: str
    observed: float | None = None
    limit: float | None = None

    def __post_init__(self) -> None:
        if not self.limit_name.strip():
            raise ValueError("A limit outcome needs a name.")
        if not self.reason.strip():
            raise ValueError("A limit outcome needs its reason.")
        for label, value in (("observed", self.observed), ("limit", self.limit)):
            if value is not None and not math.isfinite(value):
                raise ValueError(f"A limit outcome's {label} must be finite.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit_name": self.limit_name,
            "passed": self.passed,
            "reason": self.reason,
            "observed": self.observed,
            "limit": self.limit,
        }


@dataclass(frozen=True, slots=True)
class RiskLimitsVerdict:
    """
    Both account-level limits' verdicts, and whether trading may continue.

    ``allowed`` is the conjunction: one breached limit stops new trading, and
    which one is in ``breached``. The overall risk band is derived, never
    set by the caller: all-passed is LOW, a failed-closed (unknown-input)
    breach is HIGH (the engine cannot judge the account), a measured breach
    is MEDIUM (the account is measurably over a boundary but observable).
    """

    outcomes: tuple[RiskLimitOutcome, ...]
    equity: float
    captured_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise ValueError("A verdict requires at least one limit outcome.")
        if not math.isfinite(self.equity) or self.equity <= 0:
            raise ValueError("A verdict requires positive equity.")

    @property
    def allowed(self) -> bool:
        return all(outcome.passed for outcome in self.outcomes)

    @property
    def breached(self) -> tuple[RiskLimitOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if not outcome.passed)

    @property
    def risk_band(self) -> RiskBand:
        if self.allowed:
            return RiskBand.LOW
        if any(outcome.observed is None for outcome in self.breached):
            return RiskBand.HIGH
        return RiskBand.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_band": self.risk_band.value,
            "equity": self.equity,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "breached": [
                outcome.to_dict() for outcome in self.outcomes if not outcome.passed
            ],
            "captured_at": self.captured_at.isoformat(),
        }
