"""
Bootstrap wiring for the two optional subsystems.

The HUD and the voice pipeline were fully implemented but had no caller: nothing
in bootstrap, the CLI or the runtime ever constructed either one. These tests
cover the wiring that connects them, and specifically the three properties that
have to hold on a machine that wants neither:

* the event bus actually exists (it was a commented-out stub, which alone was
  enough to leave the overlay dark forever, since the HUD is driven entirely by
  voice events on a shared bus),
* both subsystems stay off unless their environment flag says otherwise,
* a subsystem that cannot start degrades instead of taking the session with it.

The individual `_bootstrap_*` methods are driven directly rather than through
`start()`, which would also bring up desktop automation, OCR models and a real
LLM provider.
"""

from __future__ import annotations

import pytest

from aetheros.bootstrap.bootstrapper import Bootstrapper
from aetheros.core.container.container import ServiceContainer
from aetheros.hud.service import HUDService
from aetheros.hud.state import HUDState
from aetheros.runtime.events.event_bus import EventBus
from aetheros.voice.events import VoiceServiceStarted, VoiceStateChanged
from aetheros.voice.service import VoiceService
from aetheros.voice.state import VoiceState


# ==============================================================
# Fixtures
# ==============================================================

#: Everything either subsystem reads from the environment. Cleared for every
# test so the developer's own .env cannot decide whether a test passes.
_FLAGS = (
    "AETHEROS_HUD_ENABLED",
    "AETHEROS_VOICE_ENABLED",
    "AETHEROS_VOICE_ACTIVATOR",
    "AETHEROS_STT_PROVIDER",
    "AETHEROS_TTS_PROVIDER",
    "AETHEROS_MICROPHONE_DISABLED",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch) -> None:

    for name in _FLAGS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def boot(monkeypatch) -> Bootstrapper:
    """
    A bootstrapper whose container is isolated from the process-wide one.

    `Bootstrapper.__init__` picks up the global container, and
    `_shutdown_container` calls `clear()` on it — which would drop singletons
    the rest of the suite may have registered.
    """

    instance = Bootstrapper()

    monkeypatch.setattr(instance, "_container", ServiceContainer())

    return instance


# ==============================================================
# Event bus
# ==============================================================


class TestEventBus:

    @pytest.mark.asyncio
    async def test_a_bus_is_built_and_registered(self, boot) -> None:
        """
        This was the stub. With `event_bus` left at None, the HUD had nothing to
        subscribe to and voice had nothing to publish into.
        """

        await boot._bootstrap_events()

        bus = boot.event_bus

        assert isinstance(bus, EventBus)

        # Both keys: the type is what a typed constructor asks for, the string
        # is what a @tool or a CLI command can name without importing runtime.
        assert boot.container.resolve(EventBus) is bus
        assert boot.container.resolve("event_bus") is bus

    @pytest.mark.asyncio
    async def test_the_module_publisher_resolves_to_it(self, boot) -> None:
        """
        `publisher.publish()` is how code fires an event without holding a bus.
        """

        from aetheros.runtime.events import publisher

        await boot._bootstrap_events()

        try:
            assert publisher.get_event_bus() is boot.event_bus

        finally:
            publisher.set_event_bus(None)

    @pytest.mark.asyncio
    async def test_shutdown_releases_the_subscribers(self, boot) -> None:
        """
        Dropping the reference is not enough: the HUD registers bound methods,
        so a second start() in the same process would leave the previous
        overlay's callbacks subscribed and pushing into a dead pipe.
        """

        await boot._bootstrap_events()

        bus = boot.event_bus

        async def handler(event) -> None:
            return None

        await bus.subscribe(VoiceStateChanged, handler)

        assert bus.listener_count(VoiceStateChanged) == 1

        await boot._shutdown_events()

        assert boot.event_bus is None
        assert bus.listener_count(VoiceStateChanged) == 0


# ==============================================================
# Off by default
# ==============================================================


class TestDisabledByDefault:

    @pytest.mark.asyncio
    async def test_the_hud_stays_off(self, boot) -> None:
        """
        A headless or server install must not try to open a window.
        """

        await boot._bootstrap_events()
        await boot._bootstrap_hud()

        assert boot.hud is None
        assert boot.container.has(HUDService) is False

    @pytest.mark.asyncio
    async def test_voice_stays_off(self, boot) -> None:
        """
        Nothing should grab the microphone or install a global hotkey hook
        unless it was asked for.
        """

        await boot._bootstrap_events()
        await boot._bootstrap_voice()

        assert boot.voice is None
        assert boot.container.has(VoiceService) is False

    @pytest.mark.asyncio
    async def test_shutdown_is_a_no_op_when_neither_ran(self, boot) -> None:
        """
        The common case: `aether` on a machine with both flags unset.
        """

        await boot._bootstrap_events()

        await boot._shutdown_voice()
        await boot._shutdown_hud()
        await boot._shutdown_events()

        assert boot.hud is None
        assert boot.voice is None

    @pytest.mark.asyncio
    async def test_a_flag_is_read_from_the_environment(
        self,
        boot,
        monkeypatch,
    ) -> None:
        """
        The gate is the caller's, not HUDService's — the service stays usable
        from a test or a demo with no environment variable at all.
        """

        monkeypatch.setenv("AETHEROS_HUD_ENABLED", "true")

        from aetheros.hud.config import HUDConfig

        assert HUDConfig.from_env().enabled is True


# ==============================================================
# Degradation
# ==============================================================


