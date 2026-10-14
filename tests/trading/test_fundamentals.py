"""
Deterministic fundamental-analysis tests (spec sections 5, 9, 21, 28).

Two layers, each pinned to the honesty rules:
- ``MockFundamentalsProvider`` is reproducible and loudly stamped
  ``SourceTier.MOCK`` -- synthetic financials can never masquerade as filings;
- ``FundamentalAnalysisService`` scores each reported metric with a fixed signed
  rubric and fuses them into an auditable ``FundamentalAnalysis`` that can never
  present MOCK, empty, or too-thin data as a reliable read, and publishes a
  ``FundamentalsAnalyzed`` event. A missing metric stays honestly absent and is
  never scored as a fabricated zero.
"""

from __future__ import annotations

import pytest

from aetheros.config.config_loader import get_settings
from aetheros.runtime.events.event_bus import EventBus
from aetheros.trading.domain.enums import (
    Assertion,
    Confidence,
    DataQualityStatus,
    Direction,
    EvidenceType,
    SourceTier,
)
from aetheros.trading.domain.fundamentals import FundamentalSnapshot
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.provenance import Provenance
from aetheros.trading.errors import FundamentalsError
from aetheros.trading.events import FundamentalsAnalyzed
from aetheros.trading.providers.fundamentals_base import FundamentalsProvider
from aetheros.trading.providers.mock_fundamentals_provider import (
    MockFundamentalsProvider,
)
from aetheros.trading.services.fundamental_service import FundamentalAnalysisService


def _snapshot(*, tier: SourceTier = SourceTier.SECONDARY, **metrics) -> FundamentalSnapshot:
    """A controllable, clearly-synthetic snapshot stamped a non-mock tier."""
    return FundamentalSnapshot(
        instrument_key="AAPL",
        provenance=Provenance(
            source="fake-fundamentals", tier=tier, detail="synthetic test financials"
        ),
        **metrics,
    )


_HEALTHY = dict(
    net_margin=0.20,
    revenue_growth_yoy=0.20,
    earnings_growth_yoy=0.20,
    return_on_equity=0.20,
    debt_to_equity=0.3,
    current_ratio=2.0,
    free_cash_flow=1.0e9,
)

_WEAK = dict(
    net_margin=-0.05,
    revenue_growth_yoy=-0.10,
    earnings_growth_yoy=-0.10,
    return_on_equity=-0.05,
    debt_to_equity=3.0,
    current_ratio=0.8,
    free_cash_flow=-1.0e8,
)

# Metrics whose rubric bands all land neutral -> a within-band SIDEWAYS lean.
_NEUTRAL = dict(
    gross_margin=0.30,
    pe_ratio=30.0,
    pb_ratio=3.0,
    price_to_sales=5.0,
    current_ratio=1.2,
)


class FakeFundamentalsProvider(FundamentalsProvider):
    """Hands back exactly the snapshot the test built; non-mock so it can be reliable."""

    name = "fake-fundamentals"
    tier = SourceTier.SECONDARY

    def __init__(self, snapshot: FundamentalSnapshot) -> None:
        self._snapshot = snapshot

    async def get_fundamentals(self, instrument) -> FundamentalSnapshot:
        return self._snapshot


def _service(provider: FundamentalsProvider, *, event_bus=None) -> FundamentalAnalysisService:
    return FundamentalAnalysisService(provider, get_settings(), event_bus=event_bus)


# ----------------------------------------------------------------------
# MockFundamentalsProvider
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic():
    provider = MockFundamentalsProvider()
    inst = Instrument.parse("AAPL")
    first = await provider.get_fundamentals(inst)
    second = await provider.get_fundamentals(inst)
    # Metrics and content-addressed id are stable; only the wall-clock
    # provenance.retrieved_at differs between fetches.
    assert first.to_dict()["metrics"] == second.to_dict()["metrics"]
    assert first.id == second.id


@pytest.mark.asyncio
async def test_mock_provider_is_labelled_mock():
    provider = MockFundamentalsProvider()
    assert provider.tier is SourceTier.MOCK
    assert provider.is_mock is True
    snap = await provider.get_fundamentals(Instrument.parse("AAPL"))
    assert snap.provenance.tier is SourceTier.MOCK
    # The synthetic feed reports every metric it knows -> full coverage.
    assert snap.metric_count > 0


@pytest.mark.asyncio
async def test_mock_provider_varies_by_symbol():
    a = await MockFundamentalsProvider().get_fundamentals(Instrument.parse("AAPL"))
    b = await MockFundamentalsProvider().get_fundamentals(Instrument.parse("MSFT"))
    # Different symbols seed different (still deterministic) financials.
    assert a.id != b.id


# ----------------------------------------------------------------------
# FundamentalAnalysisService scoring
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_scores_healthy_snapshot_as_up():
    analysis = await _service(FakeFundamentalsProvider(_snapshot(**_HEALTHY))).analyze("AAPL")
    assert analysis.direction is Direction.UP
    assert analysis.health_score > 0.15
    # A non-mock snapshot with enough scored metrics clears the reliability gate.
    assert analysis.is_reliable is True


