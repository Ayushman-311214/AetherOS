"""
Broker value objects (spec Phase 9).

An :class:`ExecutionRequest` is the full §9-required record for an executable
trade: instrument, side, quantity, entry, stop loss, take profit, risk, risk
/reward, strategy, evidence, reason. It is built *from* a
:class:`~aetheros.trading.domain.trade.TradeSignal` plus its
:class:`~aetheros.trading.domain.risk.RiskAssessment` -- the signal layer
already refused to carry a quantity, so this is the first object in the
pipeline that has one, and it cannot be constructed without every field the
spec requires. Nothing downstream may submit anything less.

:class:`ExecutionResult` records what a broker actually did with a request.
Its ``status`` reuses :class:`OrderStatus`, and a rejected result carries the
broker's reason verbatim -- a broker never silently drops an order.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .enums import Direction, OrderStatus, OrderType, RiskBand
from .evidence import Evidence
from .instrument import Instrument
from .risk import RiskAssessment
from .strategy import StrategySetup
from .trade import TradeSignal


def _utcnow() -> datetime:
    return datetime.now(UTC)


_REQUEST_COUNTER = 0


def _request_id() -> str:
    """Sequential, monotonic ids: audit trails order correctly."""
    global _REQUEST_COUNTER
    _REQUEST_COUNTER += 1
    stamp = _utcnow().timestamp()
    return f"req_{stamp:.0f}_{_REQUEST_COUNTER:06d}"


def _idempotency_key(
    *,
    signal_id: str,
    instrument_key: str,
    direction: Direction,
    quantity: float,
) -> str:
    """
    The stable client-order id for one request (spec Phase 2 idempotency).

    Content-addressed over the signal it descends from plus the side and size,
    so re-submitting the *same* logical order -- a retried transport fault, a
    re-issued decision -- resolves to the same key and dedupes at the venue,
    while a genuinely different order never collides. The wall clock is
    excluded for the same reason the signal id excludes it: identity is what
    the request *is*, not when it was typed.
    """
    payload = "|".join(
        (signal_id, instrument_key, direction.value, f"{quantity:.8f}")
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"coid_{digest[:16]}"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    """
    A fully-specified executable trade request, built from a judged signal.

    Every field the financial-safety contract (§9) demands on an executable
    trade is present and validated here: side, quantity, entry, stop loss,
    take profit, risk, risk/reward, strategy, evidence and reason. A request
    is the *only* input a broker accepts, so nothing under-specified can
    reach an execution path.

    The order type is part of the record too. A MARKET request fills on
    arrival; a LIMIT/STOP/STOP_LIMIT request rests at the venue until its
    trigger is met, so it must carry the price(s) that define that trigger --
    a resting order without its trigger price is under-specified in exactly
    the way this model exists to prevent.
    """

    instrument: Instrument
    direction: Direction
    quantity: float
    entry: float
    stop_loss: float
    take_profit: float
    risk: RiskBand
    risk_reward_ratio: float | None
    risk_pct: float | None
    strategy_id: str
    reasoning: str
    evidence: tuple[Evidence, ...]
    signal_id: str
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    stop_price: float | None = None
    request_id: str = field(default_factory=_request_id)
    idempotency_key: str = ""
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if self.direction not in (Direction.UP, Direction.DOWN):
            raise ValueError("An execution request must be directional.")
        if not math.isfinite(self.quantity) or self.quantity <= 0:
            raise ValueError("A quantity must be a finite positive number.")
        for label, value in (
            ("entry", self.entry),
            ("stop_loss", self.stop_loss),
            ("take_profit", self.take_profit),
        ):
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"A request's {label} must be positive.")
        if self.direction is Direction.UP and self.stop_loss >= self.entry:
            raise ValueError("A long request's stop must sit below its entry.")
        if self.direction is Direction.DOWN and self.stop_loss <= self.entry:
            raise ValueError("A short request's stop must sit above its entry.")
        if self.direction is Direction.UP and self.take_profit <= self.entry:
            raise ValueError("A long request's target must sit above its entry.")
        if self.direction is Direction.DOWN and self.take_profit >= self.entry:
            raise ValueError("A short request's target must sit below its entry.")
        if not self.strategy_id.strip():
            raise ValueError("A request must name its strategy.")
        if not self.reasoning.strip():
            raise ValueError("A request must carry the signal's reasoning.")
        if not self.signal_id.strip():
            raise ValueError("A request must carry the signal's id.")
        if self.risk_reward_ratio is not None and not math.isfinite(
            self.risk_reward_ratio
        ):
            raise ValueError("A risk/reward ratio must be finite when present.")
        if not self.idempotency_key.strip():
            # A request that did not name a key derives a stable one, so the
            # venue can always dedupe on it; the wall clock is never an input.
            object.__setattr__(
                self,
                "idempotency_key",
                _idempotency_key(
                    signal_id=self.signal_id,
                    instrument_key=self.instrument.key,
                    direction=self.direction,
                    quantity=self.quantity,
                ),
            )
        self._validate_order_type()

    def _validate_order_type(self) -> None:
        """
        The trigger prices an order type requires -- present exactly when due.

        A resting order without its trigger price cannot be executed honestly
        and a market order *with* one states a condition the venue will never
        consult, so both are refused rather than silently ignored.
        """
        for label, value in (
            ("limit_price", self.limit_price),
            ("stop_price", self.stop_price),
        ):
            if value is not None and (not math.isfinite(value) or value <= 0):
                raise ValueError(f"An order's {label} must be positive.")
        needs_limit = self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT)
        needs_stop = self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT)
        if needs_limit and self.limit_price is None:
            raise ValueError(f"A {self.order_type.value} request requires a limit price.")
        if needs_stop and self.stop_price is None:
            raise ValueError(f"A {self.order_type.value} request requires a stop price.")
        if self.order_type is OrderType.MARKET and (
            self.limit_price is not None or self.stop_price is not None
        ):
            raise ValueError("A market request cannot carry a limit or stop price.")

    @property
    def is_resting(self) -> bool:
        """Whether this request must rest at the venue until its trigger is met."""
        return self.order_type is not OrderType.MARKET

    @property
    def client_order_id(self) -> str:
        """The caller-side order id the venue should index for dedupe."""
        return self.idempotency_key

    @classmethod
    def from_signal(
        cls,
        signal: TradeSignal,
        risk: RiskAssessment,
        setup: StrategySetup,
        *,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> ExecutionRequest:
        """
        Build the executable request from a fired signal and its geometry.

        ``quantity`` comes from the caller (the risk engine's position size or
        an explicit override) -- the signal layer deliberately never carried
        one, and this is the single point where a size becomes part of the
        trade record. The order type defaults to MARKET; a resting type is
        chosen explicitly and must bring its trigger price(s) with it.
        """
        if signal.strategy_id != setup.strategy_id:
            raise ValueError("The signal and the setup must come from one strategy.")
        if signal.direction is not setup.direction:
            raise ValueError("The signal and the setup must share a side.")
        if risk.direction is not signal.direction:
            raise ValueError("The risk assessment must share the signal's side.")
        if signal.entry is None or signal.stop_loss is None:
            raise ValueError(
                "A fired signal must carry entry and stop geometry to be executed."
            )
        if signal.take_profit is None:
            raise ValueError(
                "A fired signal must carry a target to be executed."
            )
        return cls(
            instrument=signal.instrument,
            direction=signal.direction,
            quantity=quantity,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk=signal.risk,
            risk_reward_ratio=risk.risk_reward_ratio,
            risk_pct=risk.risk_pct,
            strategy_id=signal.strategy_id,
            reasoning=signal.reasoning,
            evidence=signal.evidence,
            signal_id=signal.signal_id,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "idempotency_key": self.idempotency_key,
            "signal_id": self.signal_id,
            "instrument": self.instrument.to_dict(),
            "direction": self.direction.value,
            "quantity": self.quantity,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk": self.risk.value,
            "risk_reward_ratio": self.risk_reward_ratio,
            "risk_pct": self.risk_pct,
            "strategy_id": self.strategy_id,
            "reasoning": self.reasoning,
            "evidence": [item.to_dict() for item in self.evidence],
            "order_type": self.order_type.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """What a broker did with one request."""

    request_id: str
    status: OrderStatus
    reason: str
    order_id: str | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    created_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("An execution result needs its request id.")
        if not self.reason.strip():
            raise ValueError("An execution result needs its reason.")
        if not math.isfinite(self.filled_quantity) or self.filled_quantity < 0:
            raise ValueError("filled_quantity must be non-negative and finite.")

    @property
    def filled(self) -> bool:
        return self.status is OrderStatus.FILLED

    @property
    def rejected(self) -> bool:
        return self.status is OrderStatus.REJECTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "reason": self.reason,
            "order_id": self.order_id,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "created_at": self.created_at.isoformat(),
        }
