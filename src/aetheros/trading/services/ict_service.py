"""
ICT service: one deterministic, session-aware read per instrument/timeframe.

This is the assembly point, not a detector. It builds the session context once,
hands it to the eight independent detectors in :mod:`aetheros.trading.ict`, and
fuses their results into a single :class:`ICTAnalysis` -- so the shared work
(session windows, day buckets, the SMC read) is done once rather than once per
detector, and every detector sees exactly the same market picture.

It reuses rather than rebuilds (CLAUDE.md section 32): swings, structure breaks,
fair value gaps, equal-highs/lows clusters and the dealing range all come from
:class:`SMCService` via its public ``analyze``; the trend comes from
:class:`MarketStructureService`. What is genuinely new here is the time layer and
the eight ICT rules on top of that structure.

Nothing in this service calls an LLM, places an order or produces a probability.
It detects and describes; it is the strategy, signal and decision layers
(Phases 7+) that interpret. Its ``limitations`` tuple is the honest record of
what could not be determined, and it is never empty-but-silent about a failure
to read something (spec sections 5, 28).
"""

from __future__ import annotations

from datetime import timedelta

from ...core.logging import get_logger
from ..domain.enums import DataQualityStatus, SourceTier
from ..domain.ict import ICTAnalysis
from ..domain.market_data import MarketData
from ..domain.provenance import Provenance
from ..errors import InsufficientDataError
from ..ict.daily_bias import detect_daily_bias
from ..ict.judas_swing import (
    DEFAULT_OPENING_WINDOW_MINUTES,
    detect_judas_swings,
)
from ..ict.kill_zones import detect_kill_zones
from ..ict.liquidity_pools import detect_liquidity_pools
from ..ict.market_structure_shift import (
    DEFAULT_DISPLACEMENT_BODY_MULTIPLE,
    detect_market_structure_shifts,
)
from ..ict.ote import (
    DEFAULT_OTE_HIGH_RATIO,
    DEFAULT_OTE_LOW_RATIO,
    detect_ote,
)
from ..ict.power_of_three import (
    DEFAULT_ACCUMULATION_MAX_SHARE,
    detect_power_of_three,
)
from ..ict.session_models import detect_session_models
from ..ict.sessions import DEFAULT_EXCHANGE_TIMEZONE, SessionCatalogue
from .market_structure_service import MarketStructureService
from .smc_service import SMCService

logger = get_logger("trading.ict")


