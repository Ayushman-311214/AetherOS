"""
The journal store -- durable persistence for trading-journal entries (Phase 27).

The journal records one traceable entry per paper trade (spec Phase 21), but the
record shape alone is transient: a :class:`~aetheros.trading.services.journal_service.JournalService`
builds entries from a run and hands them back, and when the process exits the
trail is gone. Section 15 ("maintain prediction history", "learn from historical
performance") and section 28 ("maintain prediction history", "measure prediction
performance") require that history to *survive*. This module supplies the store
the journal hangs its durability off, behind the same narrow port the rest of
the trading persistence already uses -- no second storage architecture.

* :class:`JournalStore` -- the abstract port. An upsert-and-read contract keyed on
  the entry's content-addressed ``entry_id``: an entry opens (``from_request``)
  and later closes (``close``) under the *same* id, so re-recording the matured,
  closed entry overwrites the open one in place rather than holding two rows for
  one trade. A genuine backing failure raises
  :class:`~aetheros.trading.errors.PredictionError`; a lookup that finds nothing
  returns ``None`` / an empty tuple (an honest "not recorded").
* :class:`InMemoryJournalStore` -- a dependency-free reference impl for tests and
  for any caller wanting an in-process trail. Non-durable across restarts.
* :class:`FileJournalStore` -- a durable JSON Lines impl (append-per-write,
  last-line-wins per ``entry_id`` on load), mirroring the prediction/outcome
  stores exactly.

A store keeps an entry verbatim. It never re-judges, upgrades or invents one -- a
replayed entry with no risk geometry is preserved as exactly that, and a MOCK
entry stays flagged MOCK. It never fabricates: a malformed or partially-written
line is skipped on load with a warning, never parsed into an invented entry.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path

from ...core.logging import get_logger
from ..domain.journal import JournalEntry
from ..errors import PredictionError

logger = get_logger("trading.journal_store")


class JournalStore(ABC):
    """
    Upsert-and-read persistence port for :class:`JournalEntry` records.

    Keyed on the content-addressed ``entry_id``. Recording an entry whose id is
    already stored overwrites it in place -- which is how an entry maturing from
    open (``from_request``) to closed (``close``) is reflected without leaving a
    stale open row behind. Implementations must not fabricate: an absent lookup
    is ``None`` / an empty tuple, and a genuine backing failure raises
    :class:`~aetheros.trading.errors.PredictionError`.
    """

    @abstractmethod
    async def record(self, entry: JournalEntry) -> str:
        """Persist ``entry`` (upsert on ``entry_id``) and return that id."""

    @abstractmethod
    async def get(self, entry_id: str) -> JournalEntry | None:
        """Return the stored entry with this id, or ``None`` if unknown."""

    @abstractmethod
    async def list_entries(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[JournalEntry, ...]:
        """
        Return stored entries newest-first.

        Optionally filtered to one ``instrument_key`` and capped at ``limit``.
        """


class InMemoryJournalStore(JournalStore):
    """
    Process-local reference store. Deterministic, dependency-free, non-durable.

    Entries are held in first-seen order and returned newest-first. A lock
    guards mutation so concurrent ``record`` calls from overlapping runs cannot
    interleave into a corrupt state.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, JournalEntry] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()

    async def record(self, entry: JournalEntry) -> str:
        async with self._lock:
            if entry.entry_id not in self._by_id:
                self._order.append(entry.entry_id)
            # Upsert: the matured (closed) entry overwrites the open one under
            # the same content-addressed id, never appending a second row.
            self._by_id[entry.entry_id] = entry
        return entry.entry_id

    async def get(self, entry_id: str) -> JournalEntry | None:
        return self._by_id.get(entry_id)

    async def list_entries(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[JournalEntry, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        entries = [self._by_id[eid] for eid in reversed(self._order)]
        if instrument_key is not None:
            entries = [e for e in entries if e.instrument_key == instrument_key]
        if limit is not None:
            entries = entries[:limit]
        return tuple(entries)

    def __len__(self) -> int:
        return len(self._by_id)


class FileJournalStore(JournalStore):
    """
    A durable, append-only JSON Lines implementation of the same port.

    Each entry is one newline-terminated ``JournalEntry.to_dict`` object appended
    to a file, so the journal survives process restarts (spec sections 15, 28).
    On load the file is read front-to-back and the *last* line for a given
    ``entry_id`` wins -- which is how an entry maturing from open to closed across
    writes is reflected without rewriting the file. An in-memory index is loaded
    once from the file on first use and kept in step with every write.

    Honesty and robustness:
    * It never fabricates. A read that finds nothing returns ``None`` / an empty
      tuple, and a genuine backing failure (an unreadable or unwritable file)
      raises :class:`~aetheros.trading.errors.PredictionError` rather than
      silently losing the write.
    * A crash mid-append can leave at most one trailing partial line; such a line
      (and any other malformed one) is skipped on load with a warning, never
      parsed into a fabricated entry.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._by_id: dict[str, JournalEntry] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()
        self._loaded = False

    def _load(self) -> None:
        """Populate the in-memory index from the file (once). Caller holds lock."""
        if self._loaded:
            return
        if self._path.exists():
            try:
                text = self._path.read_text(encoding="utf-8")
            except OSError as exc:
                raise PredictionError(
                    f"Could not read the journal store at '{self._path}'."
                ) from exc
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = JournalEntry.from_dict(json.loads(line))
                except (ValueError, KeyError, TypeError):
                    # A malformed or partially-written line is skipped, never
                    # fabricated into an entry.
                    logger.warning("Skipping a malformed journal-store line.")
                    continue
                if entry.entry_id not in self._by_id:
                    self._order.append(entry.entry_id)
                # Last line wins: a later close overwrites the earlier open.
                self._by_id[entry.entry_id] = entry
        self._loaded = True

    async def record(self, entry: JournalEntry) -> str:
        async with self._lock:
            self._load()
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                line = json.dumps(entry.to_dict(), ensure_ascii=False)
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                raise PredictionError(
                    f"Could not append to the journal store at '{self._path}'."
                ) from exc
            if entry.entry_id not in self._by_id:
                self._order.append(entry.entry_id)
            self._by_id[entry.entry_id] = entry
        return entry.entry_id

    async def get(self, entry_id: str) -> JournalEntry | None:
        async with self._lock:
            self._load()
            return self._by_id.get(entry_id)

    async def list_entries(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[JournalEntry, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        async with self._lock:
            self._load()
            entries = [self._by_id[eid] for eid in reversed(self._order)]
        if instrument_key is not None:
            entries = [e for e in entries if e.instrument_key == instrument_key]
        if limit is not None:
            entries = entries[:limit]
        return tuple(entries)
