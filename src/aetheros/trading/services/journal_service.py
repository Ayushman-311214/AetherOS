"""
Trading-journal service (spec Phase 21).

Builds :class:`JournalEntry` records from a :class:`SimulationReport` -- one
entry per simulated round trip, in trade order. The service computes nothing
about the market: it reads the trades the simulation already settled, the
strategy and timeframe the report already names, and the provenance the run
already stamped, and arranges them into the traceable record the journal keeps.

Paper trades therefore create complete journal entries automatically wherever
the caller asks for them (the ``simulate_strategy`` path gains a journal
section), without the simulation itself growing a second output.

Two entry paths exist on the record itself. This service covers the *exit*
side (settled replays via :meth:`JournalEntry.from_trade`); the *entry* side
(a validated execution request via :meth:`JournalEntry.from_request`, closed
later with :meth:`JournalEntry.close`) is built by the live paper-trade path,
which holds the §9 decision context the replay does not retain. Human
reflection (emotion, lesson) is attached with :meth:`JournalEntry.annotate`
-- the service never invents it.
"""

from __future__ import annotations

from ..domain.journal import JournalEntry
from ..domain.simulation import SimulationReport


class JournalService:
    """Builds journal entries from simulation reports. Pure, stateless."""

    def entries_for_report(self, report: SimulationReport) -> tuple[JournalEntry, ...]:
        """
        One entry per trade in the report, in the order the trades closed.

        The entry reason is left empty: the simulation replays geometry, not
        prose, and inventing a rationale here would fabricate the very evidence
        the journal exists to preserve.
        """
        return tuple(
            JournalEntry.from_trade(
                trade,
                strategy_id=report.strategy_id,
                timeframe=report.timeframe,
                provenance=report.provenance,
                is_mock=report.provenance.is_mock,
            )
            for trade in report.trades
        )
