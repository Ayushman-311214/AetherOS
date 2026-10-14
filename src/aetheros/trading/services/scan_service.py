"""
Watchlist-scan service.

Runs the deterministic analysis layer across a list of instruments and ranks
them, so the strongest *actionable* setups surface first -- the multi-instrument
counterpart to single-name analysis (CLAUDE.md sections 1, 26). It composes
:class:`AnalysisService` (section 22 -- reuse, never duplicate the signal maths);
it holds no analytical logic of its own and computes no signal, it only orders
what the analysis layer produced.

Honesty is inherited per row (sections 5, 28): a mock/unusable/UNKNOWN symbol is
included but flagged not actionable and ranked last, and a symbol whose data
could not be fetched is reported as an error row (with the error *type* only,
never arg values) rather than silently dropped or fabricated into a signal.

This increment is deliberately standalone: the service and its tool/command
stand beside the existing pipeline, so no existing behaviour changes.
"""

from __future__ import annotations

from collections.abc import Iterable

from ...config.settings import Settings
from ...core.logging import get_logger
from ..domain.enums import Confidence, Direction
from ..domain.scan import ScanEntry, ScanResult
from ..errors import TradingError
from .analysis_service import AnalysisService

logger = get_logger("trading.scan")

_CONFIDENCE_RANK = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}


class WatchlistScanService:
    """Deterministic multi-instrument ranking over the analysis layer."""

    def __init__(self, analysis: AnalysisService, settings: Settings) -> None:
        self._analysis = analysis
        self._settings = settings

    @property
    def max_symbols(self) -> int:
        return self._settings.TRADING_SCAN_MAX_SYMBOLS

    async def scan(
        self,
        symbols: Iterable[str],
        timeframe: str | None = None,
        *,
        limit: int | None = None,
    ) -> ScanResult:
        requested = self._normalise(symbols)
        tf = timeframe or "1d"

        entries: list[ScanEntry] = []
        errored = 0
        for symbol in requested:
            try:
                analysis = await self._analysis.analyze(symbol, timeframe, limit=limit)
            except (TradingError, ValueError) as exc:
                errored += 1
                entries.append(self._error_entry(symbol, exc))
                continue
            tf = analysis.timeframe_value
            entries.append(self._entry(symbol, analysis))

        ranked = tuple(sorted(entries, key=self._rank_key))
        actionable = sum(1 for e in ranked if e.is_actionable)
        return ScanResult(
            timeframe_value=tf,
            entries=ranked,
            requested=len(requested),
            analysed=len(requested) - errored,
            errored=errored,
            actionable=actionable,
        )

    # ------------------------------------------------------------------

    def _normalise(self, symbols: Iterable[str]) -> list[str]:
        """Trim, drop blanks, de-duplicate (order-preserving), and cap."""
        seen: dict[str, None] = {}
        for raw in symbols:
            s = (raw or "").strip()
            if s:
                seen.setdefault(s, None)
        return list(seen.keys())[: self.max_symbols]

    @staticmethod
    def _entry(symbol: str, analysis) -> ScanEntry:
        return ScanEntry(
            symbol=symbol,
            instrument_key=analysis.instrument.key,
            direction=analysis.direction,
            directional_score=analysis.directional_score,
            confidence=analysis.confidence,
            last_price=analysis.last_price,
            is_actionable=analysis.is_actionable,
            is_reliable=(
                analysis.quality.usable and not analysis.provenance.is_mock
            ),
            is_mock=analysis.provenance.is_mock,
            note=analysis.limitations[0] if analysis.limitations else "",
        )

    @staticmethod
    def _error_entry(symbol: str, exc: Exception) -> ScanEntry:
        # Report the failure by its type only -- never an arg value (sections 19, 28).
        logger.warning("Scan skipped %s: %s", symbol, type(exc).__name__)
        return ScanEntry(
            symbol=symbol,
            instrument_key=symbol,
            direction=Direction.UNKNOWN,
            directional_score=0.0,
            confidence=Confidence.LOW,
            last_price=None,
            is_actionable=False,
            is_reliable=False,
            is_mock=False,
            note=f"could not analyse ({type(exc).__name__})",
            errored=True,
        )

    @staticmethod
    def _rank_key(entry: ScanEntry) -> tuple:
        """Strongest actionable setups first; errored rows last.

        Sort ascending on a tuple where "better" is smaller: actionable before
        not, non-errored before errored, then larger absolute lean and higher
        confidence first (negated).
        """
        return (
            not entry.is_actionable,
            entry.errored,
            -abs(entry.directional_score),
            -_CONFIDENCE_RANK[entry.confidence],
            entry.symbol,
        )
