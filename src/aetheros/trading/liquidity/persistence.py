"""
Persistence ports for the liquidity layer (Phase 2).

Mirrors the established AetherOS store pattern (``PredictionStore`` /
``OutcomeStore``): a narrow abstract port plus an in-memory reference impl and a
durable JSON-Lines impl behind the identical interface. No second database
architecture -- these reuse the same append-and-read, content-addressed,
never-fabricate contract the rest of the trading persistence uses, just under
the liquidity/ namespace.

The conceptual layout the spec asks for maps onto file paths the caller picks:

    market_data/   candles, trades, order_book_snapshots  (providers hold these;
                                                         this layer persists the
                                                         *derived* artifacts)
    liquidity/     observations, zones, events            (the three stores here)

A store keeps a record verbatim -- it never re-judges, upgrades or fabricates
one. Re-recording the same id is idempotent.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from pathlib import Path

from ...core.logging import get_logger
from .observation import LiquidityObservation
from .zone import LiquidityZone

logger = get_logger("trading.liquidity.store")


class ObservationStore(ABC):
    """Append-and-read port for :class:`LiquidityObservation` records."""

    @abstractmethod
    async def record(self, observation: LiquidityObservation) -> str:
        """Persist one observation; returns a stable key for it."""

    @abstractmethod
    async def list_observations(
        self, *, symbol: str | None = None, limit: int | None = None
    ) -> tuple[LiquidityObservation, ...]:
        """Return observations newest-first, optionally filtered/capped."""


class ZoneStore(ABC):
    """Upsert-and-read port for :class:`LiquidityZone` lifecycle records."""

    @abstractmethod
    async def record(self, zone: LiquidityZone) -> str:
        """Persist a zone (upsert on its content-addressed ``id``)."""

    @abstractmethod
    async def get(self, zone_id: str) -> LiquidityZone | None:
        """Return the latest recorded state of a zone, or ``None``."""

    @abstractmethod
    async def list_zones(
        self, *, symbol: str | None = None, limit: int | None = None
    ) -> tuple[LiquidityZone, ...]:
        """Return recorded zones newest-first, optionally filtered/capped."""


class _JsonLinesStore:
    """
    Shared append-per-write / read-back machinery for the file impls.

    Each record is one newline-terminated JSON line. On load the file is read
    front-to-back so, where upsert semantics apply (zones), the *last* line for
    an id wins -- exactly the maturing-lifecycle semantics a zone needs. A
    malformed or partially-written trailing line is skipped with a warning,
    never parsed into a fabricated record.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = asyncio.Lock()
        self._loaded = False

    def _read_lines(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(f"Could not read the store at '{self._path}'.") from exc
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except (ValueError, TypeError):
                logger.warning("Skipping a malformed liquidity-store line.")
        return rows

    def _append(self, payload: dict) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except OSError as exc:
            raise RuntimeError(f"Could not append to '{self._path}'.") from exc


class InMemoryObservationStore(ObservationStore):
    """Process-local, deterministic, non-durable reference impl."""

    def __init__(self) -> None:
        self._rows: list[LiquidityObservation] = []
        self._lock = asyncio.Lock()

    async def record(self, observation: LiquidityObservation) -> str:
        async with self._lock:
            self._rows.append(observation)
        return f"{observation.symbol}:{observation.timestamp.isoformat()}"

    async def list_observations(
        self, *, symbol: str | None = None, limit: int | None = None
    ) -> tuple[LiquidityObservation, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        rows = list(reversed(self._rows))
        if symbol is not None:
            rows = [r for r in rows if r.symbol == symbol]
        if limit is not None:
            rows = rows[:limit]
        return tuple(rows)

    def __len__(self) -> int:
        return len(self._rows)


class InMemoryZoneStore(ZoneStore):
    """Process-local, deterministic, non-durable reference impl."""

    def __init__(self) -> None:
        self._by_id: dict[str, LiquidityZone] = {}
        self._order: list[str] = []
        self._lock = asyncio.Lock()

    async def record(self, zone: LiquidityZone) -> str:
        async with self._lock:
            if zone.id not in self._by_id:
                self._order.append(zone.id)
            self._by_id[zone.id] = zone
        return zone.id

    async def get(self, zone_id: str) -> LiquidityZone | None:
        return self._by_id.get(zone_id)

    async def list_zones(
        self, *, symbol: str | None = None, limit: int | None = None
    ) -> tuple[LiquidityZone, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        zones = [self._by_id[zid] for zid in reversed(self._order)]
        if symbol is not None:
            zones = [z for z in zones if z.symbol == symbol]
        if limit is not None:
            zones = zones[:limit]
        return tuple(zones)

    def __len__(self) -> int:
        return len(self._by_id)


class FileObservationStore(_JsonLinesStore, ObservationStore):
    """Durable JSON-Lines observation store (append-only audit trail)."""

    def __init__(self, path: str | Path) -> None:
        _JsonLinesStore.__init__(self, path)

    async def record(self, observation: LiquidityObservation) -> str:
        async with self._lock:
            self._append(observation.to_dict())
        return f"{observation.symbol}:{observation.timestamp.isoformat()}"

    async def list_observations(
        self, *, symbol: str | None = None, limit: int | None = None
    ) -> tuple[LiquidityObservation, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        async with self._lock:
            rows = [LiquidityObservation.from_dict(r) for r in self._read_lines()]
        rows = list(reversed(rows))
        if symbol is not None:
            rows = [r for r in rows if r.symbol == symbol]
        if limit is not None:
            rows = rows[:limit]
        return tuple(rows)


class FileZoneStore(_JsonLinesStore, ZoneStore):
    """
    Durable JSON-Lines zone store (append-per-write, last-line-wins on load).

    A zone is appended each time the tracker updates it; on read the latest
    line for its ``id`` wins, so a zone's maturing lifecycle (active -> touched
    -> swept/invalidated) is reflected without rewriting the file.
    """

    def __init__(self, path: str | Path) -> None:
        _JsonLinesStore.__init__(self, path)

    def _load(self) -> dict[str, LiquidityZone]:
        by_id: dict[str, LiquidityZone] = {}
        order: list[str] = []
        for row in self._read_lines():
            try:
                zone = LiquidityZone.from_dict(row)
            except (ValueError, KeyError, TypeError):
                continue
            if zone.id not in by_id:
                order.append(zone.id)
            by_id[zone.id] = zone  # last line wins
        self._order = order
        return by_id

    async def record(self, zone: LiquidityZone) -> str:
        async with self._lock:
            self._append(zone.to_dict())
        return zone.id

    async def get(self, zone_id: str) -> LiquidityZone | None:
        async with self._lock:
            return self._load().get(zone_id)

    async def list_zones(
        self, *, symbol: str | None = None, limit: int | None = None
    ) -> tuple[LiquidityZone, ...]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be non-negative")
        async with self._lock:
            by_id = self._load()
            zones = [by_id[zid] for zid in reversed(self._order)]
        if symbol is not None:
            zones = [z for z in zones if z.symbol == symbol]
        if limit is not None:
            zones = zones[:limit]
        return tuple(zones)
