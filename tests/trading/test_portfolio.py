"""
PortfolioRiskService: deterministic risk-budgeted allocation across a basket.

The allocator is a pure function of candidate trade geometries + equity, so these
pin its budgeting and honesty rules directly (CLAUDE.md sections 5, 28): the book
risks at most the total budget split per trade, gross exposure is scaled down to
the cap rather than silently levered past it, a candidate with no usable stop is
excluded with a reason (never sized on a fabricated risk), and sizing is exact
whole-share arithmetic.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction
from aetheros.trading.domain.portfolio import PortfolioCandidate
from aetheros.trading.services.portfolio_service import PortfolioRiskService


def _svc() -> PortfolioRiskService:
    return PortfolioRiskService(get_settings())


def _cand(key: str, entry: float, stop: float) -> PortfolioCandidate:
    return PortfolioCandidate(
        instrument_key=key,
        direction=Direction.UP,
        entry=entry,
        stop=stop,
        risk_per_share=abs(entry - stop),
    )


def test_equal_risk_slices_and_budget_respected():
    # Equity 100k, default 5% total budget = 5,000, two trades -> 2,500 each.
    # Risk/share 5 -> 500 shares each; risk 2,500 each; total 5,000 == budget.
    plan = _svc().allocate(
        [_cand("A", 100.0, 95.0), _cand("B", 50.0, 45.0)],
        account_equity=100_000.0,
        max_exposure_pct=10.0,  # lift exposure cap so the risk math is isolated
    )
    assert plan.included == 2
    by_key = {p.instrument_key: p for p in plan.positions}
    assert by_key["A"].shares == 500.0
    assert by_key["A"].risk_amount == 2500.0
    assert plan.total_risk <= plan.total_risk_budget
    assert plan.within_risk_budget is True


def test_exposure_cap_scales_the_book_down():
    # Two trades whose unscaled notional would blow past a 100% equity cap.
    # Equity 10k, cap 1.0 -> max exposure 10k. Entry 100, stop 99 (risk/share 1):
    # per-trade budget 250 -> 250 shares -> notional 25k each = 50k gross >> 10k.
    plan = _svc().allocate(
        [_cand("A", 100.0, 99.0), _cand("B", 100.0, 99.0)],
        account_equity=10_000.0,
    )
    assert plan.gross_exposure <= plan.max_gross_exposure + 1.0
    assert plan.within_exposure_cap is True
    assert any("exposure cap" in lim for lim in plan.limitations)


def test_candidate_without_a_stop_is_excluded_with_a_reason():
    plan = _svc().allocate(
        [_cand("A", 100.0, 95.0), _cand("NOSTOP", 100.0, 100.0)],
        account_equity=100_000.0,
        max_exposure_pct=10.0,
    )
    excluded = [p for p in plan.positions if not p.included]
    assert any(p.instrument_key == "NOSTOP" for p in excluded)
    assert any("NOSTOP" in lim for lim in plan.limitations)


def test_empty_basket_is_a_valid_empty_plan():
    plan = _svc().allocate([], account_equity=100_000.0)
    assert plan.included == 0
    assert plan.total_risk == 0.0
    assert plan.gross_exposure == 0.0
    assert plan.within_risk_budget is True
    assert plan.within_exposure_cap is True


def test_non_positive_equity_raises():
    with pytest.raises(ValueError):
        _svc().allocate([_cand("A", 100.0, 95.0)], account_equity=0.0)


def test_is_deterministic():
    cands = [_cand("A", 100.0, 95.0), _cand("B", 50.0, 45.0)]
    a = _svc().allocate(cands, account_equity=100_000.0).to_dict()
    b = _svc().allocate(cands, account_equity=100_000.0).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    assert a == b
