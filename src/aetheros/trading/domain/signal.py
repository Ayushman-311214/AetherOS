"""
Signal-layer value objects (spec Phase 8).

The signal layer converts a strategy's reading plus the risk engine's geometry
into a *proposed action*. Two boundaries are drawn deliberately, and the models
enforce them:

**A signal is a proposal, never an order.** :class:`TradeSignal` already exists
in ``domain/trade.py`` as the output contract -- the spec's "every signal
contains confidence, risk, reasoning, supporting evidence" maps exactly onto
its fields. What is new here is the *reason a signal was or was not produced*:
the honest answer for most contexts is "no signal", and section 28 requires
that answer be carried as data rather than an exception.

**Nothing here can reach a broker.** There is no order construction, no
quantity, no submission. The §9 path (strategy → decision → policy → risk →
execution validation → broker) is enforced by construction: a
:class:`SignalCandidate` holds a proposal and the gate verdicts it accumulated;
turning one into an execution is the execution engine's phase, and it happens
nowhere in this module.

A candidate is directional or it is an explicit no-signal. As with setups,
there is no SIDEWAYS candidate -- a market with no edge produces no proposal,
and the reason is recorded.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .critique import CriticReport
from .enums import (
    Direction,
    RiskBand,
    StrategyCategory,
)
from .instrument import Instrument
from .provenance import DataQuality, Provenance
from .risk import RiskAssessment
from .strategy import StrategySetup
from .trade import TradeSignal


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _stable_signal_id(
    *,
    instrument_key: str,
    strategy_id: str,
    timeframe: str,
    action: str,
    direction: str,
    entry: float,
    stop_loss: float | None,
) -> str:
    """
    Content-addressed id, mirroring the setup id it derives from.

    The wall clock is deliberately excluded; the strategy, the action, the
    side and the geometry are included, because re-deriving the same proposal
    from the same reading must be recognisable as the same proposal -- that is
    what makes an emitted ``SignalGenerated`` event de-duplicable and an audit
    trail trustworthy.
    """
    payload = "|".join(
        (
            instrument_key,
            strategy_id,
            timeframe,
            action,
            direction,
            f"{entry:.8f}",
            f"{stop_loss:.8f}" if stop_loss is not None else "none",
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"sg_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class SignalCandidate:
    """
    A proposed :class:`TradeSignal` with the verdict trail that produced it.

    ``signal`` is None when the pipeline declined to propose -- every gate the
    candidate failed is named in ``rejections`` so "why is there no signal?" is
    as answerable as "why is there one?". The risk assessment is always
    attached when a directional read existed, because §9 requires risk
    approval *before* any executable trade, and a candidate without its risk
    geometry could not be judged by the policy layer that consumes it.

    ``setup`` carries the strategy reading the candidate was built from, and
    is kept because §9's record for an executable trade names the *strategy*
    beside the geometry: :meth:`ExecutionRequest.from_signal` needs both. A
    candidate that discarded its own reading could not become a request
    without re-evaluating the strategy -- a silent second opinion, and exactly
    what this layer exists to prevent. It is optional so a hand-built
    candidate (tests, replayed verdicts) need not fabricate one.
    """

    strategy_id: str
    strategy_name: str
    category: StrategyCategory
    timeframe: str
    direction: Direction  # UP or DOWN only; the no-signal case is signal=None
    signal: TradeSignal | None
    risk: RiskAssessment
    critique: CriticReport
    setup: StrategySetup | None = None
    rejections: tuple[str, ...] = ()
    provenance: Provenance | None = None
    quality: DataQuality | None = None
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)
    candidate_id: str = ""

    def __post_init__(self) -> None:
        if not self.strategy_id.strip() or not self.strategy_name.strip():
            raise ValueError("A candidate requires a strategy id and name.")
        if not self.timeframe.strip():
            raise ValueError("A candidate requires a timeframe.")
        if self.direction not in (Direction.UP, Direction.DOWN):
            raise ValueError(
                "A candidate must be directional; a no-edge market produces "
                "no candidate at all, not a SIDEWAYS one."
            )
        if self.signal is not None:
            if self.signal.direction is not self.direction:
                raise ValueError("A candidate's signal must share its side.")
            if self.signal.strategy_id != self.strategy_id:
                raise ValueError(
                    "A candidate's signal must come from that strategy."
                )
        if self.risk.direction is not self.direction:
            raise ValueError("A candidate's risk assessment must share its side.")
        if not self.candidate_id:
            object.__setattr__(
                self,
                "candidate_id",
                _stable_signal_id(
                    instrument_key=self.risk.instrument.key,
                    strategy_id=self.strategy_id,
                    timeframe=self.timeframe,
                    action=self.signal.action.value if self.signal else "none",
                    direction=self.direction.value,
                    entry=self.risk.entry,
                    stop_loss=self.risk.stop_loss,
                ),
            )

    @property
    def instrument(self) -> Instrument:
        return self.risk.instrument

    @property
    def fired(self) -> bool:
        """Whether this candidate became a signal."""
        return self.signal is not None

    @property
    def risk_band(self) -> RiskBand:
        """The overall risk band of the risk assessment behind the proposal."""
        return self.risk.overall_risk

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "category": self.category.value,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "fired": self.fired,
            "signal": self.signal.to_dict() if self.signal else None,
            "risk": self.risk.to_dict(),
            "critique": self.critique.to_dict(),
            "setup": self.setup.to_dict() if self.setup else None,
            "rejections": list(self.rejections),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class SignalEvaluation:
    """
    What the signal engine concluded for one instrument, across one panel run.

    ``candidates`` holds every strategy's candidate, fired or not, in panel
    order; ``signals`` is the fired subset's trade signals in the same order.
    When not a single candidate fired, that fact is the result -- an empty
    evaluation is the §28 "no trade / insufficient evidence" answer, not a
    failure, and ``limitations`` says so explicitly.
    """

    instrument_key: str
    timeframe: str
    candidates: tuple[SignalCandidate, ...] = ()
    signals: tuple[TradeSignal, ...] = ()
    provenance: Provenance | None = None
    quality: DataQuality | None = None
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.instrument_key.strip() or not self.timeframe.strip():
            raise ValueError("An evaluation requires an instrument and timeframe.")
        for candidate in self.candidates:
            if candidate.risk.instrument.key != self.instrument_key:
                raise ValueError(
                    "An evaluation's candidates must describe its instrument."
                )
        if len(self.signals) != sum(1 for c in self.candidates if c.fired):
            raise ValueError(
                "An evaluation's signals must be exactly its fired candidates'."
            )

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def fired_strategies(self) -> tuple[str, ...]:
        return tuple(
            candidate.strategy_id for candidate in self.candidates if candidate.fired
        )

    @property
    def consensus(self) -> Direction:
        """
        The side the *fired* signals agree on, or UNKNOWN.

        Mixed sides are reported as UNKNOWN rather than majority-voted: an
        evaluation exists to surface disagreement, not to average it away --
        the same principle :class:`StrategyComparison` applies one layer down.
        """
        sides = {signal.direction for signal in self.signals}
        if len(sides) == 1 and Direction.UP in sides:
            return Direction.UP
        if len(sides) == 1 and Direction.DOWN in sides:
            return Direction.DOWN
        return Direction.UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "candidates": [c.to_dict() for c in self.candidates],
            "signals": [s.to_dict() for s in self.signals],
            "signal_count": self.signal_count,
            "fired_strategies": list(self.fired_strategies),
            "consensus": self.consensus.value,
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
