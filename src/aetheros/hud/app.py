from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from .config import HUDConfig
from .demo import DemoScript, single_state
from .pipe import PipeReader, PipeWriter
from .protocol import (
    MSG_CONFIG,
    MSG_QUIT,
    MSG_SNAPSHOT,
    MessageQueue,
    closed_message,
    drain,
    error_message,
    message_type,
    read_config,
    read_snapshot,
    ready_message,
    stats_message,
)
from .state import HUDSnapshot, HUDState
from .window import HUDWindow

#: How often the render process checks its inbound queue. Fast enough
# that a state change is imperceptible, slow enough to cost nothing.
_POLL_INTERVAL_MS = 25

#: How often frame-rate statistics go back to the parent. Purely for
# `hud status`, so this is deliberately infrequent.
_STATS_INTERVAL_MS = 2000

#: How often the child checks that its parent is still there. Without
# this an orphaned overlay would outlive AetherOS.
_ORPHAN_CHECK_INTERVAL_MS = 1500

#: How long the child waits for the parent's opening config message.
_CONFIG_WAIT_SECONDS = 2.0


class _Reporter:
    """
    Where the render process sends messages.

    Routes to the parent when there is one, and to stderr when running
    standalone. Deliberately does not import the application logger:
    this process must start even if nothing else in AetherOS is
    available, and a spawned process re-configuring loguru sinks would
    duplicate output.
    """

    def __init__(self, outbound: MessageQueue | None) -> None:
        self._outbound = outbound

    def send(self, message: dict[str, Any]) -> None:

        if self._outbound is None:
            return

        try:
            self._outbound.put(message)

        except Exception:
            # The parent has gone away; nothing useful to do.
            pass

    def error(self, text: str) -> None:

        if self._outbound is None:
            print(f"[hud] {text}", file=sys.stderr)

            return

        self.send(error_message(text))


def build_application() -> QApplication:
    """
    Create the QApplication with high-DPI behaviour set correctly.

    The rounding policy has to be set before the application exists,
    which is why this is a function rather than inline setup.
    """

    existing = QApplication.instance()

    if isinstance(existing, QApplication):
        return existing

    # PassThrough keeps fractional scaling intact, so the overlay is
    # the right physical size on 125% and 150% displays instead of
    # being rounded to the nearest integer factor.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    application = QApplication(sys.argv[:1])

    application.setApplicationName("AetherOS HUD")
    application.setApplicationDisplayName("AetherOS")

    # The overlay is the only window; closing it should end the
    # process, but we drive that explicitly so a transient close
    # cannot race the shutdown handshake.
    application.setQuitOnLastWindowClosed(False)

    return application


