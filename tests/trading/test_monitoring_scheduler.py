"""
MonitoringScheduler: the bounded, opt-in autonomous loop (spec section 29).

A fake monitoring service (counting sweeps, no network) stands in for the real
one, so these pin the loop's lifecycle and safety: it does not start when
disabled, it sweeps repeatedly on a short interval when enabled, stop() cancels
it cleanly, and a failing sweep does not kill the loop.
"""

from __future__ import annotations

import asyncio

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.services.monitoring_scheduler import MonitoringScheduler


class _FakeMonitoring:
    def __init__(self, *, fail_first: bool = False) -> None:
        self.runs = 0
        self._fail_first = fail_first
        self.ran = asyncio.Event()

    async def run_once(self, **kwargs):
        self.runs += 1
        if self._fail_first and self.runs == 1:
            raise RuntimeError("sweep boom")
        self.ran.set()
        return None


def _settings(enabled: bool, interval: float = 0.01):
    s = get_settings()
    # Override just the two knobs on a copy-like shim: pydantic settings are
    # frozen-ish, so patch via object.__setattr__ on a shallow proxy.
    class _S:
        TRADING_MONITOR_ENABLED = enabled
        TRADING_MONITOR_INTERVAL_SECONDS = interval

    return _S()


@pytest.mark.asyncio
async def test_disabled_scheduler_does_not_start():
    sched = MonitoringScheduler(_FakeMonitoring(), _settings(enabled=False))
    started = await sched.start()
    assert started is False
    assert sched.is_running is False


@pytest.mark.asyncio
async def test_enabled_scheduler_sweeps_then_stops_cleanly():
    mon = _FakeMonitoring()
    sched = MonitoringScheduler(mon, _settings(enabled=True, interval=0.01))
    started = await sched.start()
    assert started is True
    assert sched.is_running is True

    await asyncio.wait_for(mon.ran.wait(), timeout=2.0)
    assert mon.runs >= 1

    await sched.stop()
    assert sched.is_running is False


@pytest.mark.asyncio
async def test_a_failing_sweep_does_not_kill_the_loop():
    mon = _FakeMonitoring(fail_first=True)
    sched = MonitoringScheduler(mon, _settings(enabled=True, interval=0.01))
    await sched.start()
    # The first sweep raises; the loop must survive and run again.
    await asyncio.wait_for(mon.ran.wait(), timeout=2.0)
    assert mon.runs >= 2
    await sched.stop()


@pytest.mark.asyncio
async def test_run_once_now_bypasses_the_schedule():
    mon = _FakeMonitoring()
    sched = MonitoringScheduler(mon, _settings(enabled=False))
    await sched.run_once_now()
    assert mon.runs == 1
