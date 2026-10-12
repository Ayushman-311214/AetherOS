"""
ICT engine: session-aware market structure detection (spec Phase 6).

Eight independent, deterministic detectors plus the session/time engine they
stand on:

======================  ==================================================
:mod:`.sessions`        session/kill-zone definitions, lookups and the
                        exchange-local day buckets everything else reads
:mod:`.daily_bias`      the day's directional read, from the prior day
:mod:`.market_structure_shift`
                        a change of character confirmed by displacement
:mod:`.kill_zones`      kill-zone occurrences and what price did inside them
:mod:`.ote`             the 0.618-0.79 retracement band of the active leg
:mod:`.liquidity_pools` resting liquidity at equal highs/lows and extremes
:mod:`.judas_swing`     the false opening move, and its reversal
:mod:`.power_of_three`  a session decomposed into accumulation/manipulation/
                        distribution
:mod:`.session_models`  how each session behaved against its predecessor
======================  ==================================================

Each detector is independent and pure: it takes candles (or a session context)
and returns value objects, with no I/O, no LLM and no state. That is what makes
them separately testable, which the spec requires of them. Nothing here produces
a probability or a trade decision -- :class:`ICTService` assembles the read, and
the strategy/signal layers (Phases 7+) interpret it.
"""

from __future__ import annotations

from .daily_bias import detect_daily_bias
from .judas_swing import DEFAULT_OPENING_WINDOW_MINUTES, detect_judas_swings
from .kill_zones import detect_kill_zones
from .liquidity_pools import detect_liquidity_pools
from .market_structure_shift import (
    DEFAULT_DISPLACEMENT_BODY_MULTIPLE,
    detect_market_structure_shifts,
)
from .ote import DEFAULT_OTE_HIGH_RATIO, DEFAULT_OTE_LOW_RATIO, detect_ote
from .power_of_three import (
    DEFAULT_ACCUMULATION_MAX_SHARE,
    detect_power_of_three,
)
from .session_models import (
    CONSOLIDATION_RANGE_SHARE,
    EXPANSION_RANGE_MULTIPLE,
    detect_session_models,
)
from .sessions import (
    DEFAULT_EXCHANGE_TIMEZONE,
    DayBucket,
    SessionCatalogue,
)

__all__ = [
    "CONSOLIDATION_RANGE_SHARE",
    "DEFAULT_ACCUMULATION_MAX_SHARE",
    "DEFAULT_DISPLACEMENT_BODY_MULTIPLE",
    "DEFAULT_EXCHANGE_TIMEZONE",
    "DEFAULT_OPENING_WINDOW_MINUTES",
    "DEFAULT_OTE_HIGH_RATIO",
    "DEFAULT_OTE_LOW_RATIO",
    "EXPANSION_RANGE_MULTIPLE",
    "DayBucket",
    "SessionCatalogue",
    "detect_daily_bias",
    "detect_judas_swings",
    "detect_kill_zones",
    "detect_liquidity_pools",
    "detect_market_structure_shifts",
    "detect_ote",
    "detect_power_of_three",
    "detect_session_models",
]
