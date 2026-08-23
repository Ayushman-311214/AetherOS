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

from pathlib import Path

from loguru import logger

# from aetheros.config.config_loader import get_settings
from ...config.config_loader import get_settings

settings = get_settings()

LOG_DIR = settings.LOG_DIR
LOG_DIR.mkdir(exist_ok=True)


def configure_handlers() -> None:

    logger.remove()

    # Console
    logger.add(
        sink=lambda msg: print(msg, end=""),
        colorize=True,
        level=settings.LOG_LEVEL,
    )

    # Application log
    logger.add(
        LOG_DIR / "app.log",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True,
        level="INFO",
    )

    # Error log
    logger.add(
        LOG_DIR / "error.log",
        rotation="10 MB",
        retention="60 days",
        compression="zip",
        enqueue=True,
        level="ERROR",
        backtrace=True,
        diagnose=True,
    )

    # Debug log
    logger.add(
        LOG_DIR / "debug.log",
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
        level="DEBUG",
    )

    # JSON log
    logger.add(
        LOG_DIR / "events.jsonl",
        serialize=True,
        enqueue=True,
        rotation="25 MB",
    )