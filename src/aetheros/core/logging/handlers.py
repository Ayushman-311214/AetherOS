# """
# Sink configuration for the central logging framework.

# Each add_*_handler() wraps a single logger.add(...) call so sinks can be
# composed and reasoned about independently. `logger` is passed in explicitly
# rather than imported here, keeping these functions decoupled from any one
# Loguru instance (handy for testing).
# """

# from __future__ import annotations

# import sys
# from pathlib import Path
# from typing import Union

# from .formatter import CONSOLE_FORMAT, FILE_FORMAT, json_formatter

# StrPath = Union[str, Path]

# DEFAULT_ROTATION = "10 MB"
# DEFAULT_RETENTION = "14 days"
# DEFAULT_COMPRESSION = "zip"


# def add_console_handler(logger, *, level: str = "DEBUG") -> int:
#     """Colored, human-readable output to stderr."""
#     return logger.add(
#         sys.stderr,
#         format=CONSOLE_FORMAT,
#         level=level,
#         colorize=True,
#         backtrace=False,
#         diagnose=False,
#         enqueue=True,
#     )


# def add_file_handler(
#     logger,
#     path: StrPath,
#     *,
#     level: str = "INFO",
#     rotation: str = DEFAULT_ROTATION,
#     retention: str = DEFAULT_RETENTION,
#     compression: str = DEFAULT_COMPRESSION,
# ) -> int:
#     """General-purpose rotating log file (INFO and above by default)."""
#     return logger.add(
#         path,
#         format=FILE_FORMAT,
#         level=level,
#         rotation=rotation,
#         retention=retention,
#         compression=compression,
#         encoding="utf-8",
#         enqueue=True,
#         backtrace=True,
#         diagnose=False,
#     )


# def add_error_handler(
#     logger,
#     path: StrPath,
#     *,
#     rotation: str = DEFAULT_ROTATION,
#     retention: str = "90 days",
#     compression: str = DEFAULT_COMPRESSION,
# ) -> int:
#     """ERROR+ only, kept in its own file with full diagnostics and a longer
#     retention window, so incidents don't get buried in routine noise."""
#     return logger.add(
#         path,
#         format=FILE_FORMAT,
#         level="ERROR",
#         rotation=rotation,
#         retention=retention,
#         compression=compression,
#         encoding="utf-8",
#         enqueue=True,
#         backtrace=True,
#         diagnose=True,
#     )


# def add_debug_handler(
#     logger,
#     path: StrPath,
#     *,
#     rotation: str = "5 MB",
#     retention: str = "3 days",
#     compression: str = DEFAULT_COMPRESSION,
# ) -> int:
#     """DEBUG+ (i.e. everything). High volume, so it rotates sooner and is
#     kept for a much shorter window than the general/error logs."""
#     return logger.add(
#         path,
#         format=FILE_FORMAT,
#         level="DEBUG",
#         rotation=rotation,
#         retention=retention,
#         compression=compression,
#         encoding="utf-8",
#         enqueue=True,
#         backtrace=True,
#         diagnose=True,
#     )


# def add_json_handler(
#     logger,
#     path: StrPath,
#     *,
#     level: str = "INFO",
#     rotation: str = DEFAULT_ROTATION,
#     retention: str = DEFAULT_RETENTION,
#     compression: str = DEFAULT_COMPRESSION,
# ) -> int:
#     """One JSON object per line - meant for shipping to a log aggregator
#     (ELK, Loki, CloudWatch, etc.) rather than for humans to read directly."""
#     return logger.add(
#         path,
#         format=json_formatter,
#         level=level,
#         rotation=rotation,
#         retention=retention,
#         compression=compression,
#         encoding="utf-8",
#         enqueue=True,
#     )

import os
import shutil
import sys
import threading
from pathlib import Path

from loguru import logger
from datetime import datetime

# from aetheros.config.config_loader import get_settings
from ...config.config_loader import get_settings

settings = get_settings()

LOG_DIR = settings.LOG_DIR

DEFAULT_ROTATION = settings.LOG_ROTATION  # "10 MB"
LOG_RUNS_TO_KEEP = settings.LOG_RUNS_TO_KEEP
DEFAULT_COMPRESSION = settings.LOG_COMPRESSION  # "zip"

# ---------------------------------------------------------------------------
# Single-run tracking
#
# A run directory is created exactly once per process. The first
# ``configure_handlers`` call creates it and records it in ``_ACTIVE_RUN``;
# every subsequent call reuses that same directory and never removes/recreates
# the sinks a second time. The lock makes the create-or-reuse step atomic so a
# bootstrap component and a service resolving logging on two threads cannot
# each mint their own run folder.
# ---------------------------------------------------------------------------

_ACTIVE_RUN: Path | None = None
_RUN_LOCK = threading.Lock()
# Handler id of the optional stderr console sink (None = not attached). Tracked
# so enable/disable_console_logging toggles exactly that one sink instead of
# re-running the whole file-sink setup.
_CONSOLE_SINK_ID: int | None = None


def current_run_dir() -> Path | None:
    """The directory this process's run writes into, or None before init."""
    return _ACTIVE_RUN


