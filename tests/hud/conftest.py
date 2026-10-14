"""
Fixtures for the HUD tests.

The process double lives in ``tests/hud_support.py`` and is also exposed from
the root conftest as ``fake_hud_process``, since the bootstrap wiring tests need
it too. These fixtures are the HUD-specific conveniences on top of it: a bus, a
builder, and a started service that is stopped again on teardown.
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from hud_support import FakeHUDProcess

from aetheros.hud.config import HUDConfig
from aetheros.hud.service import HUDService
from aetheros.runtime.events.event_bus import EventBus


@pytest.fixture
def bus() -> EventBus:
    """
    A bus isolated from the process-wide publisher.
    """

    return EventBus()


@pytest.fixture
def process() -> FakeHUDProcess:
    """
    A HUD child process that never launches anything.
    """

    return FakeHUDProcess()


@pytest.fixture
def fake_process() -> type[FakeHUDProcess]:
    """
    The double's class, for tests that need a differently configured one.
    """

    return FakeHUDProcess


@pytest.fixture
def make_service(bus):
    """
    Build an unstarted service over a fake process.
    """

    def build(
        process: FakeHUDProcess | None = None,
        **overrides: Any,
    ) -> HUDService:

        return HUDService(
            config=HUDConfig(enabled=True, **overrides),
            event_bus=bus,
            process=(
                process if process is not None else FakeHUDProcess()
            ),
        )

    return build


@pytest_asyncio.fixture
async def service(make_service, process):
    """
    A started service, stopped again on teardown.

    `start()` creates the pump task, so a service left running would outlive
    the test's event loop.
    """

    started = make_service(process)

    assert await started.start() is True

    try:
        yield started

    finally:
        await started.stop()
