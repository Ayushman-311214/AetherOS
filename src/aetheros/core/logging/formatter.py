# """
# Formatting and serialization for the central logging framework.

# - CONSOLE_FORMAT : colorized, human-friendly text for interactive terminals.
# - FILE_FORMAT    : the same layout without ANSI color codes, for on-disk logs.
# - json_formatter : turns each record into a single line of JSON, following
#                     Loguru's own recipe for custom serialization.
# """

# from __future__ import annotations

# import json
# from typing import Any, Dict

# # --------------------------------------------------------------------------
# # Human-readable formats
# # --------------------------------------------------------------------------

# CONSOLE_FORMAT = (
#     "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
#     "<level>{level: <8}</level> | "
#     "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
#     "- <level>{message}</level>"
# )

# FILE_FORMAT = (
#     "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
#     "{level: <8} | "
#     "{process.name}:{thread.name} | "
#     "{name}:{function}:{line} - {message}"
# )


# # --------------------------------------------------------------------------
# # JSON format
# # --------------------------------------------------------------------------

# def _record_to_dict(record: Dict[str, Any]) -> Dict[str, Any]:
#     """Pick a stable, JSON-safe subset of fields off a Loguru record."""
#     payload: Dict[str, Any] = {
#         "timestamp": record["time"].isoformat(),
#         "level": record["level"].name,
#         "logger": record["name"],
#         "module": record["module"],
#         "function": record["function"],
#         "line": record["line"],
#         "message": record["message"],
#         "process": record["process"].name,
#         "thread": record["thread"].name,
#     }

#     exc = record["exception"]
#     if exc is not None:
#         payload["exception"] = {
#             "type": exc.type.__name__ if exc.type else None,
#             "value": str(exc.value) if exc.value is not None else None,
#         }

#     # Anything attached via logger.bind(key=value) shows up here.
#     extra = {k: v for k, v in record["extra"].items() if k != "serialized"}
#     if extra:
#         payload["extra"] = extra

#     return payload


# def json_formatter(record: Dict[str, Any]) -> str:
#     """
#     Loguru 'format' callable used by the JSON sink.

#     Loguru re-applies {field} substitution to whatever string this function
#     returns, so a raw JSON string can't be handed back directly (braces in
#     the payload would be read as format fields). The serialized JSON is
#     stashed on record["extra"] instead and referenced back via a
#     placeholder - the same approach used in Loguru's own docs.
#     """
#     record["extra"]["serialized"] = json.dumps(_record_to_dict(record), default=str)
#     return "{extra[serialized]}\n"




from loguru import logger


def console_format(record: dict) -> str:
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[module]}</cyan> | "
        "<white>{message}</white>\n"
    )


def json_format(record: dict) -> str:
    return "{message}"