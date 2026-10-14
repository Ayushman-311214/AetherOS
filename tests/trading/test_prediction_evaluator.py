"""
The deterministic prediction-outcome evaluator (spec sections 6, 16, 29).

These pin the "was the previous prediction correct?" scorer at its honesty
boundary: a genuinely resolved directional call is graded hit/miss and (when the
record carried a reliable P(up)) given a Brier contribution; a call whose horizon
has not yet elapsed is PENDING and one whose entry bar cannot be located -- or
that rests on unusable data -- is UNRESOLVABLE. Neither is scored, and only a
RESOLVED outcome emits PredictionResolved. A resolution against MOCK data is
never a track record (is_reliable=False), a non-directional call is never graded,
and a mismatched instrument/timeframe is a typed error, not a silent wrong answer.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Direction,
    DataQualityStatus,
    PredictionOutcomeStatus,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.prediction import PredictionRecord
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.errors import PredictionError
from aetheros.trading.events import PredictionResolved
from aetheros.trading.services.prediction_evaluator import PredictionEvaluator


# --------------------------------------------------------------------------- #
# Fixtures / helpers                                                           #
# --------------------------------------------------------------------------- #


class _Bus:
    """A minimal event bus that records what the evaluator publishes."""

    def __init__(self) -> None:
        self.events: list = []

    async def publish(self, event) -> None:
        self.events.append(event)


def _ts(day: int) -> datetime:
    return datetime(2026, 1, day, tzinfo=timezone.utc)


# Five daily bars; closes chosen so entry@bar2 -> exit@bar4 is a clear +move.
_CLOSES = {1: 100.0, 2: 102.0, 3: 104.0, 4: 101.0, 5: 110.0}


def _market_data(
    *,
    tier: SourceTier = SourceTier.SECONDARY,
    status: DataQualityStatus = DataQualityStatus.OK,
    instrument: Instrument | None = None,
    timeframe: Timeframe = Timeframe.D1,
) -> MarketData:
    inst = instrument or Instrument(symbol="AAPL")
    candles = tuple(
        Candle(
            timestamp=_ts(day),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=1000.0,
        )
        for day, close in sorted(_CLOSES.items())
    )
    return MarketData(
        instrument=inst,
        timeframe=timeframe,
        candles=candles,
        provenance=Provenance(source="test", tier=tier),
        quality=DataQuality(status=status),
    )


def _record(
    *,
    direction: str = "up",
    created_at: datetime | None = None,
    horizon_bars: int = 2,
    is_mock: bool = False,
    probability_reliable: bool = False,
    probability_up: float | None = None,
    instrument_key: str = "AAPL",
    symbol: str = "AAPL",
    timeframe: str = "1d",
) -> PredictionRecord:
    return PredictionRecord(
        id="pred_test000000000",
        instrument_key=instrument_key,
        symbol=symbol,
        exchange=None,
        asset_class="equity",
        name=None,
        timeframe=timeframe,
        created_at=created_at if created_at is not None else _ts(3),
        horizon_bars=horizon_bars,
        recommendation="approved" if direction in ("up", "down") else "no_trade",
        is_actionable=direction in ("up", "down"),
        direction=direction,
        confidence="medium",
        directional_score=0.5,
        probability_reliable=probability_reliable,
        probability_up=probability_up,
        probability_down=(1.0 - probability_up) if probability_up is not None else None,
        risk_reward_ratio=2.0,
        overall_risk="medium",
        invalidation="close below support",
        source_tier=SourceTier.MOCK.value if is_mock else SourceTier.SECONDARY.value,
        is_mock=is_mock,
        model_pipeline="test_pipeline@1",
        evidence_count=3,
    )


def _evaluator(bus: _Bus | None = None) -> PredictionEvaluator:
    return PredictionEvaluator(get_settings(), event_bus=bus)


# --------------------------------------------------------------------------- #
# RESOLVED outcomes                                                            #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_resolved_correct_up_call_is_scored_a_hit():
    outcome = await _evaluator().resolve(_record(direction="up"), _market_data())

    assert outcome.status is PredictionOutcomeStatus.RESOLVED
    assert outcome.is_resolved is True
    # entry = bar@2026-01-03 close 104, exit = bar@2026-01-05 close 110.
    assert outcome.entry_price == 104.0
    assert outcome.exit_price == 110.0
    assert outcome.realized_return == pytest.approx((110.0 - 104.0) / 104.0)
    assert outcome.realized_direction is Direction.UP
    assert outcome.is_correct is True
    assert outcome.is_scored is True
    assert outcome.entry_timestamp == _ts(3)
    assert outcome.exit_timestamp == _ts(5)
    assert outcome.bars_elapsed == 2


@pytest.mark.asyncio
async def test_resolved_wrong_directional_call_is_scored_a_miss():
    # Same +move, but the prediction was DOWN -> a graded miss.
    outcome = await _evaluator().resolve(_record(direction="down"), _market_data())

    assert outcome.status is PredictionOutcomeStatus.RESOLVED
    assert outcome.realized_direction is Direction.UP
    assert outcome.is_correct is False
    assert outcome.is_scored is True


@pytest.mark.asyncio
async def test_resolved_non_directional_call_is_not_graded():
    # A SIDEWAYS call has no directional bet: measured, but is_correct stays None.
    outcome = await _evaluator().resolve(
        _record(direction="sideways"), _market_data()
    )

    assert outcome.status is PredictionOutcomeStatus.RESOLVED
    assert outcome.realized_return is not None
    assert outcome.is_correct is None
    assert outcome.is_scored is False


@pytest.mark.asyncio
async def test_flat_move_resolves_sideways_and_misses_a_directional_call():
    # entry@bar0 (day1, 100) exit@bar1 (day2, 102): +2% is outside the flat band,
    # so instead resolve a genuinely flat pair by predicting from a flat window.
    flat = {1: 100.0, 2: 100.05, 3: 104.0, 4: 101.0, 5: 110.0}
    md = _market_data()
    candles = tuple(
        Candle(
            timestamp=_ts(day),
            open=c,
            high=c,
            low=c,
            close=c,
            volume=1000.0,
        )
        for day, c in sorted(flat.items())
    )
    md = MarketData(
        instrument=md.instrument,
        timeframe=md.timeframe,
        candles=candles,
        provenance=md.provenance,
        quality=md.quality,
    )
    # created_at@day1 -> entry bar0 (100.0), horizon 1 -> exit bar1 (100.05):
    # +0.05% is inside the default 0.1% flat band -> SIDEWAYS.
    outcome = await _evaluator().resolve(
        _record(direction="up", created_at=_ts(1), horizon_bars=1), md
    )
    assert outcome.status is PredictionOutcomeStatus.RESOLVED
    assert outcome.realized_direction is Direction.SIDEWAYS
    assert outcome.is_correct is False  # predicted a move that did not happen


# --------------------------------------------------------------------------- #
# PENDING / UNRESOLVABLE                                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_pending_when_horizon_has_not_elapsed():
    # created_at@day4 -> entry bar3; horizon 2 -> exit bar5 which does not exist.
    outcome = await _evaluator().resolve(
        _record(created_at=_ts(4), horizon_bars=2), _market_data()
    )

    assert outcome.status is PredictionOutcomeStatus.PENDING
    assert outcome.is_resolved is False
    assert outcome.is_correct is None
    assert outcome.realized_return is None
    assert outcome.entry_price == 101.0  # bar@day4
    assert outcome.bars_elapsed == 1  # only day5 formed after entry
    assert outcome.is_reliable is False


@pytest.mark.asyncio
async def test_unresolvable_when_entry_bar_predates_all_candles():
    # The prediction was made before the first candle opens -> no entry bar.
    outcome = await _evaluator().resolve(
        _record(created_at=datetime(2025, 12, 1, tzinfo=timezone.utc)),
        _market_data(),
    )

    assert outcome.status is PredictionOutcomeStatus.UNRESOLVABLE
    assert outcome.is_correct is None
    assert outcome.entry_price is None
    assert outcome.is_reliable is False


@pytest.mark.asyncio
async def test_unresolvable_when_data_is_invalid():
    outcome = await _evaluator().resolve(
        _record(), _market_data(status=DataQualityStatus.INVALID)
    )

    assert outcome.status is PredictionOutcomeStatus.UNRESOLVABLE
    assert any("cannot be resolved" in lim for lim in outcome.limitations)


# --------------------------------------------------------------------------- #
# Mismatches                                                                    #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_instrument_mismatch_raises():
    with pytest.raises(PredictionError):
        await _evaluator().resolve(
            _record(instrument_key="MSFT", symbol="MSFT"), _market_data()
        )


@pytest.mark.asyncio
async def test_timeframe_mismatch_raises():
    with pytest.raises(PredictionError):
        await _evaluator().resolve(_record(timeframe="1h"), _market_data())


# --------------------------------------------------------------------------- #
# Honesty: mock resolution + Brier contribution                                #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_mock_resolution_is_never_a_track_record():
    outcome = await _evaluator().resolve(
        _record(is_mock=True), _market_data(tier=SourceTier.MOCK)
    )

    assert outcome.status is PredictionOutcomeStatus.RESOLVED
    assert outcome.is_mock is True
    assert outcome.is_reliable is False
    assert any("MOCK" in lim for lim in outcome.limitations)


@pytest.mark.asyncio
async def test_reliable_resolution_on_real_data_is_reliable():
    outcome = await _evaluator().resolve(_record(), _market_data())

    assert outcome.is_reliable is True
    assert outcome.is_mock is False
    assert outcome.limitations == ()


@pytest.mark.asyncio
async def test_brier_contribution_only_when_probability_reliable():
    # A reliable P(up)=0.8 against a realised UP move (y=1) -> (0.8-1)^2 = 0.04.
    reliable = await _evaluator().resolve(
        _record(probability_reliable=True, probability_up=0.8), _market_data()
    )
    assert reliable.predicted_p_up == 0.8
    assert reliable.brier_contribution == pytest.approx(0.04)

    # Without a reliable probability there is no calibration datapoint.
    unreliable = await _evaluator().resolve(
        _record(probability_reliable=False, probability_up=0.8), _market_data()
    )
    assert unreliable.predicted_p_up is None
    assert unreliable.brier_contribution is None


# --------------------------------------------------------------------------- #
# Events / determinism / serialisation                                          #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_event_emitted_only_for_resolved_outcomes():
    bus = _Bus()
    ev = _evaluator(bus)

    await ev.resolve(_record(), _market_data())  # RESOLVED -> emits
    await ev.resolve(_record(created_at=_ts(4)), _market_data())  # PENDING -> no
    await ev.resolve(  # UNRESOLVABLE -> no
        _record(created_at=datetime(2025, 12, 1, tzinfo=timezone.utc)),
        _market_data(),
    )

    assert len(bus.events) == 1
    published = bus.events[0]
    assert isinstance(published, PredictionResolved)
    assert published.is_correct is True
    assert published.predicted_direction == "up"
    assert published.realized_direction == "up"


@pytest.mark.asyncio
async def test_resolution_is_deterministic():
    record, md = _record(), _market_data()
    a = await _evaluator().resolve(record, md)
    b = await _evaluator().resolve(record, md)

    # resolved_at is a wall-clock stamp; every other field is a pure function of
    # the record and the candles.
    da, db = a.to_dict(), b.to_dict()
    da.pop("resolved_at")
    db.pop("resolved_at")
    assert da == db


@pytest.mark.asyncio
async def test_to_dict_shape_is_complete():
    outcome = await _evaluator().resolve(
        _record(probability_reliable=True, probability_up=0.8), _market_data()
    )
    d = outcome.to_dict()

    expected_keys = {
        "prediction_id",
        "instrument_key",
        "timeframe",
        "status",
        "predicted_direction",
        "realized_direction",
        "is_correct",
        "entry_timestamp",
        "exit_timestamp",
        "entry_price",
        "exit_price",
        "realized_return",
        "horizon_bars",
        "bars_elapsed",
        "predicted_p_up",
        "brier_contribution",
        "is_reliable",
        "is_mock",
        "limitations",
        "resolved_at",
        "reason",
    }
    assert set(d) == expected_keys
    assert d["status"] == "resolved"
    assert d["predicted_direction"] == "up"
    assert d["realized_direction"] == "up"