def run_hud(
    config_data: dict[str, Any] | None = None,
    inbound: MessageQueue | None = None,
    outbound: MessageQueue | None = None,
    *,
    demo: bool = False,
    demo_speed: float = 1.0,
    state: str | None = None,
) -> int:
    """
    Run the overlay until told to stop. Blocks; returns an exit code.

    This is the render process's whole life. It is also directly
    callable, which is what makes `python -m aetheros.hud.app` work
    without any of the rest of AetherOS being started.
    """

    config = (
        HUDConfig.from_dict(config_data)
        if config_data
        else HUDConfig.from_env()
    )

    reporter = _Reporter(outbound)

    try:
        application = build_application()

    except Exception as exc:
        reporter.error(f"Could not create Qt application: {exc}")

        return 1

    closing = {"done": False}

    def finish(reason: str) -> None:
        """
        Single shutdown path, so the parent gets exactly one notice.
        """

        if closing["done"]:
            return

        closing["done"] = True

        reporter.send(closed_message(reason))

        application.quit()

    try:
        window = HUDWindow(
            config,
            on_close=lambda: finish("closed"),
            on_error=reporter.error,
        )

    except Exception as exc:
        reporter.error(f"Could not create HUD window: {exc}")

        return 1

    # ----------------------------------------------------------
    # Initial content
    # ----------------------------------------------------------

    script: DemoScript | None = None
    started_at = time.perf_counter()

    if state is not None:
        window.apply_snapshot(single_state(state))

    elif demo:
        script = DemoScript(speed=demo_speed)

    elif inbound is None:
        # Standalone with no driver and no demo: show the resting
        # state rather than an empty window.
        window.apply_snapshot(HUDSnapshot(state=HUDState.IDLE))

    # ----------------------------------------------------------
    # Timers
    # ----------------------------------------------------------

    timers: list[QTimer] = []

    if script is not None:

        demo_timer = QTimer()
        demo_timer.setInterval(50)

        def advance_demo() -> None:
            elapsed = time.perf_counter() - started_at

            window.apply_snapshot(script.snapshot_at(elapsed))

        demo_timer.timeout.connect(advance_demo)
        timers.append(demo_timer)

    if inbound is not None:

        poll_timer = QTimer()
        poll_timer.setInterval(_POLL_INTERVAL_MS)

        def poll() -> None:
            """
            Apply queued messages, keeping only the newest snapshot.
            """

            latest: HUDSnapshot | None = None

            for message in drain(inbound):

                kind = message_type(message)

                if kind == MSG_SNAPSHOT:
                    # Only the newest matters; intermediate frames are
                    # already history by the time we draw.
                    decoded = read_snapshot(message)

                    if decoded is not None:
                        latest = decoded

                elif kind == MSG_CONFIG:
                    payload = read_config(message)

                    if payload is not None:
                        try:
                            window.apply_config(
                                HUDConfig.from_dict(payload)
                            )

                        except Exception as exc:
                            reporter.error(
                                f"Bad HUD config: {exc}"
                            )

                elif kind == MSG_QUIT:
                    finish("quit")

                    return

            if latest is not None:
                window.apply_snapshot(latest)

        poll_timer.timeout.connect(poll)
        timers.append(poll_timer)

        # ------------------------------------------------------
        # Statistics
        # ------------------------------------------------------

        stats_timer = QTimer()
        stats_timer.setInterval(_STATS_INTERVAL_MS)

        stats_timer.timeout.connect(
            lambda: reporter.send(
                stats_message(
                    window.scene.fps,
                    window.scene.quality,
                )
            )
        )

        timers.append(stats_timer)

        # ------------------------------------------------------
        # Orphan guard
        # ------------------------------------------------------

        orphan_timer = QTimer()
        orphan_timer.setInterval(_ORPHAN_CHECK_INTERVAL_MS)

        def check_parent() -> None:
            """
            Exit if the parent is gone.

            The normal path is an explicit quit message; this only
            covers the parent dying without one, which must not leave
            an overlay stranded on the desktop. A closed inbound stream
            is the signal, because a pipe ends when the process holding
            the other end does. Queues used in tests have no such
            attribute, so this quietly does nothing there.
            """

            if getattr(inbound, "closed", False):
                finish("orphaned")

        orphan_timer.timeout.connect(check_parent)
        timers.append(orphan_timer)

    # ----------------------------------------------------------
    # Signals
    # ----------------------------------------------------------

    def handle_signal(*_: object) -> None:
        finish("signal")

    for name in ("SIGINT", "SIGTERM"):

        handler = getattr(signal, name, None)

        if handler is None:
            continue

        try:
            signal.signal(handler, handle_signal)

        except (ValueError, OSError):
            # Not the main thread, or unsupported on this platform.
            pass

    # ----------------------------------------------------------
    # Run
    # ----------------------------------------------------------

    try:
        window.start()

        for timer in timers:
            timer.start()

        reporter.send(ready_message(os.getpid()))

        code = application.exec()

    except Exception as exc:
        reporter.error(f"HUD event loop failed: {exc}")

        code = 1

    finally:
        for timer in timers:
            try:
                timer.stop()

            except Exception:
                pass

        try:
            window.stop()
            window.close()

        except Exception:
            pass

        # If we are leaving for any reason other than an explicit
        # quit, the parent still needs to know.
        finish("exited")

    return int(code)


# ==============================================================
# Parent-driven mode
# ==============================================================


def _initial_config(
    inbound: PipeReader,
    timeout: float = _CONFIG_WAIT_SECONDS,
) -> dict[str, Any] | None:
    """
    Wait briefly for the parent's opening config message.

    Without this the window would be built from the environment and
    then rebuilt from the parent's config a frame later, which is
    visible as the overlay appearing and then jumping.

    Anything else arriving first is handed back rather than dropped, so
    no message is lost if the parent has already started pushing state.
    """

    try:
        message = inbound.get(timeout=timeout)

    except Exception:
        # Nothing arrived. Fall back to the environment, which is also
        # what a hand-run `--ipc` process gets.
        return None

    if message_type(message) == MSG_CONFIG:
        return read_config(message)

    inbound.put(message)

    return None


