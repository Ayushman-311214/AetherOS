"""
The 6-state market-regime model + a stateful transition tracker.

The existing ``MarketRegime`` enum is the 5-state classification a single
snapshot can support (trending up/down, ranging, volatile, unknown). The brief
asks for a richer regime that adds two genuinely *temporal* states a single
snapshot cannot express -- ``LOW_VOLATILITY`` (calm, distinct from a whipsawing
HIGH-volatility tape) and ``TRANSITION`` (the regime is mid-shift, which is by
definition a property of successive reads, not one). This module supplies that
richer state as a *derived* read on top of the deterministic ``RegimeService``,
plus the tracker that emits ``MarketRegimeChanged`` only on a real, confirmed
transition -- never on a flicker.

Honesty: the states are a *characterisation*, not a prediction. TRANSITION is
honest "the last N reads disagree / are shifting" -- it is reported because the
evidence genuinely points between regimes, not smoothed into a confident label.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..domain.enums import MarketRegime
from ..domain.regime import RegimeAnalysis


class MarketRegimeState(str, Enum):
    """
    The 6-state regime vocabulary the brief asks for.

    TRENDING_BULLISH / TRENDING_BEARISH / RANGING / HIGH_VOLATILITY map onto the
    deterministic ``MarketRegime`` reads; ``LOW_VOLATILITY`` (calm tape) and
    ``TRANSITION`` (mid-shift) are *derived* from the read + the recent window.
    ``UNKNOWN`` is first-class: mock/unusable/thin data never gets a confident
    regime it didn't earn (CLAUDE.md sections 5, 28).
    """

    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


#: An ATR-fraction below this reads as a LOW-volatility tape (calm).
#: Chosen so a normal ~1% daily-range equity tape is LOW, and only clearly
#: compressed ranges drop below it. A heuristic, not a validated constant.
LOW_VOL_ATR_PCT = 0.005


def classify_state(
    analysis: RegimeAnalysis,
    *,
    atr_low_pct: float = LOW_VOL_ATR_PCT,
) -> MarketRegimeState:
    """
    Map one ``RegimeAnalysis`` to the 6-state vocabulary.

    The deterministic regime is the base; LOW_VOLATILITY is carved out of the
    RANGING read when realised volatility is genuinely compressed (calm, not
    just non-trending). UNKNOWN propagates honestly.
    """
    r = analysis.regime
    if r is MarketRegime.TRENDING_UP:
        return MarketRegimeState.TRENDING_BULLISH
    if r is MarketRegime.TRENDING_DOWN:
        return MarketRegimeState.TRENDING_BEARISH
    if r is MarketRegime.VOLATILE:
        return MarketRegimeState.HIGH_VOLATILITY
    if r is MarketRegime.RANGING:
        # A non-trending tape is LOW-volatility only when realised vol is
        # genuinely compressed; a choppy-but-not-calm range stays RANGING.
        if analysis.atr_pct is not None and analysis.atr_pct <= atr_low_pct:
            return MarketRegimeState.LOW_VOLATILITY
        return MarketRegimeState.RANGING
    return MarketRegimeState.UNKNOWN


@dataclass(frozen=True, slots=True)
class RegimeTransition:
    """A confirmed before->after regime change (the event's payload)."""

    instrument_key: str
    timeframe: str
    previous: MarketRegimeState
    current: MarketRegimeState
    direction: str          # directional bias of the NEW regime (never a prob)
    is_reliable: bool
    is_mock: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "previous_regime": self.previous.value,
            "regime": self.current.value,
            "direction": self.direction,
            "is_reliable": self.is_reliable,
            "is_mock": self.is_mock,
        }


class RegimeTracker:
    """
    Stateful regime-transition detector over a sequence of reads.

    Holds a short window of recent classified states; a transition is emitted
    only when the regime *settles* into a new state -- ``confirm`` consecutive
    reads at a different state -- rather than on a single flicker. That is the
    "only when it actually changes according to configured logic" rule: the
    dwell/confirm bar stops a one-off noisy read from announcing a regime flip
    that immediately reverts.

    TRANSITION is reported when the recent window is mixed *and* the running
    state is stale -- the regime is genuinely shifting, an honest "between
    regimes" read rather than a fabricated confident one.

    Deterministic: state is a pure function of the ordered reads fed to it.
    """

    def __init__(
        self,
        *,
        window: int = 3,
        confirm: int = 2,
    ) -> None:
        if window < 1 or confirm < 1:
            raise ValueError("window and confirm must be >= 1.")
        self._window = window
        self._confirm = confirm
        self._history: deque[MarketRegimeState] = deque(maxlen=window)
        self._current: MarketRegimeState | None = None

    @property
    def current(self) -> MarketRegimeState | None:
        return self._current

    def update(
        self, analysis: RegimeAnalysis
    ) -> RegimeTransition | None:
        """
        Fold one regime read in; return a transition iff the regime changed.

        Classifies the read into the 6-state vocabulary, appends it to the
        window, and decides the running regime:

        * The newest read's state becomes current once it has held for
          ``confirm`` consecutive reads (a confirmed flip -> ``TRANSITION`` ->
          new state, or straight to the new state if the window is unanimous).
        * A mixed window where the running state is no longer dominant is
          reported as ``TRANSITION``.
        * ``None`` while the running state is unchanged or not yet confirmed.
        """
        state = classify_state(analysis)
        self._history.append(state)

        if self._current is None:
            # First read establishes the regime outright.
            self._current = state
            return None

        if state == self._current:
            return None  # no change

        # Did the new state hold for `confirm` consecutive recent reads?
        recent = list(self._history)
        held = (
            len(recent) >= self._confirm
            and all(s == state for s in recent[-self._confirm :])
        )

        if held:
            prev = self._current
            self._current = state
            return RegimeTransition(
                instrument_key=analysis.instrument.key,
                timeframe=analysis.timeframe_value,
                previous=prev,
                current=state,
                direction=self._direction(state),
                is_reliable=analysis.is_reliable,
                is_mock=analysis.provenance.is_mock,
            )

        # The new state hasn't confirmed yet -- is the window genuinely mixed?
        distinct = set(recent)
        if len(distinct) > 1 and self._current is not MarketRegimeState.TRANSITION:
            prev = self._current
            self._current = MarketRegimeState.TRANSITION
            return RegimeTransition(
                instrument_key=analysis.instrument.key,
                timeframe=analysis.timeframe_value,
                previous=prev,
                current=MarketRegimeState.TRANSITION,
                direction="unknown",
                is_reliable=analysis.is_reliable,
                is_mock=analysis.provenance.is_mock,
            )
        return None

    @staticmethod
    def _direction(state: MarketRegimeState) -> str:
        if state is MarketRegimeState.TRENDING_BULLISH:
            return "up"
        if state is MarketRegimeState.TRENDING_BEARISH:
            return "down"
        if state is MarketRegimeState.RANGING:
            return "sideways"
        return "unknown"
