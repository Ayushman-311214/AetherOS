"""Typed, immutable trading lifecycle and policy value objects."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .enums import (
    Confidence,
    Direction,
    OrderStatus,
    OrderType,
    PositionStatus,
    RiskBand,
    StrategyCategory,
    TradeAction,
)
from .evidence import Evidence
from .instrument import Instrument


def _positive(value: float, field_name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field_name} must be a finite positive number.")


def _optional_positive(value: float | None, field_name: str) -> None:
    if value is not None:
        _positive(value, field_name)


def _aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware.")


@dataclass(frozen=True, slots=True)
class TradeSignal:
    """Evidence-backed proposed trading action; never an execution instruction."""

    instrument: Instrument
    action: TradeAction
    direction: Direction
    confidence: Confidence
    risk: RiskBand
    reasoning: str
    evidence: tuple[Evidence, ...]
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    strategy_id: str | None = None
    signal_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.instrument.key.strip() or not self.signal_id.strip():
            raise ValueError("TradeSignal requires instrument and signal identifiers.")
        if not self.reasoning.strip():
            raise ValueError("TradeSignal reasoning must not be empty.")
        _aware(self.created_at, "created_at")
        _optional_positive(self.entry, "entry")
        _optional_positive(self.stop_loss, "stop_loss")
        _optional_positive(self.take_profit, "take_profit")
        if self.action in (TradeAction.BUY, TradeAction.SELL):
            if self.direction not in (Direction.UP, Direction.DOWN):
                raise ValueError("Entry signals require an UP or DOWN direction.")
            if self.entry is None:
                raise ValueError("Entry signals require an entry price.")
        if self.action is TradeAction.BUY and self.stop_loss is not None:
            if self.stop_loss >= self.entry:
                raise ValueError("A BUY stop_loss must be below entry.")
        if self.action is TradeAction.SELL and self.stop_loss is not None:
            if self.stop_loss <= self.entry:
                raise ValueError("A SELL stop_loss must be above entry.")
        if self.action is TradeAction.BUY and self.take_profit is not None:
            if self.take_profit <= self.entry:
                raise ValueError("A BUY take_profit must be above entry.")
        if self.action is TradeAction.SELL and self.take_profit is not None:
            if self.take_profit >= self.entry:
                raise ValueError("A SELL take_profit must be below entry.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "instrument": self.instrument.to_dict(),
            "action": self.action.value,
            "direction": self.direction.value,
            "confidence": self.confidence.value,
            "risk": self.risk.value,
            "reasoning": self.reasoning,
            "evidence": [item.to_dict() for item in self.evidence],
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "strategy_id": self.strategy_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Order:
    """Order value object with validated terms and lifecycle snapshot."""

    instrument: Instrument
    direction: Direction
    quantity: float
    order_type: OrderType
    status: OrderStatus = OrderStatus.PENDING
    order_id: str = field(default_factory=lambda: str(uuid4()))
    limit_price: float | None = None
    stop_price: float | None = None
    filled_quantity: float = 0.0
    average_fill_price: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.direction not in (Direction.UP, Direction.DOWN):
            raise ValueError("Order direction must be UP or DOWN.")
        if not self.order_id.strip():
            raise ValueError("Order ID must not be empty.")
        _positive(self.quantity, "quantity")
        for value, name in (
            (self.limit_price, "limit_price"),
            (self.stop_price, "stop_price"),
            (self.average_fill_price, "average_fill_price"),
        ):
            _optional_positive(value, name)
        if not math.isfinite(self.filled_quantity) or not 0 <= self.filled_quantity <= self.quantity:
            raise ValueError("filled_quantity must be between zero and quantity.")
        if self.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and self.limit_price is None:
            raise ValueError("Limit and stop-limit orders require limit_price.")
        if self.order_type in (OrderType.STOP, OrderType.STOP_LIMIT) and self.stop_price is None:
            raise ValueError("Stop and stop-limit orders require stop_price.")
        if self.status is OrderStatus.FILLED and self.filled_quantity != self.quantity:
            raise ValueError("A FILLED order must have filled its full quantity.")
        if self.status is OrderStatus.PARTIALLY_FILLED and not 0 < self.filled_quantity < self.quantity:
            raise ValueError("A PARTIALLY_FILLED order requires a partial fill quantity.")
        if self.filled_quantity > 0 and self.average_fill_price is None:
            raise ValueError("Filled quantity requires an average_fill_price.")
        _aware(self.created_at, "created_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "instrument": self.instrument.to_dict(),
            "direction": self.direction.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class Position:
    """A position snapshot; state transitions are performed by a manager later."""

    instrument: Instrument
    direction: Direction
    quantity: float
    entry_price: float
    status: PositionStatus = PositionStatus.OPEN
    position_id: str = field(default_factory=lambda: str(uuid4()))
    stop_loss: float | None = None
    take_profit: float | None = None
    exit_price: float | None = None
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.direction not in (Direction.UP, Direction.DOWN):
            raise ValueError("Position direction must be UP or DOWN.")
        if not self.position_id.strip():
            raise ValueError("Position ID must not be empty.")
        _positive(self.quantity, "quantity")
        _positive(self.entry_price, "entry_price")
        for value, name in ((self.stop_loss, "stop_loss"), (self.take_profit, "take_profit"), (self.exit_price, "exit_price")):
            _optional_positive(value, name)
        _aware(self.opened_at, "opened_at")
        if self.status is PositionStatus.OPEN and (self.exit_price is not None or self.closed_at is not None):
            raise ValueError("An OPEN position cannot have exit fields.")
        if self.status is PositionStatus.CLOSED:
            if self.exit_price is None or self.closed_at is None:
                raise ValueError("A CLOSED position requires exit_price and closed_at.")
            _aware(self.closed_at, "closed_at")
            if self.closed_at < self.opened_at:
                raise ValueError("closed_at cannot precede opened_at.")

    @property
    def realized_pnl(self) -> float | None:
        if self.status is not PositionStatus.CLOSED or self.exit_price is None:
            return None
        sign = 1.0 if self.direction is Direction.UP else -1.0
        return (self.exit_price - self.entry_price) * self.quantity * sign

    def to_dict(self) -> dict[str, Any]:
        return {
            "position_id": self.position_id,
            "instrument": self.instrument.to_dict(),
            "direction": self.direction.value,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "status": self.status.value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "exit_price": self.exit_price,
            "realized_pnl": self.realized_pnl,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        }


@dataclass(frozen=True, slots=True)
class Strategy:
    """Strategy metadata/configuration; evaluation logic lives outside the model."""

    strategy_id: str
    name: str
    category: StrategyCategory
    description: str
    enabled: bool = True
    parameters: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.strategy_id.strip() or not self.name.strip():
            raise ValueError("Strategy requires a non-empty ID and name.")
        if not self.description.strip():
            raise ValueError("Strategy description must not be empty.")
        keys = [key for key, _ in self.parameters]
        if any(not key.strip() for key in keys) or len(keys) != len(set(keys)):
            raise ValueError("Strategy parameter keys must be non-empty and unique.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "enabled": self.enabled,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True, slots=True)
class RiskProfile:
    """Configured risk limits expressed as percentages and minimum reward:risk."""

    max_risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_exposure_pct: float
    min_risk_reward: float
    profile_id: str = "default"

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("Risk profile ID must not be empty.")
        for value, name in (
            (self.max_risk_per_trade_pct, "max_risk_per_trade_pct"),
            (self.max_daily_loss_pct, "max_daily_loss_pct"),
            (self.max_exposure_pct, "max_exposure_pct"),
        ):
            if not math.isfinite(value) or not 0 < value <= 100:
                raise ValueError(f"{name} must be greater than 0 and at most 100.")
        if not math.isfinite(self.min_risk_reward) or self.min_risk_reward <= 0:
            raise ValueError("min_risk_reward must be a finite positive number.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "max_risk_per_trade_pct": self.max_risk_per_trade_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_exposure_pct": self.max_exposure_pct,
            "min_risk_reward": self.min_risk_reward,
        }


@dataclass(frozen=True, slots=True)
class Portfolio:
    """Account snapshot, separate from the existing portfolio-risk allocation plan."""

    portfolio_id: str
    currency: str
    cash_balance: float
    equity: float
    margin_used: float = 0.0
    positions: tuple[Position, ...] = ()
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.portfolio_id.strip() or not self.currency.strip():
            raise ValueError("Portfolio requires an ID and currency.")
        for value, name in (
            (self.cash_balance, "cash_balance"),
            (self.equity, "equity"),
            (self.margin_used, "margin_used"),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative.")
        if self.margin_used > self.equity:
            raise ValueError("margin_used cannot exceed equity.")
        _aware(self.updated_at, "updated_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "currency": self.currency,
            "cash_balance": self.cash_balance,
            "equity": self.equity,
            "margin_used": self.margin_used,
            "positions": [position.to_dict() for position in self.positions],
            "updated_at": self.updated_at.isoformat(),
        }
