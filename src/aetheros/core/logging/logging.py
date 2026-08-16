from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


# ==========================================================
# Paths
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

LOG_DIR = PROJECT_ROOT / "logs"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

GENERAL_LOG = LOG_DIR / "aetheros.log"
ERROR_LOG = LOG_DIR / "errors.log"


# ==========================================================
# State
# ==========================================================

_CONFIGURED = False
_CONSOLE_ENABLED = False


# ==========================================================
# Setup
# ==========================================================

def setup_logging(
    *,
    console: bool = False,
) -> None:
    """
    Configure AetherOS logging.

    Parameters
    ----------
    console:
        If True, logs are also displayed in terminal.
        If False, terminal stays clean.
    """

    global _CONFIGURED
    global _CONSOLE_ENABLED

    if _CONFIGURED:
        return

    # Remove Loguru's default stderr handler.
    logger.remove()

    # ------------------------------------------------------
    # General application log
    # ------------------------------------------------------

    logger.add(
        GENERAL_LOG,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    # ------------------------------------------------------
    # Error log
    # ------------------------------------------------------

    logger.add(
        ERROR_LOG,
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    # ------------------------------------------------------
    # Optional console logging
    # ------------------------------------------------------

    if console:
        logger.add(
            sys.stderr,
            level="INFO",
            colorize=True,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level:<8}</level> | "
                "{message}"
            ),
        )

        _CONSOLE_ENABLED = True

    _CONFIGURED = True


# ==========================================================
# Logger
# ==========================================================

def get_logger(name: str):
    """
    Return a named AetherOS logger.
    """

    if not _CONFIGURED:
        setup_logging()

    return logger.bind(
        name=f"aetheros.{name}"
    )


# ==========================================================
# Console Control
# ==========================================================

def enable_console_logging() -> None:
    """
    Enable logs in terminal.
    """

    global _CONSOLE_ENABLED

    if _CONSOLE_ENABLED:
        return

    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "{message}"
        ),
    )

    _CONSOLE_ENABLED = True


def disable_console_logging() -> None:
    """
    Disable console logging.

    File logging continues normally.
    """

    global _CONSOLE_ENABLED

    if not _CONSOLE_ENABLED:
        return

    # Reconfigure without console output.
    logger.remove()

    logger.add(
        GENERAL_LOG,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    logger.add(
        ERROR_LOG,
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    _CONSOLE_ENABLED = False