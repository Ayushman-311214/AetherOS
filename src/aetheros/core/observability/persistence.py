"""
Persist a run's trace as JSON Lines.

One file per run inside the active run folder (``logs/run_.../traces/<run_id>.jsonl``),
one :class:`TraceEvent` per line via its ``to_dict()`` projection. The directory
is supplied by the caller (``bootstrapper`` passes ``logging.trace_dir()``, which
resolves inside the current run folder), so a run's traces live beside its logs
rather than in a top-level ``logs/traces`` folder. Append-only and flushed per
line so a crash mid-run still leaves a readable, ordered record -- the same "a
trace that can be edited after the fact is not an audit trail" reasoning that
keeps the event immutable (CLAUDE.md 8/19).

The writer is deliberately dumb: it does not filter by level (the recorder
already decided what to hand it) and it never raises into the caller. A trace
that cannot be written must not take a run down with it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from ..logging import get_logger
from .events import TraceEvent

# Lazy: binding the module logger at import time would create a run directory
# the moment this file is imported (get_logger configures logging on first
# call). A run folder must be created on first *use*, not on import -- so the
# logger is resolved lazily inside the methods that need it.
def _logger():
    return get_logger("trace.persistence")


# Runs without a correlation id still need somewhere to go rather than being
# dropped or crashing on a ``None`` filename.
_UNKNOWN_RUN = "unknown-run"


class TraceFileWriter:
    """Append trace events to a per-run JSONL file.

    Files are opened lazily on the first event for a given ``run_id`` and cached,
    so a run that spans many events pays one ``open`` and interleaved runs each
    get their own handle. :meth:`close` flushes and releases them all.
    """

    def __init__(self, trace_dir: Path) -> None:
        self._dir = Path(trace_dir)
        self._handles: dict[str, TextIO] = {}
        self._ensured = False

    def write(self, event: TraceEvent) -> None:
        """Append one event to its run's file. Never raises."""

        try:
            handle = self._handle_for(event.run_id or _UNKNOWN_RUN)
            handle.write(json.dumps(event.to_dict(), ensure_ascii=False))
            handle.write("\n")
            handle.flush()
        except Exception:
            # Persistence is best-effort; a full disk or a bad path must not
            # break the run being traced.
            _logger().exception("Failed to persist trace event")

    def _handle_for(self, run_id: str) -> TextIO:
        handle = self._handles.get(run_id)
        if handle is not None:
            return handle

        if not self._ensured:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._ensured = True

        path = self._dir / f"{_safe_name(run_id)}.jsonl"
        handle = path.open("a", encoding="utf-8")
        self._handles[run_id] = handle
        return handle

    def close(self) -> None:
        """Flush and close every open file. Safe to call more than once."""

        for handle in self._handles.values():
            try:
                handle.flush()
                handle.close()
            except Exception:
                _logger().exception("Failed to close a trace file")
        self._handles.clear()


def _safe_name(run_id: str) -> str:
    """Reduce a run id to a filename-safe token.

    ``state_id`` values are already tame, but a stray path separator or drive
    colon would otherwise let a trace escape ``trace_dir``; keep only characters
    that are safe on both Windows and POSIX.
    """

    cleaned = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in run_id)
    return cleaned or _UNKNOWN_RUN


__all__ = ["TraceFileWriter"]
