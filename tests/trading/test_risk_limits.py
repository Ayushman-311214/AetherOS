"""
RiskLimitsService: the account-level admission gate (spec Phase 9).

The gate the rest of the risk stack did not have: before any *new* position
is opened, is the account as it stands inside its daily-loss and
maximum-exposure boundaries? The per-trade geometry is :class:`RiskService`'s
job and the basket cap is ``PortfolioRiskService``'s, so nothing here
recomputes either -- these tests pin the two properties that matter:

- **fail-closed** -- an input the caller could not measure breaches rather
  than passes, because a gate that cannot see its own input is not a gate;
- **auditable** -- the verdict carries the numbers it judged by, and a breach
  publishes :class:`RiskLimitReached`.

The limits themselves are configuration, so a test can move them and see the
same snapshot judged differently.
"""

from __future__ import annotations

import asyncio

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.enums import RiskBand
from aetheros.trading.domain.risk_limits import (
    AccountSnapshot,
    RiskLimitOutcome,
    RiskLimitsVerdict,
)
from aetheros.trading.events import RiskLimitReached
from aetheros.trading.risk import DAILY_LOSS, MAX_EXPOSURE, RiskLimitsService

#: The shipped defaults, restated so a change to them is a visible test failure
#: rather than a silently retuned gate.
DEFAULT_DAILY_LOSS = 0.03
DEFAULT_MAX_EXPOSURE = 1.0


def _service(**overrides: float) -> RiskLimitsService:
    """A gate whose limits can be moved per test (production reads config)."""
    settings = get_settings().model_copy(update=overrides)
    return RiskLimitsService(settings)


def _snapshot(
    *,
    equity: float = 100_000.0,
    realised_pnl_today: float | None = -1_000.0,
    open_exposure_notional: float | None = 50_000.0,
) -> AccountSnapshot:
    return AccountSnapshot(
        equity=equity,
        realised_pnl_today=realised_pnl_today,
        open_exposure_notional=open_exposure_notional,
    )


# ----------------------------------------------------------------------
# AccountSnapshot


@pytest.mark.parametrize("equity", [0.0, -1.0, float("inf"), float("nan")])
def test_account_snapshot_requires_known_positive_equity(equity):
    with pytest.raises(ValueError, match="equity"):
        AccountSnapshot(equity=equity)


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
@pytest.mark.parametrize(
    "field", ["realised_pnl_today", "open_exposure_notional"]
)
def test_account_snapshot_rejects_a_non_finite_measurement(field, value):
    with pytest.raises(ValueError, match=field):
        AccountSnapshot(equity=100_000.0, **{field: value})


def test_an_unknown_measurement_is_allowed_to_be_none():
    """None is the honest "not measured" -- it is judged, not rejected here."""
    snapshot = AccountSnapshot(
        equity=100_000.0, realised_pnl_today=None, open_exposure_notional=None
    )
    assert snapshot.realised_pnl_today is None


# ----------------------------------------------------------------------
# The small value objects


def test_a_limit_outcome_needs_a_name_and_a_reason():
    with pytest.raises(ValueError, match="name"):
        RiskLimitOutcome(limit_name="  ", passed=True, reason="fine")
    with pytest.raises(ValueError, match="reason"):
        RiskLimitOutcome(limit_name=DAILY_LOSS, passed=True, reason="   ")


def test_a_limit_outcome_rejects_a_non_finite_measurement():
    with pytest.raises(ValueError, match="observed"):
        RiskLimitOutcome(
            limit_name=DAILY_LOSS, passed=True, reason="fine", observed=float("nan")
        )


def test_a_verdict_needs_outcomes_and_equity():
    with pytest.raises(ValueError, match="at least one"):
        RiskLimitsVerdict(outcomes=(), equity=100_000.0)
    outcome = RiskLimitOutcome(limit_name=DAILY_LOSS, passed=True, reason="fine")
    with pytest.raises(ValueError, match="positive equity"):
        RiskLimitsVerdict(outcomes=(outcome,), equity=0.0)


# ----------------------------------------------------------------------
# The allowed path


def test_an_account_inside_its_limits_is_allowed():
    verdict = _service().check(_snapshot())
    assert verdict.allowed
    assert verdict.breached == ()
    assert verdict.risk_band is RiskBand.LOW
    assert {o.limit_name for o in verdict.outcomes} == {DAILY_LOSS, MAX_EXPOSURE}


def test_the_verdict_carries_the_numbers_it_judged():
    """Auditability: the observed fractions and the limits are on the record."""
    verdict = _service().check(_snapshot(realised_pnl_today=-1_000.0))
    daily = next(o for o in verdict.outcomes if o.limit_name == DAILY_LOSS)
    assert daily.observed == pytest.approx(-0.01)
    assert daily.limit == pytest.approx(DEFAULT_DAILY_LOSS)


# ----------------------------------------------------------------------
# Daily loss


