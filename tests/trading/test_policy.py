"""
The execution-policy gate (spec Phase 26 -- "Policy + Execution Safety").

The policy gate is the first admission check on the §9 execution path --
Decision → **Policy** → Risk Validation → Execution Validation → Broker -- and
the one with the widest blast radius. What is pinned here is the safety
contract that gives the phase its name:

- **mode governs venues.** ``analysis_only`` blocks every submission;
  ``paper`` blocks live venues; ``live`` permits them. The default is
  ``paper``, so a live order is an explicit opt-in, never an accident.
- **a live order needs confirmation.** In live mode, a live venue is refused
  unless the caller explicitly confirms the specific order.
- **the gate fails closed.** An unparseable mode is treated as the most
  restrictive; an unknown per-trade risk cannot be shown inside the cap, so it
  is refused.
- **a verdict agrees with its own evidence.** ``allowed`` is always the
  conjunction of the checks -- a verdict cannot claim to permit a request it
  found a violation in.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.brokers.base import BrokerProvider
from aetheros.trading.domain.enums import (
    SourceTier,
    TradingMode,
)
from aetheros.trading.domain.policy import PolicyCheck, PolicyVerdict
from aetheros.trading.policy import ExecutionPolicyService

from .test_execution import _request


# ----------------------------------------------------------------------
# Venues -- a paper venue and a live venue, both inert (policy never submits).
# ----------------------------------------------------------------------
class _PaperVenue(BrokerProvider):
    name = "paper"
    tier = SourceTier.MOCK

    async def submit(self, request):  # pragma: no cover - never called by policy
        raise NotImplementedError

    async def cancel(self, order_id):  # pragma: no cover
        raise NotImplementedError

    async def modify(self, order_id, request):  # pragma: no cover
        raise NotImplementedError

    async def status(self, order_id):  # pragma: no cover
        raise NotImplementedError

    async def fill_price(self, instrument_key):  # pragma: no cover
        return 100.0

    async def account_equity(self):  # pragma: no cover
        return 100_000.0


class _LiveVenue(_PaperVenue):
    name = "live-broker"
    tier = SourceTier.PRIMARY


def _settings(**overrides):
    return get_settings().model_copy(update=overrides)


def _policy(**overrides) -> ExecutionPolicyService:
    return ExecutionPolicyService(_settings(**overrides))


# ----------------------------------------------------------------------
# The value objects
# ----------------------------------------------------------------------
def test_a_check_needs_a_name_and_a_reason():
    with pytest.raises(ValueError, match="name"):
        PolicyCheck(name="   ", passed=True, reason="ok")
    with pytest.raises(ValueError, match="reason"):
        PolicyCheck(name="mode", passed=True, reason="  ")


def test_a_verdict_must_carry_at_least_one_check():
    with pytest.raises(ValueError, match="at least one check"):
        PolicyVerdict(
            allowed=True, mode=TradingMode.PAPER, broker_name="paper", checks=()
        )


def test_a_verdict_cannot_disagree_with_its_own_checks():
    # Claims allowed=True while carrying a failed check -- refused.
    with pytest.raises(ValueError, match="conjunction"):
        PolicyVerdict(
            allowed=True,
            mode=TradingMode.PAPER,
            broker_name="paper",
            checks=(PolicyCheck(name="mode", passed=False, reason="no"),),
        )


def test_violations_and_reason_summarise_the_failures():
    verdict = PolicyVerdict(
        allowed=False,
        mode=TradingMode.PAPER,
        broker_name="live-broker",
        checks=(
            PolicyCheck(name="mode", passed=False, reason="live venue blocked"),
            PolicyCheck(name="max_risk_per_trade", passed=True, reason="inside cap"),
        ),
    )
    assert len(verdict.violations) == 1
    assert verdict.violations[0].name == "mode"
    assert "live venue blocked" in verdict.reason
    assert verdict.to_dict()["allowed"] is False


# ----------------------------------------------------------------------
# Mode governs which venues may be reached
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analysis_only_blocks_every_venue():
    policy = _policy(TRADING_MODE="analysis_only")
    for venue in (_PaperVenue(), _LiveVenue()):
        verdict = policy.evaluate(_request(), venue)
        assert not verdict.allowed
        assert any(c.name == "mode" and not c.passed for c in verdict.checks)


@pytest.mark.asyncio
async def test_paper_mode_permits_the_paper_venue():
    verdict = _policy(TRADING_MODE="paper").evaluate(_request(), _PaperVenue())
    assert verdict.allowed
    assert verdict.mode is TradingMode.PAPER


@pytest.mark.asyncio
async def test_paper_mode_blocks_a_live_venue():
    verdict = _policy(TRADING_MODE="paper").evaluate(_request(), _LiveVenue())
    assert not verdict.allowed
    mode_check = next(c for c in verdict.checks if c.name == "mode")
    assert not mode_check.passed
    assert "live venue" in mode_check.reason


@pytest.mark.asyncio
async def test_an_unparseable_mode_fails_safe_to_analysis_only():
    policy = _policy(TRADING_MODE="banana")
    assert policy.mode is TradingMode.ANALYSIS_ONLY
    verdict = policy.evaluate(_request(), _PaperVenue())
    assert not verdict.allowed


# ----------------------------------------------------------------------
# Live confirmation
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_live_order_without_confirmation_is_refused():
    verdict = _policy(TRADING_MODE="live").evaluate(_request(), _LiveVenue())
    assert not verdict.allowed
    conf = next(c for c in verdict.checks if c.name == "live_confirmation")
    assert not conf.passed


@pytest.mark.asyncio
async def test_a_confirmed_live_order_passes_the_confirmation_check():
    verdict = _policy(TRADING_MODE="live").evaluate(
        _request(), _LiveVenue(), confirmed=True
    )
    assert verdict.allowed


@pytest.mark.asyncio
async def test_confirmation_can_be_disabled_by_configuration():
    verdict = _policy(
        TRADING_MODE="live", TRADING_POLICY_REQUIRE_LIVE_CONFIRMATION=False
    ).evaluate(_request(), _LiveVenue())
    assert verdict.allowed


@pytest.mark.asyncio
async def test_a_paper_order_in_live_mode_needs_no_confirmation():
    verdict = _policy(TRADING_MODE="live").evaluate(_request(), _PaperVenue())
    assert verdict.allowed


# ----------------------------------------------------------------------
# Per-trade risk cap
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_trade_over_the_risk_cap_is_refused():
    over = replace(_request(), risk_pct=5.0)
    verdict = _policy(TRADING_POLICY_MAX_RISK_PER_TRADE_PCT=2.0).evaluate(
        over, _PaperVenue()
    )
    assert not verdict.allowed
    cap = next(c for c in verdict.checks if c.name == "max_risk_per_trade")
    assert not cap.passed
    assert "exceeds" in cap.reason


@pytest.mark.asyncio
async def test_an_unknown_per_trade_risk_fails_closed():
    unknown = replace(_request(), risk_pct=None)
    verdict = _policy(TRADING_POLICY_MAX_RISK_PER_TRADE_PCT=2.0).evaluate(
        unknown, _PaperVenue()
    )
    assert not verdict.allowed
    cap = next(c for c in verdict.checks if c.name == "max_risk_per_trade")
    assert not cap.passed
    assert "fails closed" in cap.reason


@pytest.mark.asyncio
async def test_a_zero_cap_disables_the_risk_check():
    unknown = replace(_request(), risk_pct=None)
    verdict = _policy(TRADING_POLICY_MAX_RISK_PER_TRADE_PCT=0.0).evaluate(
        unknown, _PaperVenue()
    )
    cap = next(c for c in verdict.checks if c.name == "max_risk_per_trade")
    assert cap.passed


# ----------------------------------------------------------------------
# Allow-lists
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_an_empty_broker_allow_list_permits_any_venue():
    verdict = _policy(TRADING_POLICY_ALLOWED_BROKERS="").evaluate(
        _request(), _PaperVenue()
    )
    assert next(c for c in verdict.checks if c.name == "allowed_broker").passed


@pytest.mark.asyncio
async def test_a_venue_outside_the_broker_allow_list_is_refused():
    verdict = _policy(TRADING_POLICY_ALLOWED_BROKERS="zerodha, upstox").evaluate(
        _request(), _PaperVenue()
    )
    assert not verdict.allowed
    assert not next(c for c in verdict.checks if c.name == "allowed_broker").passed


@pytest.mark.asyncio
async def test_a_venue_on_the_broker_allow_list_passes_case_insensitively():
    verdict = _policy(TRADING_POLICY_ALLOWED_BROKERS="PAPER").evaluate(
        _request(), _PaperVenue()
    )
    assert next(c for c in verdict.checks if c.name == "allowed_broker").passed


@pytest.mark.asyncio
async def test_an_instrument_allow_list_matches_the_bare_symbol():
    # ``_request`` builds a request on the signal fixtures' instrument; match it
    # by its symbol to prove exchange need not be pinned.
    symbol = _request().instrument.symbol
    verdict = _policy(TRADING_POLICY_ALLOWED_INSTRUMENTS=symbol).evaluate(
        _request(), _PaperVenue()
    )
    assert next(c for c in verdict.checks if c.name == "allowed_instrument").passed


@pytest.mark.asyncio
async def test_an_instrument_outside_the_allow_list_is_refused():
    verdict = _policy(TRADING_POLICY_ALLOWED_INSTRUMENTS="NOTATRADEABLE").evaluate(
        _request(), _PaperVenue()
    )
    assert not verdict.allowed


@pytest.mark.asyncio
async def test_a_strategy_outside_the_allow_list_is_refused():
    verdict = _policy(TRADING_POLICY_ALLOWED_STRATEGIES="some_other_strategy").evaluate(
        _request(), _PaperVenue()
    )
    assert not verdict.allowed
    assert not next(c for c in verdict.checks if c.name == "allowed_strategy").passed


@pytest.mark.asyncio
async def test_the_requests_own_strategy_passes_the_strategy_allow_list():
    strat = _request().strategy_id
    verdict = _policy(TRADING_POLICY_ALLOWED_STRATEGIES=strat).evaluate(
        _request(), _PaperVenue()
    )
    assert next(c for c in verdict.checks if c.name == "allowed_strategy").passed


# ----------------------------------------------------------------------
# A clean default-settings request is permitted on the paper venue
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_default_paper_request_is_permitted():
    verdict = _policy().evaluate(_request(), _PaperVenue())
    assert verdict.allowed
    assert verdict.violations == ()
