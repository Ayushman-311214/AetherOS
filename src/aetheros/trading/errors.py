"""
Domain-specific trading errors.

These extend the project-wide :class:`BaseError` so trading failures carry the
same structured ``code`` / ``message`` / ``hint`` shape as the rest of AetherOS
and serialise identically for logs and tool results. Each subclass pins a
default code so a raise site can stay terse without losing the code.
"""

from __future__ import annotations

from typing import Any

from ..core.errors.base_error import BaseError, ErrorContext


def _as_context(context: ErrorContext | dict[str, Any] | None) -> ErrorContext | None:
    """Accept a plain dict for ergonomics and wrap it as ErrorContext details."""
    if context is None or isinstance(context, ErrorContext):
        return context
    return ErrorContext(module="trading", details=dict(context))


class TradingError(BaseError):
    """Base class for every Trading Intelligence error."""

    default_code = "TRADING_000"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        hint: str | None = None,
        context: ErrorContext | dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(
            code=code or self.default_code,
            message=message,
            hint=hint,
            context=_as_context(context),
            cause=cause,
        )


class MarketDataError(TradingError):
    """A market-data operation could not be completed."""

    default_code = "TRADING_MD_001"


class ProviderError(MarketDataError):
    """A data provider failed, timed out, or returned an unusable response."""

    default_code = "TRADING_MD_002"


class InsufficientDataError(MarketDataError):
    """Not enough history to compute the requested analysis honestly."""

    default_code = "TRADING_MD_003"


class InvalidSymbolError(MarketDataError):
    """The instrument symbol could not be resolved."""

    default_code = "TRADING_MD_004"


class IndicatorError(TradingError):
    """A technical indicator could not be computed."""

    default_code = "TRADING_TA_001"


class AnalysisError(TradingError):
    """The analysis pipeline failed to assemble a result."""

    default_code = "TRADING_AN_001"


class RiskError(TradingError):
    """A risk assessment could not be computed from the given inputs."""

    default_code = "TRADING_RK_001"


class BacktestError(TradingError):
    """A backtest could not be run over the supplied data or signal."""

    default_code = "TRADING_BT_001"


class CriticError(TradingError):
    """The critic could not evaluate the proposed signal."""

    default_code = "TRADING_CR_001"


class ProbabilityError(TradingError):
    """A calibrated probability estimate could not be produced honestly."""

    default_code = "TRADING_PB_001"


class PredictionError(TradingError):
    """An auditable prediction record could not be built, stored, or read back."""

    default_code = "TRADING_PR_001"


class NewsError(TradingError):
    """A news/sentiment analysis could not be produced from the given inputs."""

    default_code = "TRADING_NW_001"


class CalendarError(TradingError):
    """An event/economic-calendar lookup could not be produced from the inputs."""

    default_code = "TRADING_EV_001"


class FundamentalsError(TradingError):
    """A fundamental analysis could not be produced from the given inputs."""

    default_code = "TRADING_FN_001"
