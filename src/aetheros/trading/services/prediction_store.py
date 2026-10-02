"""
The prediction audit store -- interface plus an in-memory reference impl.

Sections 8, 19 and 28 make prediction history a first-class requirement of the
trading core: every produced report is a prediction with a fixed contract, that
contract must be *auditable*, and the system must *maintain* a history so a past
call can later be checked against what happened. This module supplies the port
that history hangs off:

* :class:`PredictionStore` -- the abstract persistence interface. It is a narrow
  append-and-read contract (``record`` / ``get`` / ``list_records``); it deliberately
  says nothing about retrieval-by-similarity, outcome resolution, calibration
  feedback or learning. Those belong to the deferred Memory intelligence layer,
  which will implement richer stores *behind this same interface* -- so exposing
  the clean port now, with content-addressed ids, is exactly what lets that layer
  arrive later without churning the orchestrator (spec sections 15, 23).
* :class:`InMemoryPredictionStore` -- a dependency-free reference implementation
  used by tests and by any caller that wants an in-process audit trail. It never
  fabricates and never loses a record within its lifetime; it does not persist
  across process restarts, which a durable store (a later increment) will add
  behind the same interface.

A store keeps a prediction verbatim. It never re-judges, upgrades or "corrects" a
recorded call -- a NO_TRADE on mock data is preserved as exactly that (section 15).
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path

from ...core.logging import get_logger
from ..domain.prediction import PredictionRecord
from ..errors import PredictionError

logger = get_logger("trading.prediction_store")


class PredictionStore(ABC):
    """
    Append-and-read persistence port for auditable predictions (section 8).

    Implementations must not fabricate: a lookup that finds nothing returns
    ``None`` / an empty tuple (an honest "not recorded"), and any genuine backing
    failure raises :class:`~aetheros.trading.errors.PredictionError` rather than
    silently swallowing the write. Recording the *same* prediction (same
    content-addressed id) twice is idempotent -- a re-run of the same report must
    not inflate the history.
    """

    @abstractmethod
    async def record(self, record: PredictionRecord) -> str:
        """Persist ``record`` and return its id. Idempotent on the id."""

    @abstractmethod
    async def get(self, prediction_id: str) -> PredictionRecord | None:
        """Return the recorded prediction with this id, or ``None`` if unknown."""

    @abstractmethod
    async def list_records(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[PredictionRecord, ...]:
        """
        Return recorded predictions newest-first.

        Optionally filtered to one ``instrument_key`` and capped at ``limit``.
        """


class InMemoryPredictionStore(PredictionStore):
    """
    Process-local reference store. Deterministic, dependency-free, non-durable.

    Records are held in insertion order and returned newest-first. A lock guards
    mutation so concurrent ``record`` calls from overlapping orchestration runs
    cannot interleave into a corrupt state.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, PredictionRecord] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()

    async def record(self, record: PredictionRecord) -> str:
        async with self._lock:
            if record.id not in self._by_id:
                self._order.append(record.id)
            # Content-addressed: re-recording the same prediction overwrites with
            # an identical value and never appends a duplicate to the history.
            self._by_id[record.id] = record
        return record.id

    async def get(self, prediction_id: str) -> PredictionRecord | None:
        return self._by_id.get(prediction_id)

    async def list_records(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[PredictionRecord, ...]:
        records = [self._by_id[pid] for pid in reversed(self._order)]
        if instrument_key is not None:
            records = [r for r in records if r.instrument_key == instrument_key]
        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be non-negative")
            records = records[:limit]
        return tuple(records)

    def __len__(self) -> int:
        return len(self._by_id)


class FilePredictionStore(PredictionStore):
    """
    A durable, append-only JSON Lines implementation of the same port.

    Each prediction is one newline-terminated JSON object (``PredictionRecord.
    to_dict``) appended to a file, so the audit trail survives process restarts
    (spec sections 8, 15, 19) -- this is the durable implementation the module
    docstring promised, slotting behind the identical interface so the
    orchestrator is untouched. It keeps an in-memory index for reads, loaded
    once from the file on first use.

    Honesty and robustness:
    * It never fabricates. A read that finds nothing returns ``None`` / an empty
      tuple, and a genuine backing failure (an unreadable or unwritable file)
      raises :class:`~aetheros.trading.errors.PredictionError` rather than
      silently losing the write.
    * Recording is idempotent on the content-addressed id: a re-run of the same
      report neither appends a duplicate line nor inflates the history.
    * A crash mid-append can leave at most one trailing partial line; such a line
      (and any other malformed one) is skipped on load with a warning, never
      parsed into a fabricated record.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._by_id: dict[str, PredictionRecord] = {}
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
                    f"Could not read the prediction store at '{self._path}'."
                ) from exc
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = PredictionRecord.from_dict(json.loads(line))
                except (ValueError, KeyError, TypeError):
                    # A malformed or partially-written line is skipped, never
                    # fabricated into a record.
                    logger.warning("Skipping a malformed prediction-store line.")
                    continue
                if record.id not in self._by_id:
                    self._order.append(record.id)
                self._by_id[record.id] = record
        self._loaded = True

    async def record(self, record: PredictionRecord) -> str:
        async with self._lock:
            self._load()
            # Content-addressed + append-only: an already-recorded prediction is
            # already durably on disk, so re-recording writes nothing.
            if record.id in self._by_id:
                return record.id
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                line = json.dumps(record.to_dict(), ensure_ascii=False)
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                raise PredictionError(
                    f"Could not append to the prediction store at '{self._path}'."
                ) from exc
            self._by_id[record.id] = record
            self._order.append(record.id)
        return record.id

    async def get(self, prediction_id: str) -> PredictionRecord | None:
        async with self._lock:
            self._load()
            return self._by_id.get(prediction_id)

    async def list_records(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[PredictionRecord, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        async with self._lock:
            self._load()
            records = [self._by_id[pid] for pid in reversed(self._order)]
        if instrument_key is not None:
            records = [r for r in records if r.instrument_key == instrument_key]
        if limit is not None:
            records = records[:limit]
        return tuple(records)
