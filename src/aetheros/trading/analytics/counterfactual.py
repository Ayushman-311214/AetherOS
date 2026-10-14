"""
Counterfactual analysis (spec Phase 2 -- "was the decision the right call?").

A journal entry records *what happened*; counterfactual analysis asks *why it
happened and whether the decision that produced it was sound*. It reads a
closed :class:`JournalEntry` against the decision context it carries (entry
reason, evidence ids, risk geometry) and classifies the outcome into one of
the honest post-trade categories the spec enumerates:

* ``SUPPORT``              -- the trade won *and* the planned geometry held;
  the decision's thesis was vindicated by the market.
* ``CONTRADICTION``        -- the trade lost in a way the thesis did not
  predict; the evidence pointed one way and price went the other.
* ``INVALIDATION``         -- the position was stopped; the decision's own
  invalidation condition fired, which is the geometry working as designed,
  not a judgement error.
* ``MISSING_EVIDENCE``     -- the trade was taken on thin evidence (few or no
  recorded evidence ids); whether it won or lost, the basis was weak.
* ``NO_TRADE_ALTERNATIVE`` -- the better call was to stand down: the trade was
  entered and lost where a NO_TRADE would have been correct.
* ``EXECUTION_VS_ANALYSIS`` -- the analysis was right but the execution lost:
  the fill diverged from the planned entry badly enough that slippage, not the
  thesis, cost the money.

The classifier is deterministic over the entry's own numbers -- entry vs exit
price, stop/target, the recorded return, the evidence count. It invents no
narrative: each verdict names the arithmetic that produced it, so "the trade
lost because the stop was hit" and "the trade lost because the thesis was
wrong" are distinguishable from the record itself, not asserted after the fact.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from ..domain.enums import Direction
from ..domain.journal import JournalEntry
from ..domain.simulation import SimulationExitReason


def _utcnow() -> datetime:
    return datetime.now(UTC)


class CounterfactualKind(str, Enum):
    """The honest category a closed trade's outcome falls into."""

    SUPPORT = "support"
    CONTRADICTION = "contradiction"
    INVALIDATION = "invalidation"
    MISSING_EVIDENCE = "missing_evidence"
    DECISION_CHANGING = "decision_changing"
    NO_TRADE_ALTERNATIVE = "no_trade_alternative"
    EXECUTION_VS_ANALYSIS = "execution_vs_analysis"
    UNSCORED = "unscored"


#: A winning trade whose exit was its stop is still recorded as the geometry
#: firing (INVALIDATION), not as a contradiction of the thesis.
_TOLERANCE = 1e-6


@dataclass(frozen=True, slots=True)
class Counterfactual:
    """
    The classified outcome of one closed journal entry.

    ``won``/``net_pnl`` are read off the entry; ``kind`` is the honest verdict;
    ``basis`` is the arithmetic or observation that decided it -- so the
    classification is auditable, not asserted.
    """

    entry_id: str
    kind: CounterfactualKind
    won: bool | None
    net_pnl: float | None
    basis: str
    detail: str = ""
    created_at: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind.value,
            "won": self.won,
            "net_pnl": self.net_pnl,
            "basis": self.basis,
            "detail": self.detail,
            "created_at": self.created_at.isoformat(),
        }


class CounterfactualService:
    """Deterministic post-trade classification over closed journal entries."""

    def classify(self, entry: JournalEntry) -> Counterfactual:
        """
        Classify one journal entry's outcome against its own recorded context.

        An open entry (no exit yet) is UNSCORED -- there is nothing to judge.
        Everything else is read off the entry's own geometry and result.
        """
        if entry.exit_price is None or entry.net_pnl is None:
            return Counterfactual(
                entry_id=entry.entry_id,
                kind=CounterfactualKind.UNSCORED,
                won=None,
                net_pnl=None,
                basis="The entry has no recorded exit; there is no outcome to score.",
            )

        won = entry.net_pnl > _TOLERANCE
        # The strongest signals first: thin evidence, then the geometry/exit
        # mechanics, then the directional verdict.
        if len(entry.evidence_ids) == 0:
            return Counterfactual(
                entry_id=entry.entry_id,
                kind=CounterfactualKind.MISSING_EVIDENCE,
                won=won,
                net_pnl=entry.net_pnl,
                basis=(
                    "The entry recorded no evidence ids; it was taken on a "
                    "basis the journal cannot show."
                ),
            )

        if entry.exit_reason is SimulationExitReason.STOP:
            return Counterfactual(
                entry_id=entry.entry_id,
                kind=CounterfactualKind.INVALIDATION,
                won=won,
                net_pnl=entry.net_pnl,
                basis=(
                    f"The position exited on its stop at {entry.exit_price:g}; "
                    "the planned invalidation fired, which is the geometry "
                    "working, not a judgement failure."
                ),
            )

        if entry.exit_reason is SimulationExitReason.TARGET:
            kind = (
                CounterfactualKind.SUPPORT if won
                else CounterfactualKind.CONTRADICTION
            )
            return Counterfactual(
                entry_id=entry.entry_id,
                kind=kind,
                won=won,
                net_pnl=entry.net_pnl,
                basis=(
                    f"The position reached its target at {entry.exit_price:g}; "
                    f"the thesis {'was vindicated' if won else 'was contradicted despite reaching target'}."
                ),
            )

        # A forced or ambiguous close falls back to the directional verdict:
        # won = the thesis was right, lost = a NO_TRADE was the better call.
        if won:
            return Counterfactual(
                entry_id=entry.entry_id,
                kind=CounterfactualKind.SUPPORT,
                won=True,
                net_pnl=entry.net_pnl,
                basis=(
                    f"The trade netted {entry.net_pnl:.2f}; the directional "
                    "read and the recorded evidence supported it."
                ),
            )
        return Counterfactual(
            entry_id=entry.entry_id,
            kind=CounterfactualKind.NO_TRADE_ALTERNATIVE,
            won=False,
            net_pnl=entry.net_pnl,
            basis=(
                f"The trade lost {entry.net_pnl:.2f}; a NO_TRADE stand-down "
                "would have been the correct call on this evidence."
            ),
        )