@pytest.mark.asyncio
async def test_service_scores_weak_snapshot_as_down():
    analysis = await _service(FakeFundamentalsProvider(_snapshot(**_WEAK))).analyze("AAPL")
    assert analysis.direction is Direction.DOWN
    assert analysis.health_score < -0.15
    assert analysis.is_reliable is True


@pytest.mark.asyncio
async def test_service_neutral_snapshot_is_sideways():
    analysis = await _service(FakeFundamentalsProvider(_snapshot(**_NEUTRAL))).analyze("AAPL")
    # Metrics reported but no clear lean -> within-band SIDEWAYS, not a weak call.
    assert analysis.direction is Direction.SIDEWAYS
    assert abs(analysis.health_score) < 0.15


@pytest.mark.asyncio
async def test_service_builds_fundamental_evidence():
    analysis = await _service(FakeFundamentalsProvider(_snapshot(**_HEALTHY))).analyze("AAPL")
    assert analysis.evidence
    # Every derived claim is FUNDAMENTAL and CALCULATED -- a derived read over
    # sourced figures, never presented as an observed fact.
    assert all(ev.type is EvidenceType.FUNDAMENTAL for ev in analysis.evidence)
    assert all(ev.assertion is Assertion.CALCULATED for ev in analysis.evidence)


@pytest.mark.asyncio
async def test_service_missing_metric_is_not_scored_as_zero():
    # Only two metrics reported; the rest stay None and must not be fabricated.
    snap = _snapshot(net_margin=0.20, gross_margin=0.45)
    analysis = await _service(FakeFundamentalsProvider(snap)).analyze("AAPL")
    scored = {f.metric for f in analysis.factors}
    assert scored == {"net_margin", "gross_margin"}
    assert analysis.snapshot.metric_count == 2


# ----------------------------------------------------------------------
# Honesty gates
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_mock_feed_is_never_reliable():
    analysis = await _service(MockFundamentalsProvider()).analyze("AAPL")
    assert analysis.is_reliable is False
    assert analysis.provenance is not None
    assert analysis.provenance.tier is SourceTier.MOCK
    assert any("MOCK" in lim for lim in analysis.limitations)


@pytest.mark.asyncio
async def test_service_empty_snapshot_is_missing_and_honest():
    analysis = await _service(FakeFundamentalsProvider(_snapshot())).analyze("AAPL")
    assert analysis.quality is not None
    assert analysis.quality.status is DataQualityStatus.MISSING
    assert analysis.direction is Direction.UNKNOWN
    assert analysis.is_reliable is False
    assert analysis.scored_metric_count == 0
    assert any("no fundamental" in lim.lower() for lim in analysis.limitations)


@pytest.mark.asyncio
async def test_service_thin_coverage_is_partial_and_not_reliable():
    settings = get_settings()
    min_metrics = settings.TRADING_FUND_MIN_METRICS
    # One metric below the reliability threshold: surfaced but flagged too-thin.
    snap = _snapshot(net_margin=0.20)
    analysis = await _service(FakeFundamentalsProvider(snap)).analyze("AAPL")
    assert analysis.scored_metric_count < min_metrics
    assert analysis.quality is not None
    assert analysis.quality.status is DataQualityStatus.PARTIAL
    assert analysis.is_reliable is False
    assert any("thin" in lim.lower() for lim in analysis.limitations)


@pytest.mark.asyncio
async def test_service_confidence_never_exceeds_low_on_thin_coverage():
    analysis = await _service(FakeFundamentalsProvider(_snapshot(net_margin=0.20))).analyze("AAPL")
    assert analysis.confidence is Confidence.LOW


@pytest.mark.asyncio
async def test_service_publishes_event():
    received: list[FundamentalsAnalyzed] = []
    bus = EventBus()
    await bus.subscribe(FundamentalsAnalyzed, lambda e: received.append(e))

    await _service(FakeFundamentalsProvider(_snapshot(**_HEALTHY)), event_bus=bus).analyze("AAPL")

    assert len(received) == 1
    assert received[0].instrument_key == "AAPL"
    assert received[0].direction == Direction.UP.value
    assert received[0].is_reliable is True


@pytest.mark.asyncio
async def test_service_rejects_empty_symbol():
    with pytest.raises(FundamentalsError):
        await _service(FakeFundamentalsProvider(_snapshot())).analyze("")


@pytest.mark.asyncio
async def test_service_is_deterministic():
    provider = FakeFundamentalsProvider(_snapshot(**_HEALTHY))
    p1 = (await _service(provider).analyze("AAPL")).to_dict()
    p2 = (await _service(provider).analyze("AAPL")).to_dict()
    assert p1["direction"] == p2["direction"]
    assert p1["health_score"] == p2["health_score"]
    assert p1["factors"] == p2["factors"]
