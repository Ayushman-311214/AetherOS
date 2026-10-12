"""
The shared read a strategy interprets (spec Phase 7).

A strategy does not fetch data, compute indicators or detect structure. Those
reads already exist, deterministically, in the analysis / SMC / ICT / breakout
layers -- and computing them once per evaluation rather than once per strategy
is what keeps "compare strategies" an apples-to-apples comparison. Every
strategy in a comparison is handed *the same* :class:`StrategyContext`, so a
disagreement between two strategies is a disagreement about interpretation, not
about which one saw different numbers.

The context is deliberately passive: a frozen bundle of reads, no services, no
I/O, no clock of its own. Building it is the service layer's job
(:class:`~aetheros.trading.services.strategy_service.StrategyService`), which is
what makes a strategy itself trivially testable from hand-built fixtures.

Optional members are honest about absence. ``ict`` is None when the ICT engine
could not run (too few bars, or no session coverage), and a strategy that needs
it reports "no ICT read available" rather than evaluating against an empty
read it might mistake for "nothing detected".
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.analysis import TradingAnalysis
from ..domain.breakout import BreakoutAnalysis
from ..domain.enums import TrendState
from ..domain.ict import ICTAnalysis
from ..domain.instrument import Instrument
from ..domain.market_data import MarketData
from ..domain.provenance import DataQuality, Provenance
from ..domain.smc import SMCAnalysis


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """
    One instrument/timeframe's reads, as every strategy in a comparison sees them.

    ``data`` is carried alongside the derived reads because a strategy legitimately
    needs the raw bars -- the latest close, the bar that just closed -- and
    re-deriving those from an indicator snapshot would be both wasteful and a
    second, divergent definition of "the last price".
    """

    data: MarketData
    analysis: TradingAnalysis
    smc: SMCAnalysis
    ict: ICTAnalysis | None = None
    breakout: BreakoutAnalysis | None = None
    #: Why an optional read is missing. An absent ICT read has two very
    #: different meanings -- "the engine ran and found nothing" versus "the
    #: engine could not run" -- and only the builder knows which happened, so
    #: it records the reason here rather than leaving a bare ``None``.
    degradations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        key = self.data.instrument.key
        timeframe = self.data.timeframe.value
        # Every read must describe the same instrument and timeframe as the
        # bars, or a strategy would silently combine two different markets.
        for label, instrument_key, read_timeframe in (
            ("analysis", self.analysis.instrument.key, self.analysis.timeframe_value),
            ("SMC read", self.smc.instrument_key, self.smc.timeframe),
            (
                "ICT read",
                self.ict.instrument_key if self.ict else key,
                self.ict.timeframe if self.ict else timeframe,
            ),
            (
                "breakout read",
                self.breakout.instrument.key if self.breakout else key,
                self.breakout.timeframe_value if self.breakout else timeframe,
            ),
        ):
            if instrument_key != key:
                raise ValueError(
                    f"The {label} and the market data must describe the same "
                    f"instrument ('{instrument_key}' vs '{key}')."
                )
            if read_timeframe != timeframe:
                raise ValueError(
                    f"The {label} and the market data must be on the same "
                    f"timeframe ('{read_timeframe}' vs '{timeframe}')."
                )

    # ------------------------------------------------------------------
    # Convenience accessors -- the fields strategies actually reach for
    # ------------------------------------------------------------------

    @property
    def instrument(self) -> Instrument:
        return self.data.instrument

    @property
    def timeframe(self) -> str:
        return self.data.timeframe.value

    @property
    def last_price(self) -> float:
        """The latest close, taken from the technical snapshot's own reading."""
        return self.analysis.technical.last_price

    @property
    def quality(self) -> DataQuality:
        return self.analysis.quality

    @property
    def provenance(self) -> Provenance:
        return self.analysis.provenance

    @property
    def is_mock(self) -> bool:
        return self.provenance.is_mock

    @property
    def trend(self) -> TrendState:
        return self.analysis.structure.trend

    @property
    def trend_strength(self) -> float:
        return self.analysis.structure.trend_strength

    @property
    def atr(self) -> float | None:
        """Average true range, or None when the series was too thin to compute it."""
        return self.analysis.technical.atr

    @property
    def rsi(self) -> float | None:
        return self.analysis.technical.rsi

    @property
    def adx(self) -> float | None:
        return self.analysis.technical.adx

    @property
    def limitations(self) -> tuple[str, ...]:
        """
        Every limitation the underlying reads reported, de-duplicated in order.

        A strategy that produced a setup on top of a degraded read must be able
        to say so, and it should say it once rather than once per read that
        happened to mention it.
        """
        seen: dict[str, None] = {}
        sources: tuple[tuple[str, ...], ...] = (
            self.analysis.limitations,
            self.smc.limitations,
            self.ict.limitations if self.ict else (),
            self.breakout.limitations if self.breakout else (),
            self.degradations,
        )
        for source in sources:
            for item in source:
                seen.setdefault(item, None)
        return tuple(seen)

    def to_dict(self) -> dict[str, object]:
        """A compact summary -- the full reads are large and live on their own."""
        return {
            "instrument": self.instrument.to_dict(),
            "timeframe": self.timeframe,
            "last_price": self.last_price,
            "trend": self.trend.value,
            "trend_strength": self.trend_strength,
            "atr": self.atr,
            "rsi": self.rsi,
            "adx": self.adx,
            "has_smc": True,
            "has_ict": self.ict is not None,
            "has_breakout": self.breakout is not None,
            "quality": self.quality.to_dict(),
            "provenance": self.provenance.to_dict(),
            "limitations": list(self.limitations),
            "degradations": list(self.degradations),
        }
