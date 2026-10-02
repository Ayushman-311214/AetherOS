"""
Instrument identity.

A tradable thing AetherOS can analyse. Symbol normalisation lives here so every
downstream cache key, log line and provenance record refers to the instrument
the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Instrument:
    """A tradable instrument (equity, crypto pair, index, ...)."""

    symbol: str
    exchange: str | None = None
    asset_class: str = "equity"
    name: str | None = None

    def __post_init__(self) -> None:
        # Frozen dataclass: assign through object.__setattr__.
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if self.exchange:
            object.__setattr__(self, "exchange", self.exchange.strip().upper())

    @property
    def key(self) -> str:
        """Stable identifier used in cache keys and persistence."""
        return f"{self.exchange}:{self.symbol}" if self.exchange else self.symbol

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "asset_class": self.asset_class,
            "name": self.name,
        }

    @classmethod
    def parse(cls, value: str, *, asset_class: str = "equity") -> "Instrument":
        """
        Parse ``EXCHANGE:SYMBOL`` or a bare ``SYMBOL``.

        Raises ValueError for an empty symbol rather than constructing a
        nameless instrument that would poison every downstream cache key.
        """
        raw = value.strip()
        if not raw:
            raise ValueError("Instrument symbol must not be empty.")
        if ":" in raw:
            exchange, _, symbol = raw.partition(":")
            if not symbol.strip():
                raise ValueError(f"Instrument '{value}' has no symbol after ':'.")
            return cls(symbol=symbol, exchange=exchange, asset_class=asset_class)
        return cls(symbol=raw, asset_class=asset_class)