def _run_ipc(
    *,
    demo: bool = False,
    demo_speed: float = 1.0,
    state: str | None = None,
) -> int:
    """
    Run driven by a parent process over stdio.

    This is how HUDService starts the overlay: the parent owns the
    lifecycle and pushes state, so nothing here has to reach into the
    rest of AetherOS.
    """

    if sys.stdin is None or sys.stdout is None:
        print(
            "[hud] --ipc needs both stdin and stdout.",
            file=sys.stderr,
        )

        return 2

    # UTF-8 explicitly: on Windows these streams default to the ANSI
    # code page, which would mangle any non-ASCII character in a
    # transcript or a response.
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")

        except Exception:
            pass

    outbound = PipeWriter(sys.stdout)

    inbound = PipeReader(sys.stdin)
    inbound.start()

    # The protocol now owns the real stdout, so point everything else
    # at stderr. A stray print from Qt, a plugin or a library must not
    # be able to interleave with a message mid-line.
    sys.stdout = sys.stderr

    try:
        return run_hud(
            _initial_config(inbound),
            inbound,
            outbound,
            demo=demo,
            demo_speed=demo_speed,
            state=state,
        )

    finally:
        # No wait: this process is exiting, and the reader is a daemon
        # blocked on a stdin read that only the parent can end.
        inbound.stop(timeout=0.0)

        outbound.close()


# ==============================================================
# Command line
# ==============================================================


def main(argv: list[str] | None = None) -> int:
    """
    Standalone entry point.

    Exists so the HUD can be developed and visually verified with no
    microphone, no LLM and none of the rest of AetherOS running.
    """

    parser = argparse.ArgumentParser(
        prog="aetheros-hud",
        description="Run the AetherOS HUD overlay on its own.",
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="cycle through every state continuously",
    )

    parser.add_argument(
        "--state",
        metavar="NAME",
        help=(
            "hold a single state: IDLE, LISTENING, TRANSCRIBING, "
            "THINKING, EXECUTING, SPEAKING or ERROR"
        ),
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="demo speed multiplier (default 1.0)",
    )

    parser.add_argument(
        "--position",
        help='anchor name, or "x,y" in logical pixels',
    )

    parser.add_argument(
        "--size",
        type=int,
        help="overlay edge length in logical pixels",
    )

    parser.add_argument(
        "--opacity",
        type=float,
        help="window opacity, 0.15 to 1.0",
    )

    parser.add_argument(
        "--quality",
        choices=("auto", "low", "medium", "high"),
        help="render quality tier",
    )

    parser.add_argument(
        "--fps",
        type=int,
        help="target frame rate",
    )

    parser.add_argument(
        "--theme",
        help="colour theme name",
    )

    parser.add_argument(
        "--click-through",
        action="store_true",
        help="let mouse clicks pass through the overlay",
    )

    parser.add_argument(
        "--ipc",
        action="store_true",
        help=(
            "take state from a parent process over stdin and report "
            "back on stdout (used by HUDService)"
        ),
    )

    args = parser.parse_args(argv)

    if args.ipc:
        # The parent owns the configuration, so the overrides below are
        # deliberately not applied here.
        return _run_ipc(
            demo=args.demo,
            demo_speed=args.speed,
            state=args.state,
        )

    config = HUDConfig.from_env()

    # Command-line arguments win over the environment, so a developer
    # can override without editing .env.
    if args.position is not None:
        config.position = args.position

    if args.size is not None:
        config.size = args.size

    if args.opacity is not None:
        config.opacity = max(0.15, min(1.0, args.opacity))

    if args.quality is not None:
        config.animation_quality = args.quality

    if args.fps is not None:
        config.fps = args.fps

    if args.theme is not None:
        config.theme = args.theme

    if args.click_through:
        config.click_through = True

    return run_hud(
        config.to_dict(),
        demo=args.demo or args.state is None,
        demo_speed=args.speed,
        state=args.state,
    )


if __name__ == "__main__":
    raise SystemExit(main())
