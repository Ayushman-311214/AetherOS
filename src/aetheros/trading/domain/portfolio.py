"""
Portfolio-risk value objects.

Where :class:`~aetheros.trading.domain.risk.RiskAssessment` plans the geometry of
*one* trade, these plan a *basket*: given several candidate trades and an account
equity, allocate position sizes so the whole book respects a total risk budget
and a gross-exposure cap (CLAUDE.md section 5 -- the Risk Agent's "position
sizing", "exposure" and "drawdown risk" at the portfolio level).

It is deterministic and advisory, never a recommendation to trade: each number
traces to the per-trade risk geometry it was built from, and a candidate without
a usable stop is excluded with a reason rather than sized on a fabricated risk
(sections 5, 28).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import Direction


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PortfolioCandidate:
    """One candidate trade feeding the allocator: its directional risk geometry."""

    instrument_key: str
    direction: Direction
    entry: float
    stop: float
    risk_per_share: float  # |entry - stop|, > 0 to be sizable

    @property
    def is_sizable(self) -> bool:
        return self.entry > 0.0 and self.risk_per_share > 0.0


@dataclass(frozen=True, slots=True)
class PortfolioPosition:
    """A candidate after allocation: its size, risk and notional (or why not)."""

    instrument_key: str
    direction: Direction
    entry: float
    stop: float
    shares: float
    risk_amount: float  # shares * risk_per_share
    notional: float  # shares * entry
    included: bool
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "direction": self.direction.value,
            "entry": self.entry,
            "stop": self.stop,
            "shares": self.shares,
            "risk_amount": self.risk_amount,
            "notional": self.notional,
            "included": self.included,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class PortfolioRiskPlan:
    """A deterministic risk-budgeted allocation across a basket of candidates."""

    account_equity: float
    total_risk_budget: float  # currency, = equity * max-risk-pct
    max_gross_exposure: float  # currency, = equity * max-exposure-pct
    positions: tuple[PortfolioPosition, ...]
    total_risk: float
    gross_exposure: float
    requested: int
    included: int
    excluded: int
    within_risk_budget: bool
    within_exposure_cap: bool
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_equity": self.account_equity,
            "total_risk_budget": self.total_risk_budget,
            "max_gross_exposure": self.max_gross_exposure,
            "positions": [p.to_dict() for p in self.positions],
            "total_risk": self.total_risk,
            "gross_exposure": self.gross_exposure,
            "requested": self.requested,
            "included": self.included,
            "excluded": self.excluded,
            "within_risk_budget": self.within_risk_budget,
            "within_exposure_cap": self.within_exposure_cap,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