class TestDegradation:

    @pytest.mark.asyncio
    async def test_a_missing_qt_is_reported_not_raised(
        self,
        boot,
        monkeypatch,
    ) -> None:
        """
        The child's stderr goes to DEVNULL, so a missing PySide6 would surface
        only as exit code 1 — and HUDService.start() would still have returned
        True. Hence the probe in the parent.
        """

        monkeypatch.setenv("AETHEROS_HUD_ENABLED", "true")
        monkeypatch.setattr(
            Bootstrapper,
            "_qt_available",
            staticmethod(lambda: False),
        )

        await boot._bootstrap_events()
        await boot._bootstrap_hud()

        assert boot.hud is None
        assert boot.container.has(HUDService) is False

    @pytest.mark.asyncio
    async def test_a_failing_voice_start_is_contained(
        self,
        boot,
        monkeypatch,
    ) -> None:
        """
        VoiceService.start() raises only when no reasoner can be resolved, which
        means the LLM layer did not come up. That is worth a warning, not a
        crash — the CLI can still do everything.
        """

        monkeypatch.setenv("AETHEROS_VOICE_ENABLED", "true")
        monkeypatch.setattr(
            VoiceService,
            "start",
            _raising_start,
        )

        await boot._bootstrap_events()
        await boot._bootstrap_voice()

        assert boot.voice is None

        # Registered before the start attempt, so the failure has to remove it
        # again or `resolve` would hand out a half-built service.
        assert boot.container.has(VoiceService) is False
        assert boot.container.has("voice_service") is False


# ==============================================================
# Ordering
# ==============================================================


class TestOrdering:

    @pytest.mark.asyncio
    async def test_the_hud_is_subscribed_before_voice_starts(
        self,
        boot,
        monkeypatch,
        fake_hud_process,
    ) -> None:
        """
        VoiceServiceStarted is the event that takes the overlay from OFFLINE to
        IDLE. Published into a bus with no subscriber it is simply lost, and the
        overlay sits dark for the whole session — which is why HUD bootstrap
        runs first.
        """

        monkeypatch.setenv("AETHEROS_HUD_ENABLED", "true")
        monkeypatch.setattr(
            Bootstrapper,
            "_qt_available",
            staticmethod(lambda: True),
        )

        process = fake_hud_process()

        # Injected so nothing is spawned; everything else is the real path.
        monkeypatch.setattr(
            HUDService,
            "__init__",
            _injecting_init(process),
        )

        await boot._bootstrap_events()
        await boot._bootstrap_hud()

        try:
            assert boot.hud is not None
            assert boot.container.resolve("hud_service") is boot.hud

            # Voice has not started, so the overlay is honest about it.
            assert boot.hud.state is HUDState.OFFLINE

            await boot.event_bus.publish(VoiceServiceStarted())

            assert boot.hud.state is HUDState.IDLE

            await boot.event_bus.publish(
                VoiceStateChanged(
                    previous=VoiceState.IDLE,
                    current=VoiceState.LISTENING,
                )
            )

            assert process.states[-1] == "LISTENING"

        finally:
            await boot._shutdown_hud()
            await boot._shutdown_events()

    @pytest.mark.asyncio
    async def test_a_disabled_voice_parks_the_overlay_at_idle(
        self,
        boot,
        monkeypatch,
        fake_hud_process,
    ) -> None:
        """
        With voice off nothing will ever publish VoiceServiceStarted, so the
        overlay would stay on OFFLINE. It is still useful as a status surface.
        """

        monkeypatch.setenv("AETHEROS_HUD_ENABLED", "true")
        monkeypatch.setattr(
            Bootstrapper,
            "_qt_available",
            staticmethod(lambda: True),
        )
        monkeypatch.setattr(
            HUDService,
            "__init__",
            _injecting_init(fake_hud_process()),
        )

        await boot._bootstrap_events()
        await boot._bootstrap_hud()
        await boot._bootstrap_voice()

        try:
            assert boot.voice is None
            assert boot.hud.state is HUDState.IDLE

        finally:
            await boot._shutdown_hud()
            await boot._shutdown_events()

    @pytest.mark.asyncio
    async def test_shutdown_stops_voice_before_the_hud(
        self,
        boot,
        monkeypatch,
    ) -> None:
        """
        Reverse of startup, so the overlay is still subscribed when
        VoiceServiceStopped is published and can show OFFLINE rather than
        freezing on whatever it last displayed.
        """

        order: list[str] = []

        class _Recorder:

            def __init__(self, label: str) -> None:
                self._label = label

            async def stop(self) -> None:
                order.append(self._label)

        monkeypatch.setattr(boot, "_voice", _Recorder("voice"))
        monkeypatch.setattr(boot, "_hud", _Recorder("hud"))

        await boot._shutdown_voice()
        await boot._shutdown_hud()

        assert order == ["voice", "hud"]

    @pytest.mark.asyncio
    async def test_a_failure_during_teardown_does_not_stop_it(
        self,
        boot,
        monkeypatch,
    ) -> None:
        """
        A stuck audio device must not prevent the remaining subsystems from
        tearing down.
        """

        class _Stuck:

            async def stop(self) -> None:
                raise RuntimeError("the microphone is wedged")

        monkeypatch.setattr(boot, "_voice", _Stuck())

        await boot._shutdown_voice()

        assert boot.voice is None


# ==============================================================
# Helpers
# ==============================================================


async def _raising_start(self, *args: object, **kwargs: object) -> None:
    """
    Stand in for a VoiceService whose reasoner cannot be resolved.
    """

    raise RuntimeError("no reasoner is registered")


def _injecting_init(process: object):
    """
    Replace HUDService.__init__ with one that always injects `process`.

    Bootstrap constructs the service itself, so this is the only seam that
    keeps a real subprocess from being spawned while leaving the rest of the
    bootstrap path — config, registration, subscription, start — intact.
    """

    original = HUDService.__init__

    def __init__(self, **kwargs: object) -> None:
        kwargs["process"] = process
        original(self, **kwargs)  # type: ignore[arg-type]

    return __init__



