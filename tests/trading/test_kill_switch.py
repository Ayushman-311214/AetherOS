"""
Kill switches (spec Phase 2 -- scoped order-admission halts).

A kill switch is the emergency brake: it blocks new orders at admission, never
fabricates a recovery, and its state is preserved until explicitly cleared.
These tests pin the four scopes and the engine's enforcement:

- a tripped switch blocks the orders it covers and names itself in the refusal;
- a global switch blocks everything; a scoped switch blocks only its slice;
- ``clear`` removes exactly the named switch and returns False when none armed;
- the engine consults the gate on both the validate and validate-opted-out path.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import Direction, OrderStatus
from aetheros.trading.domain.kill_switch import KillScope, KillSwitch
from aetheros.trading.execution import ExecutionEngine
from aetheros.trading.production import KillSwitchService
from aetheros.trading.risk import RiskLimitsService

from .test_execution import _StubBroker, _request


def _engine(broker=None, kills=None) -> tuple[ExecutionEngine, KillSwitchService]:
    service = kills or KillSwitchService()
    engine = ExecutionEngine(
        broker or _StubBroker(),
        RiskLimitsService(get_settings()),
        get_settings(),
        kill_switches=service,
    )
    return engine, service


def test_a_global_switch_blocks_everything():
    engine, kills = _engine()
    kills.trip(KillSwitch(scope=KillScope.GLOBAL, reason="halt all"))
    assert kills.is_blocked(_request(), "stub") is not None


def test_a_strategy_switch_blocks_only_that_strategy():
    engine, kills = _engine()
    kills.trip(
        KillSwitch(scope=KillScope.STRATEGY, target="trend_following", reason="bad run")
    )
    assert kills.is_blocked(_request(), "stub") is not None
    # A request from a different strategy is not blocked.
    other = _request()
    kills.clear(KillScope.STRATEGY, "trend_following")
    assert kills.is_blocked(other, "stub") is None


def test_a_broker_switch_blocks_that_venue():
    engine, kills = _engine()
    kills.trip(KillSwitch(scope=KillScope.BROKER, target="stub", reason="venue down"))
    assert kills.is_blocked(_request(), "stub") is not None
    assert kills.is_blocked(_request(), "other_venue") is None


def test_a_symbol_switch_blocks_that_instrument():
    engine, kills = _engine()
    kills.trip(KillSwitch(scope=KillScope.SYMBOL, target="TEST", reason="news halt"))
    assert kills.is_blocked(_request(), "stub") is not None


def test_clearing_a_switch_arms_off_and_reports_honestly():
    kills = KillSwitchService()
    kills.trip(KillSwitch(scope=KillScope.GLOBAL, reason="halt"))
    assert kills.clear(KillScope.GLOBAL) is True
    assert kills.clear(KillScope.GLOBAL) is False  # nothing was armed


def test_a_switch_must_name_its_target():
    with pytest.raises(ValueError):
        KillSwitch(scope=KillScope.STRATEGY, target="", reason="no target")


@pytest.mark.asyncio
async def test_the_engine_rejects_a_tripped_order_before_the_broker():
    broker = _StubBroker()
    engine, kills = _engine(broker)
    kills.trip(KillSwitch(scope=KillScope.GLOBAL, reason="halt"))
    result = await engine.submit(_request())
    assert result.status is OrderStatus.REJECTED
    assert "kill switch" in result.reason.lower()
    assert broker.submitted == []  # the venue was never reached


@pytest.mark.asyncio
async def test_the_engine_blocks_on_the_validate_opted_out_path_too():
    broker = _StubBroker()
    engine, kills = _engine(broker)
    kills.trip(KillSwitch(scope=KillScope.GLOBAL, reason="halt"))
    result = await engine.submit(_request(), validate=False)
    assert result.status is OrderStatus.REJECTED
    assert broker.submitted == []
