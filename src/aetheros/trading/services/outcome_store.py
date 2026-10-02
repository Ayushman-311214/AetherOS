"""
The outcome store -- durable accumulation of resolved prediction outcomes.

Where the :class:`~aetheros.trading.services.prediction_store.PredictionStore`
holds the predictions as they are *made*, this holds the outcomes as they are
*resolved* -- so a monitoring sweep's results accumulate over time instead of
being recomputed from scratch each pass (CLAUDE.md sections 15, 29, the "Observe
Result -> Evaluate -> Learn" rung). It is the storage foundation the learning
layer will read from; it does not itself learn or recalibrate (that remains
deferred).

* :class:`OutcomeStore` -- the abstract port. A narrow upsert-and-read contract
  keyed on the outcome's ``prediction_id``: re-recording the same prediction's
  outcome overwrites in place (an outcome can mature from PENDING to RESOLVED
  across sweeps -- the latest reading wins), so the store never holds two
  outcomes for one prediction. A genuine backing failure raises
  :class:`~aetheros.trading.errors.PredictionError`; a lookup that finds nothing
  returns ``None`` / an empty tuple.
* :class:`InMemoryOutcomeStore` -- process-local reference impl.
* :class:`FileOutcomeStore` -- durable JSON Lines impl (append-per-write,
  last-line-wins per prediction_id on load), mirroring the prediction store.

It never fabricates: a malformed or partially-written line is skipped on load,
never parsed into an invented outcome.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path

from ...core.logging import get_logger
from ..domain.outcome import PredictionOutcome
from ..errors import PredictionError

logger = get_logger("trading.outcome_store")


class OutcomeStore(ABC):
    """Upsert-and-read persistence port for resolved prediction outcomes."""

    @abstractmethod
    async def record(self, outcome: PredictionOutcome) -> str:
        """Persist ``outcome`` (upsert on prediction_id) and return that id."""

    @abstractmethod
    async def get(self, prediction_id: str) -> PredictionOutcome | None:
        """Return the stored outcome for this prediction id, or ``None``."""

    @abstractmethod
    async def list_outcomes(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[PredictionOutcome, ...]:
        """Return stored outcomes newest-first, optionally filtered and capped."""


class InMemoryOutcomeStore(OutcomeStore):
    """Process-local reference store. Deterministic, dependency-free, non-durable."""

    def __init__(self) -> None:
        self._by_id: dict[str, PredictionOutcome] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()

    async def record(self, outcome: PredictionOutcome) -> str:
        async with self._lock:
            if outcome.prediction_id not in self._by_id:
                self._order.append(outcome.prediction_id)
            self._by_id[outcome.prediction_id] = outcome
        return outcome.prediction_id

    async def get(self, prediction_id: str) -> PredictionOutcome | None:
        return self._by_id.get(prediction_id)

    async def list_outcomes(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[PredictionOutcome, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        outcomes = [self._by_id[pid] for pid in reversed(self._order)]
        if instrument_key is not None:
            outcomes = [o for o in outcomes if o.instrument_key == instrument_key]
        if limit is not None:
            outcomes = outcomes[:limit]
        return tuple(outcomes)

    def __len__(self) -> int:
        return len(self._by_id)


class FileOutcomeStore(OutcomeStore):
    """
    Durable JSON Lines outcome store (append-per-write, last-line-wins on load).

    Each ``record`` appends one newline-terminated ``PredictionOutcome.to_dict``
    line; on load the file is read front-to-back so the *last* line for a given
    prediction_id wins -- which is how an outcome maturing from PENDING to
    RESOLVED across sweeps is reflected without rewriting the file. A read/write
    failure raises :class:`PredictionError`; a malformed or partially-written
    line is skipped with a warning, never fabricated into an outcome.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._by_id: dict[str, PredictionOutcome] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        if self._path.exists():
            try:
                text = self._path.read_text(encoding="utf-8")
            except OSError as exc:
                raise PredictionError(
                    f"Could not read the outcome store at '{self._path}'."
                ) from exc
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    outcome = PredictionOutcome.from_dict(json.loads(line))
                except (ValueError, KeyError, TypeError):
                    logger.warning("Skipping a malformed outcome-store line.")
                    continue
                if outcome.prediction_id not in self._by_id:
                    self._order.append(outcome.prediction_id)
                # Last line wins: a later sweep's maturer reading overwrites.
                self._by_id[outcome.prediction_id] = outcome
        self._loaded = True

    async def record(self, outcome: PredictionOutcome) -> str:
        async with self._lock:
            self._load()
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                line = json.dumps(outcome.to_dict(), ensure_ascii=False)
                with self._path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError as exc:
                raise PredictionError(
                    f"Could not append to the outcome store at '{self._path}'."
                ) from exc
            if outcome.prediction_id not in self._by_id:
                self._order.append(outcome.prediction_id)
            self._by_id[outcome.prediction_id] = outcome
        return outcome.prediction_id

    async def get(self, prediction_id: str) -> PredictionOutcome | None:
        async with self._lock:
            self._load()
            return self._by_id.get(prediction_id)

    async def list_outcomes(
        self, *, instrument_key: str | None = None, limit: int | None = None
    ) -> tuple[PredictionOutcome, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        async with self._lock:
            self._load()
            outcomes = [self._by_id[pid] for pid in reversed(self._order)]
        if instrument_key is not None:
            outcomes = [o for o in outcomes if o.instrument_key == instrument_key]
        if limit is not None:
            outcomes = outcomes[:limit]
        return tuple(outcomes)
