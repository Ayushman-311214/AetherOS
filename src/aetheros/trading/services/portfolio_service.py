"""
Portfolio-risk allocation service.

Allocates position sizes across a basket of candidate trades so the whole book
respects a total risk budget and a gross-exposure cap (CLAUDE.md section 5 --
the Risk Agent's portfolio-level "position sizing", "exposure" and "drawdown
risk"). It composes nothing stateful and holds no I/O: it is a pure function of a
list of :class:`PortfolioCandidate` geometries (which the tool builds from the
existing per-trade :class:`RiskService`) plus the account equity, so it is
trivially unit-testable and deterministic.

The allocation is deliberately simple and honest (sections 5, 28):

1. Each sizable candidate is budgeted an equal slice of the total risk budget and
   sized to risk at most that slice (``shares = floor(slice / risk_per_share)``).
2. If the resulting gross notional exceeds the exposure cap, every position is
   scaled down by one common factor so the book fits -- never silently levered
   past the cap.
3. A candidate with no usable stop (``risk_per_share <= 0``) is excluded with a
   reason rather than sized on a fabricated risk, and whole-share rounding can
   drop a candidate whose slice is smaller than one share -- also recorded.

It is advisory risk geometry, never a recommendation to trade.
"""

from __future__ import annotations

import math

from ...config.settings import Settings
from ..domain.portfolio import (
    PortfolioCandidate,
    PortfolioPosition,
    PortfolioRiskPlan,
)


class PortfolioRiskService:
    """Deterministic risk-budgeted position allocation across a basket."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def allocate(
        self,
        candidates: list[PortfolioCandidate],
        *,
        account_equity: float,
        max_risk_pct: float | None = None,
        max_exposure_pct: float | None = None,
    ) -> PortfolioRiskPlan:
        risk_pct = (
            max_risk_pct
            if max_risk_pct is not None
            else self._settings.TRADING_PORTFOLIO_MAX_RISK_PCT
        )
        exposure_pct = (
            max_exposure_pct
            if max_exposure_pct is not None
            else self._settings.TRADING_PORTFOLIO_MAX_EXPOSURE_PCT
        )

        limitations: list[str] = []
        if account_equity <= 0.0:
            raise ValueError("account_equity must be positive")

        total_budget = account_equity * risk_pct
        max_exposure = account_equity * exposure_pct

        sizable = [c for c in candidates if c.is_sizable]
        unsizable = [c for c in candidates if not c.is_sizable]

        positions: list[PortfolioPosition] = []
        for c in unsizable:
            limitations.append(
                f"{c.instrument_key}: excluded -- no usable stop (zero risk per share)."
            )
            positions.append(self._excluded(c, "no usable stop (zero risk per share)."))

        if sizable:
            per_trade_budget = total_budget / len(sizable)
            for c in sizable:
                shares = math.floor(per_trade_budget / c.risk_per_share)
                if shares <= 0:
                    positions.append(
                        self._excluded(
                            c,
                            "risk budget slice is smaller than one share at this "
                            "stop distance.",
                        )
                    )
                    limitations.append(
                        f"{c.instrument_key}: excluded -- per-trade risk budget "
                        "buys less than one share."
                    )
                    continue
                positions.append(self._sized(c, float(shares)))

        # Exposure cap: scale all included positions by one common factor if the
        # gross notional overshoots. Whole-share rounding keeps it at or under.
        included = [p for p in positions if p.included]
        gross = sum(p.notional for p in included)
        if gross > max_exposure and gross > 0.0:
            factor = max_exposure / gross
            scaled: list[PortfolioPosition] = []
            for p in positions:
                if not p.included:
                    scaled.append(p)
                    continue
                shares = math.floor(self._shares_of(p) * factor)
                if shares <= 0:
                    scaled.append(
                        self._excluded(
                            self._candidate_of(p),
                            "scaled below one share by the exposure cap.",
                        )
                    )
                    continue
                scaled.append(self._sized(self._candidate_of(p), float(shares)))
            positions = scaled
            limitations.append(
                f"Gross exposure scaled by {factor:.2f} to respect the "
                f"{exposure_pct:.0%} exposure cap."
            )

        included = [p for p in positions if p.included]
        total_risk = round(sum(p.risk_amount for p in included), 2)
        gross_exposure = round(sum(p.notional for p in included), 2)

        return PortfolioRiskPlan(
            account_equity=account_equity,
            total_risk_budget=round(total_budget, 2),
            max_gross_exposure=round(max_exposure, 2),
            positions=tuple(positions),
            total_risk=total_risk,
            gross_exposure=gross_exposure,
            requested=len(candidates),
            included=len(included),
            excluded=len(positions) - len(included),
            within_risk_budget=total_risk <= round(total_budget, 2) + 1e-6,
            within_exposure_cap=gross_exposure <= round(max_exposure, 2) + 1e-6,
            limitations=tuple(limitations),
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _sized(c: PortfolioCandidate, shares: float) -> PortfolioPosition:
        return PortfolioPosition(
            instrument_key=c.instrument_key,
            direction=c.direction,
            entry=c.entry,
            stop=c.stop,
            shares=shares,
            risk_amount=round(shares * c.risk_per_share, 2),
            notional=round(shares * c.entry, 2),
            included=True,
        )

    @staticmethod
    def _excluded(c: PortfolioCandidate, note: str) -> PortfolioPosition:
        return PortfolioPosition(
            instrument_key=c.instrument_key,
            direction=c.direction,
            entry=c.entry,
            stop=c.stop,
            shares=0.0,
            risk_amount=0.0,
            notional=0.0,
            included=False,
            note=note,
        )

    @staticmethod
    def _shares_of(p: PortfolioPosition) -> float:
        return p.shares

    @staticmethod
    def _candidate_of(p: PortfolioPosition) -> PortfolioCandidate:
        risk_per_share = abs(p.entry - p.stop)
        return PortfolioCandidate(
            instrument_key=p.instrument_key,
            direction=p.direction,
            entry=p.entry,
            stop=p.stop,
            risk_per_share=risk_per_share,
        )