class ICTService:
    """Deterministic ICT detection over a candle series."""

    def __init__(
        self,
        structure: MarketStructureService | None = None,
        smc: SMCService | None = None,
        *,
        exchange_timezone: str = DEFAULT_EXCHANGE_TIMEZONE,
        session_catalogue: SessionCatalogue | None = None,
        ote_low_ratio: float = DEFAULT_OTE_LOW_RATIO,
        ote_high_ratio: float = DEFAULT_OTE_HIGH_RATIO,
        displacement_body_multiple: float = DEFAULT_DISPLACEMENT_BODY_MULTIPLE,
        opening_window_minutes: int = DEFAULT_OPENING_WINDOW_MINUTES,
        accumulation_max_share: float = DEFAULT_ACCUMULATION_MAX_SHARE,
        min_bars: int = 20,
    ) -> None:
        if not 0.0 < ote_low_ratio < ote_high_ratio < 1.0:
            raise ValueError(
                "OTE ratios must satisfy 0 < ote_low_ratio < ote_high_ratio < 1."
            )
        if displacement_body_multiple <= 0:
            raise ValueError("displacement_body_multiple must be positive.")
        if opening_window_minutes <= 0:
            raise ValueError("opening_window_minutes must be positive.")
        if not 0.0 < accumulation_max_share < 1.0:
            raise ValueError("accumulation_max_share must lie strictly within 0 and 1.")
        if min_bars < 5:
            raise ValueError("min_bars must be at least 5.")

        self._structure = structure or MarketStructureService()
        # The SMC service is shared, not rebuilt, so the structure half of the
        # market structure shift judgement cannot drift from the SMC read.
        self._smc = smc or SMCService(self._structure)
        self._catalogue = session_catalogue or SessionCatalogue(
            timezone=exchange_timezone
        )
        self._ote_low_ratio = ote_low_ratio
        self._ote_high_ratio = ote_high_ratio
        self._displacement_body_multiple = displacement_body_multiple
        self._opening_window_minutes = opening_window_minutes
        self._accumulation_max_share = accumulation_max_share
        self._min_bars = min_bars

    @property
    def catalogue(self) -> SessionCatalogue:
        return self._catalogue

    # ------------------------------------------------------------------

    def analyze(self, data: MarketData) -> ICTAnalysis:
        candles = data.candles
        if len(candles) < self._min_bars:
            raise InsufficientDataError(
                f"Need at least {self._min_bars} candles for ICT analysis, "
                f"got {len(candles)}.",
                context={"instrument": data.instrument.key, "bars": len(candles)},
            )

        timeframe = data.timeframe.value
        interval = timedelta(seconds=data.timeframe.seconds)
        last_price = float(data.last_price)

        limitations: list[str] = []
        if data.provenance.is_mock:
            limitations.append("ICT read is based on synthetic MOCK data.")
        if data.quality.status in (
            DataQualityStatus.MISSING,
            DataQualityStatus.INVALID,
        ):
            limitations.append(
                f"Underlying data quality is '{data.quality.status.value}'."
            )

        # Shared context: built once, handed to every detector.
        structure = self._structure.analyze(data)
        smc = self._smc.analyze(data)
        buckets = self._catalogue.bucket_by_local_date(candles)
        session_windows = self._catalogue.session_windows(
            candles, interval=interval
        )

        if not session_windows:
            limitations.append(
                "No session occurrence was found in this window; the time-based "
                "ICT concepts could not be evaluated."
            )

        bias, bias_limits = detect_daily_bias(
            buckets,
            last_price=last_price,
            timeframe=timeframe,
            trend=structure.trend,
        )
        limitations.extend(bias_limits)

        shifts = detect_market_structure_shifts(
            smc,
            data,
            displacement_body_multiple=self._displacement_body_multiple,
            catalogue=self._catalogue,
        )

        kill_zones, kill_zone_limits = detect_kill_zones(
            candles,
            session_windows,
            interval=interval,
            timeframe=timeframe,
            catalogue=self._catalogue,
        )
        limitations.extend(kill_zone_limits)

        ote, ote_limits = detect_ote(
            smc.dealing_range,
            candles,
            last_price=last_price,
            timeframe=timeframe,
            low_ratio=self._ote_low_ratio,
            high_ratio=self._ote_high_ratio,
        )
        limitations.extend(ote_limits)

        pools = detect_liquidity_pools(
            smc.liquidity,
            session_windows,
            buckets,
            candles,
            timeframe=timeframe,
            catalogue=self._catalogue,
        )

        judas_swings, judas_limits = detect_judas_swings(
            session_windows,
            candles,
            timeframe=timeframe,
            opening_window_minutes=self._opening_window_minutes,
        )
        limitations.extend(judas_limits)

        power_of_three, amd_limits = detect_power_of_three(
            session_windows,
            candles,
            interval=interval,
            timeframe=timeframe,
            accumulation_max_share=self._accumulation_max_share,
        )
        limitations.extend(amd_limits)

        session_models, model_limits = detect_session_models(
            session_windows, timeframe=timeframe
        )
        limitations.extend(model_limits)

        if not shifts:
            limitations.append(
                "No change of character was confirmed by displacement in this "
                "window; no market structure shift is reported."
            )
        if not pools:
            limitations.append(
                "No liquidity pools could be located from swings, sessions or "
                "the prior day in this window."
            )

        return ICTAnalysis(
            instrument_key=data.instrument.key,
            timeframe=timeframe,
            last_price=last_price,
            exchange_timezone=self._catalogue.timezone,
            sessions=session_windows,
            daily_bias=bias,
            market_structure_shifts=shifts,
            kill_zones=kill_zones,
            ote=ote,
            liquidity_pools=pools,
            judas_swings=judas_swings,
            power_of_three=power_of_three,
            session_models=session_models,
            provenance=Provenance(
                source=data.provenance.source,
                tier=(
                    SourceTier.MOCK
                    if data.provenance.is_mock
                    else SourceTier.DERIVED
                ),
                detail="deterministic ICT analysis",
            ),
            limitations=tuple(limitations),
        )
