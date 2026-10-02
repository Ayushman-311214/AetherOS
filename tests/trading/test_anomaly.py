"""
AnomalyService: deterministic last-bar statistical-outlier detection.

These tests are fully deterministic and never touch the network: they hand the
service crafted ``MarketData`` (the RegimeService / RelativeStrengthService
pattern -- the service takes one candle series and does no I/O), so the
z-scored "unusual move / unusual volume" read is pinned against known inputs.
They assert the honesty rules (CLAUDE.md sections 5, 9, 27, 28): a genuine
return outlier is flagged anomalous with a directional lean and a non-mock
``ANOMALY`` evidence item, a volume-only spike is anomalous but non-directional
(SIDEWAYS), a quiet tape is a *determinate reliable* "no anomaly" read, and MOCK
/ unusable / too-thin data yields an UNKNOWN, never-reliable read with no
fabricated z-scores -- deterministically.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aetheros.config.config_loader import get_settings
from aetheros.trading.domain.enums import (
    Assertion,
    Direction,
    EvidenceType,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.instrument import Instrument
from aetheros.trading.domain.market_data import Candle, MarketData
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.enums import DataQualityStatus
from aetheros.trading.services.anomaly_service import AnomalyService

from .conftest import make_market_data

# A long, quiet alternating series: tiny, near-constant-magnitude moves so the
# per-bar returns have a small but positive baseline std and no single bar is an
# outlier. 90 bars fully covers the default 60-bar lookback.
_QUIET = [100.0 + (0.1 if i % 2 else -0.1) for i in range(90)]


def _service() -> AnomalyService:
    return AnomalyService(get_settings())


def _with_volumes(
    closes: list[float],
    volumes: list[float],
    *,
    symbol: str = "VOL",
    tier: SourceTier = SourceTier.PRIMARY,
) -> MarketData:
    """Build MarketData with per-bar volumes (open = prior close, so gaps are 0)."""
    assert len(closes) == len(volumes)
    end = datetime.now(timezone.utc).replace(microsecond=0)
    step = timedelta(seconds=Timeframe.D1.seconds)
    n = len(closes)
    candles: list[Candle] = []
    prev = closes[0]
    for i, (close, vol) in enumerate(zip(closes, volumes)):
        open_ = prev
        candles.append(
            Candle(
                timestamp=end - step * (n - 1 - i),
                open=open_,
                high=max(open_, close) + 0.5,
                low=min(open_, close) - 0.5,
                close=close,
                volume=vol,
            )
        )
        prev = close
    return MarketData(
        instrument=Instrument.parse(symbol),
        timeframe=Timeframe.D1,
        candles=tuple(candles),
        provenance=Provenance(source="test", tier=tier, detail="synthetic"),
        quality=DataQuality(status=DataQualityStatus.OK, issues=(), freshness_seconds=0.0),
    )


def test_quiet_tape_is_no_anomaly_and_reliable():
    a = _service().analyze(make_market_data(_QUIET, symbol="CALM"))

    # A quiet tape is a determinate, reliable "no anomaly" read -- not UNKNOWN.
    assert a.is_anomalous is False
    assert a.direction is Direction.SIDEWAYS
    assert a.is_reliable is True
    assert a.evidence is None


def test_return_spike_up_is_anomalous_and_reliable():
    closes = list(_QUIET)
    closes[-1] = 135.0  # a ~35% jump against a near-flat baseline
    a = _service().analyze(make_market_data(closes, symbol="POP"))

    assert a.is_anomalous is True
    assert a.direction is Direction.UP
    assert a.is_reliable is True
    assert a.return_z is not None and a.return_z > 3.0
    # Surfaced as a non-mock, DETECTED ANOMALY evidence item.
    assert a.evidence is not None
    assert a.evidence.type is EvidenceType.ANOMALY
    assert a.evidence.assertion is Assertion.DETECTED
    assert a.evidence.direction is Direction.UP
    assert a.evidence.is_reliable is True


def test_return_crash_down_is_anomalous():
    closes = list(_QUIET)
    closes[-1] = 60.0  # a sharp drop against a near-flat baseline
    a = _service().analyze(make_market_data(closes, symbol="DROP"))

    assert a.is_anomalous is True
    assert a.direction is Direction.DOWN
    assert a.return_z is not None and a.return_z < -3.0


def test_volume_only_spike_is_anomalous_but_non_directional():
    volumes = [1_000_000.0 + (i % 5) * 10_000.0 for i in range(90)]
    volumes[-1] = 80_000_000.0  # a huge volume spike with no price move
    a = _service().analyze(_with_volumes(_QUIET, volumes))

    assert a.is_anomalous is True
    assert a.volume_z is not None and a.volume_z > 3.0
    # A volume spike without a directional move is notable but non-directional.
    assert a.direction is Direction.SIDEWAYS
    assert a.is_reliable is True
    assert a.evidence is not None
    assert a.evidence.type is EvidenceType.ANOMALY


def test_mock_data_is_never_reliable():
    closes = list(_QUIET)
    closes[-1] = 135.0
    a = _service().analyze(make_market_data(closes, symbol="MOCKPOP", tier=SourceTier.MOCK))

    # The anomaly is still detected, but a MOCK series can never be leaned on.
    assert a.is_anomalous is True
    assert a.direction is Direction.UP
    assert a.is_reliable is False
    assert any("MOCK" in lim for lim in a.limitations)


def test_thin_data_is_unknown_not_fabricated():
    a = _service().analyze(make_market_data([100.0 + i for i in range(10)], symbol="THIN"))

    assert a.direction is Direction.UNKNOWN
    assert a.is_reliable is False
    assert a.is_anomalous is False
    assert a.return_z is None and a.volume_z is None
    assert a.evidence is None
    assert any("baseline bars" in lim for lim in a.limitations)


def test_is_deterministic():
    closes = list(_QUIET)
    closes[-1] = 135.0
    md = make_market_data(closes, symbol="POP")
    a = _service().analyze(md).to_dict()
    b = _service().analyze(md).to_dict()
    a.pop("created_at")
    b.pop("created_at")
    if a.get("evidence"):
        a["evidence"].pop("created_at", None)
        b["evidence"].pop("created_at", None)
    assert a == b
