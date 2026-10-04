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

import shutil
import sys
from pathlib import Path

from loguru import logger
from datetime import datetime
import os

# from aetheros.config.config_loader import get_settings
from ...config.config_loader import get_settings

settings = get_settings()

LOG_DIR = settings.LOG_DIR
# LOG_DIR.mkdir(exist_ok=True)

DEFAULT_ROTATION = settings.LOG_ROTATION  # "10 MB"
# DEFAULT_RETENTION = settings.LOG_RETENTION  # "14 days"
LOG_RUNS_TO_KEEP = settings.LOG_RUNS_TO_KEEP
DEFAULT_COMPRESSION = settings.LOG_COMPRESSION  # "zip"


def create_run_directory() -> Path:
    """
    Create a unique directory for the current AetherOS execution.

    Example:
        logs/run_20261004_122130_12345/
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    run_dir = LOG_DIR / f"run_{timestamp}"

    run_dir.mkdir(parents=True, exist_ok=False)

    return run_dir


def cleanup_old_runs() -> None:
    """
    Keep only the newest LOG_RUNS_TO_KEEP application runs.

    Each run is represented by a directory:

        logs/
            run_20261004_122130_12345/
            run_20261003_184512_11872/

    Older run directories are completely removed.
    """

    if LOG_RUNS_TO_KEEP < 1:
        raise ValueError("LOG_RUNS_TO_KEEP must be at least 1")

    if not LOG_DIR.exists():
        return

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

    old_runs = run_directories[LOG_RUNS_TO_KEEP:]

    for run_dir in old_runs:
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
    Configure every AetherOS log sink.

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

    # Remove Loguru's default handler and any previous handlers.
    logger.remove()

    # Create a directory for this execution.
    run_dir = create_run_directory()

    # Remove runs older than the newest LOG_RUNS_TO_KEEP runs.
    cleanup_old_runs()

    # Console (opt-in, stderr, never stdout)
    if console:
        logger.add(
            sink=sys.stderr,
            colorize=True,
            level=settings.LOG_LEVEL,
            backtrace=False,
            diagnose=False,
            enqueue=True,
        )

    # Application log
    logger.add(
        run_dir / "app.log",
        rotation=DEFAULT_ROTATION,
        # retention=DEFAULT_RETENTION,
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
        # retention=DEFAULT_RETENTION,
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
        # retention=DEFAULT_RETENTION,
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
        # retention=DEFAULT_RETENTION,
        compression=DEFAULT_COMPRESSION,
        encoding="utf-8",
        diagnose=False,
    )

    logger.info(
        "Logging initialized for AetherOS run: {}",
        run_dir.name,
    )

    return run_dir
