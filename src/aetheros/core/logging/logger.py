"""
Central logging framework - entry point.

    from core.logging import setup_logging, logger

    setup_logging(app_name="myservice", json_logs=True)
    logger.info("service starting")

setup_logging() wires up every sink (console, file, debug, error, and
optionally JSON) in one call and is idempotent, so it's safe to call more
than once (app startup, test fixtures, etc.) without duplicating output.
Standard-library `logging` calls - including from third-party dependencies
that don't know about Loguru - are routed through here too, so this really
is the one place logs end up.
"""

from __future__ import annotations

import inspect
import logging as _stdlib_logging
from pathlib import Path
from typing import Union

from loguru import logger

from .handlers import (
    add_console_handler,
    add_debug_handler,
    add_error_handler,
    add_file_handler,
    add_json_handler,
)

StrPath = Union[str, Path]

_configured = False


class _InterceptHandler(_stdlib_logging.Handler):
    """Redirects stdlib `logging` records into Loguru.

    Without this, any dependency that logs via logging.getLogger(...)
    (requests, uvicorn, sqlalchemy, boto3, ...) would bypass this framework
    entirely and fall back to Python's default stderr handler.
    """

    def emit(self, record: _stdlib_logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == _stdlib_logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(
    *,
    log_dir: StrPath = "logs",
    app_name: str = "app",
    console_level: str = "DEBUG",
    file_level: str = "INFO",
    json_logs: bool = False,
    intercept_stdlib_logging: bool = True,
    force: bool = False,
):
    """Configure every sink for the application. Call once, at startup.

    Args:
        log_dir: directory the log files are written into (created if missing).
        app_name: prefix used for the log file names.
        console_level: minimum level printed to the console.
        file_level: minimum level written to the general and JSON log files.
            The debug log always captures DEBUG+ and the error log always
            captures ERROR+, independent of this setting.
        json_logs: also write a structured, one-JSON-object-per-line log
            file alongside the plain-text ones.
        intercept_stdlib_logging: route stdlib `logging` records (from this
            app or any dependency) through Loguru as well.
        force: reconfigure even if setup_logging() already ran once.

    Returns:
        The configured Loguru `logger` instance.
    """
    global _configured
    if _configured and not force:
        return logger

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()  # drop Loguru's default stderr sink; ours replaces it

    add_console_handler(logger, level=console_level)
    add_file_handler(logger, log_dir / f"{app_name}.log", level=file_level)
    add_debug_handler(logger, log_dir / f"{app_name}.debug.log")
    add_error_handler(logger, log_dir / f"{app_name}.error.log")

    if json_logs:
        add_json_handler(logger, log_dir / f"{app_name}.json.log", level=file_level)

    if intercept_stdlib_logging:
        _stdlib_logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    _configured = True
    logger.debug(
        "Logging configured: dir={} app_name={} console={} file={} json={}",
        log_dir, app_name, console_level, file_level, json_logs,
    )
    return logger


__all__ = ["logger", "setup_logging"]