def test_the_daily_loss_limit_breaches_at_its_boundary():
    """The rule is 'at or beyond' -- exactly -3% is already the limit."""
    verdict = _service().check(_snapshot(realised_pnl_today=-3_000.0))
    assert not verdict.allowed
    assert [o.limit_name for o in verdict.breached] == [DAILY_LOSS]
    assert "daily loss limit" in verdict.breached[0].reason


def test_a_loss_just_inside_the_limit_still_passes():
    verdict = _service().check(_snapshot(realised_pnl_today=-2_999.99))
    assert verdict.allowed


def test_an_unknown_daily_pnl_fails_closed():
    verdict = _service().check(_snapshot(realised_pnl_today=None))
    assert not verdict.allowed
    daily = next(o for o in verdict.breached if o.limit_name == DAILY_LOSS)
    assert daily.observed is None
    assert "unknown" in daily.reason
    # An unjudgeable account is the *worse* state, and the band says so.
    assert verdict.risk_band is RiskBand.HIGH


# ----------------------------------------------------------------------
# Maximum exposure


def test_the_exposure_limit_is_an_exclusive_ceiling():
    """Observed == limit is inside; only strictly beyond breaches."""
    at_limit = _service().check(
        _snapshot(open_exposure_notional=100_000.0, realised_pnl_today=0.0)
    )
    assert at_limit.allowed

    beyond = _service().check(
        _snapshot(open_exposure_notional=100_000.01, realised_pnl_today=0.0)
    )
    assert not beyond.allowed
    assert [o.limit_name for o in beyond.breached] == [MAX_EXPOSURE]
    assert beyond.breached[0].limit == pytest.approx(DEFAULT_MAX_EXPOSURE)


def test_an_unknown_exposure_fails_closed():
    verdict = _service().check(_snapshot(open_exposure_notional=None))
    assert not verdict.allowed
    exposure = next(o for o in verdict.breached if o.limit_name == MAX_EXPOSURE)
    assert exposure.observed is None
    assert "unknown" in exposure.reason
    assert verdict.risk_band is RiskBand.HIGH


def test_a_measured_breach_is_medium_not_high():
    """Over a boundary but *visible*: an observable breach is the lesser evil."""
    verdict = _service().check(_snapshot(realised_pnl_today=-5_000.0))
    assert not verdict.allowed
    assert verdict.risk_band is RiskBand.MEDIUM


def test_both_limits_can_breach_together_at_equity():
    verdict = _service().check(
        _snapshot(realised_pnl_today=-5_000.0, open_exposure_notional=200_000.0)
    )
    assert {o.limit_name for o in verdict.breached} == {DAILY_LOSS, MAX_EXPOSURE}
    assert verdict.risk_band is RiskBand.MEDIUM


# ----------------------------------------------------------------------
# Configuration and determinism


def test_the_limits_come_from_configuration():
    """The same snapshot, two configurations, two verdicts."""
    snapshot = _snapshot(realised_pnl_today=-2_000.0)  # -2%
    assert _service().check(snapshot).allowed
    strict = _service(TRADING_RISK_DAILY_LOSS_PCT=0.01)
    assert not strict.check(snapshot).allowed


def test_the_verdict_is_deterministic():
    """Pure: the same snapshot always yields the same judgement."""
    service = _service()
    snapshot = _snapshot(realised_pnl_today=-5_000.0)
    first = service.check(snapshot)
    second = service.check(snapshot)
    assert first.to_dict() == second.to_dict()


# ----------------------------------------------------------------------
# The breach event


@pytest.mark.asyncio
async def test_a_breach_publishes_risk_limit_reached():
    bus = EventBus()
    received: list[RiskLimitReached] = []
    await bus.subscribe(RiskLimitReached, lambda event: received.append(event))

    service = RiskLimitsService(get_settings(), event_bus=bus)
    verdict = service.check(_snapshot(realised_pnl_today=-5_000.0))
    assert not verdict.allowed
    # The gate is synchronous and schedules its notification, so give the
    # loop a turn to deliver it.
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert len(received) == 1
    assert received[0].limit_name == DAILY_LOSS
    assert received[0].observed_value == pytest.approx(-0.05)
    assert received[0].reason == verdict.breached[0].reason


@pytest.mark.asyncio
async def test_an_allowed_account_publishes_nothing():
    bus = EventBus()
    received: list[RiskLimitReached] = []
    await bus.subscribe(RiskLimitReached, lambda event: received.append(event))

    service = RiskLimitsService(get_settings(), event_bus=bus)
    assert service.check(_snapshot()).allowed
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert received == []


def test_a_synchronous_caller_without_a_loop_is_not_an_error():
    """A breach outside an event loop is still a verdict; only the ping is lost."""
    bus = EventBus()
    service = RiskLimitsService(get_settings(), event_bus=bus)
    verdict = service.check(_snapshot(realised_pnl_today=-5_000.0))
    assert not verdict.allowed
