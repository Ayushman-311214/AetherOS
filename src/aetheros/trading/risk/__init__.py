"""
The risk package (spec Phase 9).

The spec's Risk Manager lists six responsibilities. Four -- position sizing,
stop-loss calculation, take-profit calculation, risk/reward -- are already
served deterministically by
:class:`~aetheros.trading.services.risk_service.RiskService` (per trade) and
:class:`~aetheros.trading.services.portfolio_service.PortfolioRiskService`
(across a basket), and are NOT duplicated here. This package adds the
account-level governance those layers cannot express:

- :class:`~aetheros.trading.risk.limits_service.RiskLimitsService` -- the
  admission gate: daily loss limit and maximum exposure, checked *before*
  new trading, fail-closed on unknown inputs, publishing ``RiskLimitReached``
  on a breach.

The admission gate composes with the per-trade engine rather than replacing
it: a proposed trade needs BOTH a sound ``RiskAssessment`` and an account
that is inside its limits.
"""

from __future__ import annotations

from .limits_service import DAILY_LOSS, MAX_EXPOSURE, RiskLimitsService

__all__ = [
    "DAILY_LOSS",
    "MAX_EXPOSURE",
    "RiskLimitsService",
]
