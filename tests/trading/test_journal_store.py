"""
JournalStore: durable + in-memory persistence for trading-journal entries (Phase 27).

These pin the durability + honesty contract of the journal store (CLAUDE.md
sections 15, 23, 28) without a network or the orchestrator:

* entries written by one store instance are read back by a fresh instance over
  the same file (persistence across "restarts"),
* recording upserts on the content-addressed ``entry_id`` -- an entry maturing
  from open (``from_request``) to closed (``close``) overwrites in place rather
  than leaving two rows for one trade,
* reads are newest-first with instrument/limit filters,
* a malformed trailing line is skipped on load rather than fabricated into an
  entry,
* a round trip through ``to_dict`` / ``from_dict`` preserves every field,
  including enum types and provenance.

The in-memory and file impls share one port, so both are exercised against the
same behavioural expectations where they must agree.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.trading.domain.enums import Direction, SourceTier
from aetheros.trading.domain.journal import JournalEntry
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.domain.simulation import SimulationExitReason
from aetheros.trading.errors import PredictionError
from aetheros.trading.services.journal_store import (
    FileJournalStore,
    InMemoryJournalStore,
    JournalStore,
)


def _entry(
    entry_id: str,
    *,
    instrument_key: str = "AAPL",
    closed: bool = True,
) -> JournalEntry:
    """Build a minimal, valid JournalEntry with a chosen id."""
    return JournalEntry(
        entry_id=entry_id,
        instrument_key=instrument_key,
        strategy_id="trend_following",
        direction=Direction.UP,
        quantity=10.0,
        entry_price=100.0,
        entry_bar=10,
        exit_price=105.0 if closed else None,
        exit_bar=15 if closed else None,
        exit_reason=SimulationExitReason.TARGET if closed else None,
        realized_pnl=50.0 if closed else None,
        commission_paid=1.0 if closed else 0.0,
        net_pnl=49.0 if closed else None,
        return_pct=4.9 if closed else None,
        entry_reason="momentum breakout",
        timeframe="1d",
        is_mock=False,
        provenance=Provenance(
            source="simulation",
            tier=SourceTier.DERIVED,
            retrieved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            detail="replay",
        ),
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        evidence_ids=("ev_1", "ev_2"),
        recorded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# ----------------------------------------------------------------------
# round-trip: the record shape survives to_dict/from_dict without loss
# ----------------------------------------------------------------------


def test_journal_entry_round_trips_through_dict() -> None:
    original = _entry("jrnl_a")
    rebuilt = JournalEntry.from_dict(original.to_dict())
    assert rebuilt == original


def test_round_trip_preserves_an_open_entry() -> None:
    original = _entry("jrnl_open", closed=False)
    rebuilt = JournalEntry.from_dict(original.to_dict())
    assert rebuilt == original
    assert rebuilt.exit_price is None
    assert rebuilt.exit_reason is None
    assert rebuilt.net_pnl is None


def test_round_trip_preserves_provenance_and_enums() -> None:
    rebuilt = JournalEntry.from_dict(_entry("jrnl_p").to_dict())
    assert rebuilt.direction is Direction.UP
    assert rebuilt.exit_reason is SimulationExitReason.TARGET
    assert rebuilt.provenance is not None
    assert rebuilt.provenance.tier is SourceTier.DERIVED
    assert rebuilt.provenance.source == "simulation"


# ----------------------------------------------------------------------
# in-memory store
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_records_and_reads_back() -> None:
    store: JournalStore = InMemoryJournalStore()
    await store.record(_entry("jrnl_1"))
    got = await store.get("jrnl_1")
    assert got is not None
    assert got.entry_id == "jrnl_1"


@pytest.mark.asyncio
async def test_in_memory_upsert_overwrites_in_place() -> None:
    store = InMemoryJournalStore()
    await store.record(_entry("jrnl_m", closed=False))  # open
    await store.record(_entry("jrnl_m", closed=True))  # same id, now closed

    assert len(store) == 1
    got = await store.get("jrnl_m")
    assert got is not None
    assert got.exit_price == 105.0  # the matured record won


@pytest.mark.asyncio
async def test_in_memory_missing_lookup_is_honest_none() -> None:
    store = InMemoryJournalStore()
    assert await store.get("nope") is None
    assert await store.list_entries() == ()


# ----------------------------------------------------------------------
# file store: durability + honesty
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_entries_survive_a_fresh_store_instance(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    store_a = FileJournalStore(path)
    await store_a.record(_entry("jrnl_a"))

    # A brand-new instance over the same file sees the persisted entry -- the
    # durability the in-memory store lacks.
    store_b = FileJournalStore(path)
    got = await store_b.get("jrnl_a")
    assert got is not None
    assert got.entry_id == "jrnl_a"
    assert got == _entry("jrnl_a")  # full fidelity across the restart


@pytest.mark.asyncio
async def test_file_upsert_last_line_wins_on_reload(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    store = FileJournalStore(path)
    await store.record(_entry("jrnl_m", closed=False))  # open
    await store.record(_entry("jrnl_m", closed=True))  # close under same id

    # One logical entry, even though two lines were appended.
    assert len(await store.list_entries()) == 1
    got = await store.get("jrnl_m")
    assert got is not None
    assert got.exit_price == 105.0

    # A fresh instance reloads front-to-back and the last (closed) line wins.
    reloaded = FileJournalStore(path)
    got2 = await reloaded.get("jrnl_m")
    assert got2 is not None
    assert got2.exit_price == 105.0


@pytest.mark.asyncio
async def test_file_lists_newest_first_with_filter_and_limit(tmp_path) -> None:
    store = FileJournalStore(tmp_path / "j.jsonl")
    await store.record(_entry("jrnl_1", instrument_key="AAPL"))
    await store.record(_entry("jrnl_2", instrument_key="MSFT"))
    await store.record(_entry("jrnl_3", instrument_key="AAPL"))

    newest = await store.list_entries()
    assert [e.entry_id for e in newest] == ["jrnl_3", "jrnl_2", "jrnl_1"]

    only_aapl = await store.list_entries(instrument_key="AAPL")
    assert [e.entry_id for e in only_aapl] == ["jrnl_3", "jrnl_1"]

    capped = await store.list_entries(limit=1)
    assert [e.entry_id for e in capped] == ["jrnl_3"]

    with pytest.raises(ValueError):
        await store.list_entries(limit=-1)


@pytest.mark.asyncio
async def test_malformed_trailing_line_is_skipped_not_fabricated(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    store = FileJournalStore(path)
    await store.record(_entry("jrnl_good"))
    # Simulate a crash mid-append: a trailing partial line.
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"entry_id": "jrnl_bad", "instr')  # truncated JSON

    reloaded = FileJournalStore(path)
    entries = await reloaded.list_entries()
    assert [e.entry_id for e in entries] == ["jrnl_good"]
    assert await reloaded.get("jrnl_bad") is None


@pytest.mark.asyncio
async def test_unreadable_file_raises_prediction_error(tmp_path) -> None:
    path = tmp_path / "a_directory_not_a_file.jsonl"
    path.mkdir()  # a directory can't be read as the store file
    store = FileJournalStore(path)
    with pytest.raises(PredictionError):
        await store.list_entries()


@pytest.mark.asyncio
async def test_file_idempotent_within_one_instance(tmp_path) -> None:
    path = tmp_path / "journal.jsonl"
    store = FileJournalStore(path)
    await store.record(_entry("jrnl_x"))
    await store.record(_entry("jrnl_x"))  # same, unchanged entry again

    # Append-only: two identical writes leave two lines, but the index dedupes
    # to one logical entry and a reload still sees exactly one.
    assert len(await store.list_entries()) == 1
    reloaded = FileJournalStore(path)
    assert len(await reloaded.list_entries()) == 1
