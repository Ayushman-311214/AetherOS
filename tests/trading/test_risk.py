"""
RiskService: deterministic risk geometry from a TradingAnalysis.

Every number here is a fixed calculation from the analysis inputs (ATR,
support/resistance, direction) -- never a probability and never an LLM guess
(spec section 5). Mock or unusable analysis must never yield an actionable
plan (spec section 61).
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.analysis import TradingAnalysis
from aetheros.trading.domain.enums import (
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
    RiskBand,
    SourceTier,
    Timeframe,
    TrendState,
)
from aetheros.trading.domain.evidence import Evidence
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.structure import Level, MarketStructure
from aetheros.trading.domain.technical import TechnicalSnapshot
from aetheros.trading.events import RiskAssessed
from aetheros.trading.services.risk_service import RiskService

# PLACEHOLDER_BUILDERS


def _prov(tier: SourceTier = SourceTier.PRIMARY) -> Provenance:
    return Provenance(source="test", tier=tier, detail="risk test fixture")


def _levels(prices, kind) -> tuple[Level, ...]:
    return tuple(
        Level(price=p, kind=kind, touches=2, confidence=Confidence.MEDIUM)
        for p in prices
    )


def _make_analysis(
    *,
    direction: Direction = Direction.UP,
    last_price: float = 100.0,
    atr: float | None = 2.0,
    supports=(),
    resistances=(),
    tier: SourceTier = SourceTier.PRIMARY,
    status: DataQualityStatus = DataQualityStatus.OK,
    with_evidence: bool = True,
) -> TradingAnalysis:
    """Construct a TradingAnalysis directly for precise risk-math assertions."""
    prov = _prov(tier)
    quality = DataQuality(status=status, issues=(), freshness_seconds=0.0)
    technical = TechnicalSnapshot(
        timeframe=Timeframe.D1,
        last_price=last_price,
        bars=120,
        provenance=prov,
        atr=atr,
    )
    structure = MarketStructure(
        trend=TrendState.UPTREND,
        trend_strength=0.6,
        swings=(),
        supports=_levels(supports, "support"),
        resistances=_levels(resistances, "resistance"),
        signals=(),
        higher_highs=True,
        higher_lows=True,
        lower_highs=False,
        lower_lows=False,
    )
    evidence = ()
    if with_evidence:
        evidence = (
            Evidence(
                instrument_key="TEST",
                type=EvidenceType.TREND,
                assertion=Assertion.CALCULATED,
                direction=direction,
                detail="fixture evidence",
                weight=0.6,
                confidence=Confidence.MEDIUM,
                provenance=prov,
                quality=quality,
            ),
        )
    return TradingAnalysis(
        instrument=Instrument.parse("TEST"),
        timeframe_value=Timeframe.D1.value,
        last_price=last_price,
        direction=direction,
        directional_score=0.5 if direction is Direction.UP else -0.5,
        confidence=Confidence.MEDIUM,
        technical=technical,
        structure=structure,
        evidence=evidence,
        volume=None,
        quality=quality,
        provenance=prov,
    )


def _svc(event_bus: EventBus | None = None) -> RiskService:
    return RiskService(get_settings(), event_bus=event_bus)


def _stable(assessment) -> dict:
    d = assessment.to_dict()
    d.pop("created_at", None)
    prov = dict(d.get("provenance") or {})
    prov.pop("retrieved_at", None)
    d["provenance"] = prov
    return d


# PLACEHOLDER_TESTS


@pytest.mark.asyncio
async def test_long_atr_stop_and_risk_reward():
    # entry 100, atr 2, 1.5x -> stop 97, risk 3; resistance 106 -> reward 6, rr 2.
    analysis = _make_analysis(direction=Direction.UP, atr=2.0, resistances=(106.0,))
    r = await _svc().assess(analysis)

    assert r.stop_loss == pytest.approx(97.0)
    assert r.stop_method == "atr"
    assert r.risk_per_unit == pytest.approx(3.0)
    assert r.target == pytest.approx(106.0)
    assert r.target_method == "structural"
    assert r.reward_per_unit == pytest.approx(6.0)
    assert r.risk_reward_ratio == pytest.approx(2.0)
    assert r.is_actionable is True
    assert "below 97" in r.invalidation


@pytest.mark.asyncio
async def test_short_atr_stop_mirrors_long():
    # entry 100, atr 2 -> stop 103; support 94 -> reward 6, risk 3, rr 2.
    analysis = _make_analysis(direction=Direction.DOWN, atr=2.0, supports=(94.0,))
    r = await _svc().assess(analysis)

    assert r.stop_loss == pytest.approx(103.0)
    assert r.target == pytest.approx(94.0)
    assert r.risk_reward_ratio == pytest.approx(2.0)
    assert r.is_actionable is True
    assert "above 103" in r.invalidation


@pytest.mark.asyncio
async def test_position_sizing_is_exact():
    analysis = _make_analysis(direction=Direction.UP, atr=2.0, resistances=(106.0,))
    r = await _svc().assess(analysis, account_equity=10_000.0, risk_pct=1.0)

    # Risk 1% of 10k = 100; risk/unit = 3 -> 33.333.. units; notional = size*entry.
    assert r.risk_amount == pytest.approx(100.0)
    assert r.position_size == pytest.approx(100.0 / 3.0)
    assert r.position_notional == pytest.approx((100.0 / 3.0) * 100.0)


@pytest.mark.asyncio
async def test_no_equity_omits_sizing_and_says_so():
    analysis = _make_analysis(direction=Direction.UP, atr=2.0, resistances=(106.0,))
    r = await _svc().assess(analysis)
    assert r.position_size is None
    assert any("position size not computed" in lim for lim in r.limitations)


# PLACEHOLDER_TESTS_2


@pytest.mark.asyncio
async def test_structural_stop_when_no_atr():
    # No ATR: fall back to the nearest support below entry for the stop.
    analysis = _make_analysis(
        direction=Direction.UP, atr=None, supports=(95.0,), resistances=(110.0,)
    )
    r = await _svc().assess(analysis)
    assert r.stop_loss == pytest.approx(95.0)
    assert r.stop_method == "structural"
    assert r.target == pytest.approx(110.0)


@pytest.mark.asyncio
async def test_projected_target_when_no_level_ahead():
    # No resistance above: target is projected at min_reward (1.5R), flagged.
    analysis = _make_analysis(direction=Direction.UP, atr=2.0, resistances=())
    r = await _svc().assess(analysis)
    assert r.target_method == "projected"
    # stop 97 -> risk 3; projected = 100 + 1.5*3 = 104.5
    assert r.target == pytest.approx(104.5)
    assert any("projected" in lim.lower() for lim in r.limitations)


@pytest.mark.asyncio
async def test_no_direction_yields_no_geometry():
    analysis = _make_analysis(direction=Direction.SIDEWAYS, atr=2.0)
    r = await _svc().assess(analysis)
    assert r.stop_loss is None
    assert r.target is None
    assert r.risk_reward_ratio is None
    assert r.is_actionable is False
    assert "no defined invalidation" in r.invalidation.lower()


@pytest.mark.asyncio
async def test_unknown_direction_is_not_actionable():
    analysis = _make_analysis(direction=Direction.UNKNOWN, atr=2.0)
    r = await _svc().assess(analysis)
    assert r.is_actionable is False
    assert r.stop_method == "none"


# PLACEHOLDER_TESTS_3


@pytest.mark.asyncio
async def test_mock_analysis_is_never_actionable():
    # Good geometry, but MOCK data must never produce a tradable plan.
    analysis = _make_analysis(
        direction=Direction.UP, atr=2.0, resistances=(106.0,), tier=SourceTier.MOCK
    )
    r = await _svc().assess(analysis)
    assert r.risk_reward_ratio == pytest.approx(2.0)  # math still computed
    assert r.is_actionable is False  # but not actionable
    assert r.provenance.tier is SourceTier.MOCK


@pytest.mark.asyncio
async def test_invalid_data_is_not_actionable():
    analysis = _make_analysis(
        direction=Direction.UP, atr=2.0, status=DataQualityStatus.INVALID
    )
    r = await _svc().assess(analysis)
    assert r.is_actionable is False
    assert r.overall_risk in (RiskBand.MEDIUM, RiskBand.HIGH)


@pytest.mark.parametrize(
    "atr,expected",
    [
        (0.5, RiskBand.LOW),     # 0.5% of price
        (2.0, RiskBand.MEDIUM),  # 2%
        (5.0, RiskBand.HIGH),    # 5%
        (None, RiskBand.UNKNOWN),
    ],
)
@pytest.mark.asyncio
async def test_volatility_bands(atr, expected):
    analysis = _make_analysis(direction=Direction.UP, atr=atr, resistances=(106.0,))
    r = await _svc().assess(analysis)
    assert r.volatility_risk is expected


@pytest.mark.asyncio
async def test_deterministic():
    analysis = _make_analysis(direction=Direction.UP, atr=2.0, resistances=(106.0,))
    a = await _svc().assess(analysis, account_equity=10_000.0)
    b = await _svc().assess(analysis, account_equity=10_000.0)
    assert _stable(a) == _stable(b)


@pytest.mark.asyncio
async def test_publishes_risk_assessed():
    received: list[RiskAssessed] = []
    bus = EventBus()
    await bus.subscribe(RiskAssessed, lambda e: received.append(e))

    analysis = _make_analysis(direction=Direction.UP, atr=2.0, resistances=(106.0,))
    r = await _svc(bus).assess(analysis)

    assert len(received) == 1
    assert received[0].risk_reward_ratio == r.risk_reward_ratio
    assert received[0].is_actionable == r.is_actionable




