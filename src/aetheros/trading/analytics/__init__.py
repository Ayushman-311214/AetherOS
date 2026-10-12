"""
Trading analytics (spec Phase 22).

Performance measured from actual journal/order/position data -- win rate,
average planned R:R, monthly return and strategy/symbol/timeframe breakdowns
-- reusing the shared :func:`trade_statistics` arithmetic so journal books
and backtest books reconcile. Like every quantitative layer, it flags thin,
mock or incomplete samples as not reliable rather than reporting them as
findings.
"""

from .journal_analytics import JournalAnalyticsService
from .performance import DimensionBreakdown, JournalAnalytics

__all__ = [
    "DimensionBreakdown",
    "JournalAnalytics",
    "JournalAnalyticsService",
]
