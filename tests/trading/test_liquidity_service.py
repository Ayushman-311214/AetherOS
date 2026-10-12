"""
LiquidityService: deterministic liquidity read over a candle series.

Pins the structured read (participation, POC/value area, spread proxy,
price-vs-POC), the honest-unknown behavior on thin/unusable data, and
determinism. The service holds no I/O: every test drives it with synthetic
series from the shared fixtures.
"""

from __future__ import annotations

import pytest

from aetheros.trading.domain.enums import (
    DataQualityStatus,
    SourceTier,
)
from aetheros.trading.services.liquidity_service import LiquidityService

from .conftest import make_market_data


def _stable(analysis) -> dict:
    d = analysis.to_dict()
    d.pop("computed_at", None)
    prov = dict(d.get("provenance") or {})
    prov.pop("retrieved_at", None)
    d["provenance"] = prov
    return d


def test_structured_read_from_uptrend(uptrend_data):
    analysis = LiquidityService().analyze(uptrend_data)

    assert analysis.last_price == pytest.approx(uptrend_data.closes()[-1])
    assert analysis.participation in ("high", "average", "low")
    assert analysis.relative_volume == pytest.approx(1.0)  # constant volume
    assert analysis.poc is not None
    assert analysis.value_area_low is not None
    assert analysis.value_area_low <= analysis.poc <= analysis.value_area_high
    assert analysis.concentration in ("concentrated", "distributed")
    assert analysis.spread_proxy_pct is not None
    assert analysis.spread_proxy_pct > 0
    assert analysis.price_vs_poc_pct is not None  # uptrend: price above POC
    assert analysis.price_vs_poc_pct > 0
    assert analysis.observation  # non-empty human-readable summary
    assert analysis.limitations == ()


def _replace_last_volume(data, volume: float):
    """Rebuild ``data`` with only the final bar's volume changed."""
    last = data.candles[-1]
    return data.__class__(
        instrument=data.instrument,
        timeframe=data.timeframe,
        candles=data.candles[:-1]
        + (
            last.__class__(
                timestamp=last.timestamp,
                open=last.open,
                high=last.high,
                low=last.low,
                close=last.close,
                volume=volume,
            ),
        ),
        provenance=data.provenance,
        quality=data.quality,
    )


def test_participation_labels():
    prices = [100.0 + i for i in range(40)]
    baseline = make_market_data(prices, volume=1.0)

    high_vol = _replace_last_volume(baseline, 1000.0)
    high = LiquidityService().analyze(high_vol)
    assert high.participation == "high"
    assert high.relative_volume > 1.5

    low_vol = _replace_last_volume(baseline, 0.0)
    low = LiquidityService().analyze(low_vol)
    assert low.participation == "low"
    assert low.relative_volume == pytest.approx(0.0)


def test_thin_series_reports_unknowns_not_fabrications():
    data = make_market_data([100.0, 101.0, 102.0])
    analysis = LiquidityService().analyze(data)

    assert analysis.participation == "unknown"
    assert analysis.relative_volume is None
    assert analysis.spread_proxy_pct is None
    assert analysis.poc is not None  # a price range exists
    assert any(
        "volume baseline" in lim for lim in analysis.limitations
    )
    assert any("spread proxy" in lim for lim in analysis.limitations)


def test_flat_series_has_no_profile():
    data = make_market_data([100.0] * 10)
    analysis = LiquidityService().analyze(data)
    assert analysis.poc is None
    assert analysis.value_area_low is None
    assert analysis.concentration == "unknown"
    assert any("volume profile" in lim for lim in analysis.limitations)


def test_mock_and_bad_data_record_limitations():
    data = make_market_data(
        [100.0 + i for i in range(40)],
        tier=SourceTier.MOCK,
        quality=None,
    )
    analysis = LiquidityService().analyze(data)
    assert any("MOCK" in lim for lim in analysis.limitations)
    assert analysis.provenance.tier is SourceTier.MOCK


def test_determinism(uptrend_data):
    service = LiquidityService()
    assert _stable(service.analyze(uptrend_data)) == _stable(
        service.analyze(uptrend_data)
    )


def test_invalid_period_rejected():
    with pytest.raises(ValueError):
        LiquidityService(period=0)
    with pytest.raises(ValueError):
        LiquidityService(profile_bins=1)