def trace_dir() -> Path:
    """
    The directory this run's trace/diagnostic artifacts belong in.

    Always inside the active run directory (``<run>/traces``), never a
    top-level ``logs/traces`` -- a run's traces must live beside its logs so a
    single run folder holds everything that run produced. Before the first
    ``configure_handlers`` there is no run, so this falls back to the shared
    parent to stay import-time safe; in practice the bootstrap creates the run
    before any trace is written.
    """
    if _ACTIVE_RUN is not None:
        return _ACTIVE_RUN / "traces"
    return LOG_DIR / "traces"


def create_run_directory() -> Path:
    """
    Create a unique directory for the current AetherOS execution.

    The name carries the process id so two startups in the same wall-clock
    second can never collide:

        logs/run_20261004_122130_12345/
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()

    run_dir = LOG_DIR / f"run_{timestamp}_{pid}"

    run_dir.mkdir(parents=True, exist_ok=False)

    return run_dir


def cleanup_old_runs(*, keep: int = LOG_RUNS_TO_KEEP, current: Path | None = None) -> None:
    """
    Keep only the newest ``keep`` completed application runs.

    Each run is represented by a directory::

        logs/
            run_20261004_122130_12345/
            run_20261003_184512_11872/

    Older run directories are completely removed. The currently-active run is
    never deleted even if its mtime sorts it out of the newest-N (a long-running
    process does not age out its own live folder).
    """

    if keep < 1:
        raise ValueError("LOG_RUNS_TO_KEEP must be at least 1")

    if not LOG_DIR.exists():
        return

    current = current if current is not None else _ACTIVE_RUN

    run_directories = [
        path
        for path in LOG_DIR.iterdir()
        if path.is_dir() and path.name.startswith("run_")
    ]

    # Newest first.
    run_directories.sort(
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    old_runs = run_directories[keep:]

    for run_dir in old_runs:
        if current is not None and run_dir == current:
            continue  # never delete the live run
        try:
            shutil.rmtree(run_dir)
        except OSError:
            # Logging should never prevent AetherOS from starting.
            logger.warning(
                "Failed to remove old log run: {}",
                run_dir,
            )


def configure_handlers(
    *,
    console: bool = False,
) -> Path:
    """
    Configure every AetherOS log sink and create this process's run directory.

    Idempotent and process-safe: the first call creates the run directory and
    installs the sinks; every later call returns the same run directory without
    touching the sinks (no duplicate ``logger.add`` calls, no second folder).

    Parameters
    ----------
    console:
        Attach a console sink. Off by default: AetherOS renders its own
        terminal UI (see ``cli.ui.CLIUI``) and interleaved log lines would
        corrupt it. When enabled the sink writes to ``stderr`` so that log
        output never mixes into the CLI's stdout.

    Notes
    -----
    ``diagnose`` is disabled on every sink. Loguru's diagnose mode dumps
    the local variables of each frame in a traceback, and frames inside the
    LLM bootstrap hold an ``LLMConfig`` whose repr would otherwise write the
    API key into ``error.log``.
    """

    global _ACTIVE_RUN

    # Remove Loguru's default handler once; we own every sink from here on.
    logger.remove()

    # One run directory per process: reuse the existing one if already created.
    with _RUN_LOCK:
        run_dir = _ACTIVE_RUN
        if run_dir is None:
            run_dir = create_run_directory()
            _ACTIVE_RUN = run_dir

        # Remove runs older than the newest LOG_RUNS_TO_KEEP runs. The live run
        # is excluded by ``cleanup_old_runs`` itself.
        cleanup_old_runs(current=run_dir)

    # Console (opt-in, stderr, never stdout). Idempotent: attaching it a second
    # time removes the prior console sink first so a re-configure never stacks
    # duplicate console handlers.
    set_console(console)

    # Application log
    logger.add(
        run_dir / "app.log",
        rotation=DEFAULT_ROTATION,
        compression=DEFAULT_COMPRESSION,
        enqueue=True,
        level="INFO",
        encoding="utf-8",
        diagnose=False,
    )

    # Error log
    logger.add(
        run_dir / "error.log",
        rotation=DEFAULT_ROTATION,
        compression=DEFAULT_COMPRESSION,
        enqueue=True,
        level="ERROR",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )

    # Debug log
    logger.add(
        run_dir / "debug.log",
        rotation=DEFAULT_ROTATION,
        compression=DEFAULT_COMPRESSION,
        enqueue=True,
        level="DEBUG",
        encoding="utf-8",
        diagnose=False,
    )

    # JSON log
    logger.add(
        run_dir / "events.jsonl",
        serialize=True,
        enqueue=True,
        rotation=DEFAULT_ROTATION,
        compression=DEFAULT_COMPRESSION,
        encoding="utf-8",
        diagnose=False,
    )

    logger.info(
        "Logging initialized for AetherOS run: {}",
        run_dir.name,
    )

    return run_dir


def set_console(enabled: bool) -> None:
    """
    Attach or detach the optional stderr console sink, idempotently.

    ``configure_handlers`` records the sink's handler id, so toggling adds or
    removes exactly that one sink -- never re-running the file-sink setup and
    never stacking duplicate console handlers.
    """
    global _CONSOLE_SINK_ID
    if enabled and _CONSOLE_SINK_ID is None:
        _CONSOLE_SINK_ID = logger.add(
            sink=sys.stderr,
            colorize=True,
            level=settings.LOG_LEVEL,
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )
    elif not enabled and _CONSOLE_SINK_ID is not None:
        try:
            logger.remove(_CONSOLE_SINK_ID)
        except ValueError:
            pass  # already gone
        _CONSOLE_SINK_ID = None
