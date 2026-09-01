"""
Shared HUD test doubles.

Nothing here touches Qt, a display, or a subprocess: the point is that
the service layer is fully exercisable on a headless machine.
"""

from __future__ import annotations

from typing import Any

from ...src.aetheros.hud.protocol import Message, ready_message, stats_message


class FakeHUDProcess:
    """
    Stands in for HUDProcess without launching anything.

    Records what the service sends and lets a test feed messages back,
    so the whole event -> snapshot -> transport path can be checked
    without a window existing.
    """

    def __init__(
        self,
        *,
        can_start: bool = True,
        failure: str | None = None,
    ) -> None:

        self._can_start = can_start

        self.failure = failure
        self.sent: list[Message] = []
        self.inbox: list[Message] = []

        self.is_alive = False
        self.ready = False
        self.pid: int | None = None
        self.exit_code: int | None = None
        self.stream_closed = False

        self.start_calls = 0
        self.stop_calls = 0

    # ----------------------------------------------------------
    # HUDProcess surface
    # ----------------------------------------------------------

    def start(self) -> bool:

        self.start_calls += 1

        if not self._can_start:
            self.failure = self.failure or "Qt is unavailable."

            return False

        self.is_alive = True
        self.pid = 4242

        return True

    def stop(self, timeout: float = 4.0) -> None:

        self.stop_calls += 1

        self.is_alive = False
        self.ready = False
        self.exit_code = 0

    def send(self, message: Message) -> bool:

        if not self.is_alive:
            return False

        self.sent.append(message)

        return True

    def poll(self) -> list[Message]:

        messages = list(self.inbox)
        self.inbox.clear()

        return messages

    def mark_ready(self, pid: int | None = None) -> None:

        self.ready = True

        if pid is not None:
            self.pid = pid

    # ----------------------------------------------------------
    # Test helpers
    # ----------------------------------------------------------

    def report_ready(self, pid: int = 9001) -> None:
        self.inbox.append(ready_message(pid))

    def report_stats(self, fps: float = 60.0, quality: str = "high") -> None:
        self.inbox.append(stats_message(fps, quality))

    def crash(self, exit_code: int = 3) -> None:
        """
        Die the way a Qt failure does: gone, with a non-zero code.
        """

        self.is_alive = False
        self.exit_code = exit_code
        self.stream_closed = True

    @property
    def snapshots(self) -> list[dict[str, Any]]:
        """
        Every snapshot payload sent, oldest first.
        """

        return [
            message["snapshot"]
            for message in self.sent
            if message.get("type") == "snapshot"
        ]

    @property
    def states(self) -> list[str]:
        """
        The state of every snapshot sent, in order.
        """

        return [str(payload.get("state")) for payload in self.snapshots]

    @property
    def last_snapshot(self) -> dict[str, Any]:

        payloads = self.snapshots

        return payloads[-1] if payloads else {}

FakeHUDProcess.start()