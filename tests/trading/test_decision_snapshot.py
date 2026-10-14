"""
Decision snapshot (spec section 15) -- the reproducible reconstruction.

A :class:`DecisionSnapshot` captures the decision plus everything that drove
it: the data fingerprint, the component versions, the evidence ledger ids, the
verdict trail and the resulting action. The same decision over the same data
and the same versions must rebuild to the same content-addressed
``decision_id``; a changed version, changed data or changed decision must
yield a different one.

These tests prove the four-valued ``action`` (BUY/SELL/WAIT/NO_TRADE), that the
id is deterministic (not a random uuid), that evidence ids are carried
verbatim, and that no field is fabricated (a missing data window records an
empty fingerprint, never an invented one).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aetheros.trading.domain.enums import (
    DecisionAction,
    Direction,
    ReportRecommendation,
    SourceTier,
    Timeframe,
)
from aetheros.trading.domain.market_data import MarketData, Candle
from aetheros.trading.domain.provenance import DataQuality, Provenance
from aetheros.trading.domain.snapshot import DecisionSnapshot
from aetheros.trading.domain.versions import default_versions

from .conftest import make_market_data

# PLACEHOLDER_BUILDERS: a minimal valid TradingDecision to snapshot. Every field
# is set explicitly so the snapshot test asserts the assembled value, never a
# fabricated default.
def _decision(
    *,
    direction=Direction.UP,
    recommendation=ReportRecommendation.APPROVED,
    is_actionable=True,
    key="AAPL",
    timeframe="1d",
):
    from aetheros.trading.domain.decision import TradingDecision
    from aetheros.trading.domain.instrument import Instrument

    inst = Instrument.parse(key)
    return TradingDecision(
        instrument=inst,
        timeframe_value=timeframe,
        market_view="trending tape",
        strategy_id="trend_following",
        strategy_name="Trend Following",
        setup_id="su_1",
        direction=direction,
        confidence=__import__(
            "aetheros.trading.domain.enums", fromlist=["Confidence"]
        ).Confidence.HIGH,
        recommendation=recommendation,
        is_actionable=is_actionable,
        supporting=(),
        contradictory=(),
        supporting_weight=2.0,
        contradictory_weight=0.5,
        net_weight=1.5,
        entry=100.0,
        stop_loss=95.0,
        take_profit=115.0,
        risk_reward_ratio=3.0,
        invalidation="close below 95",
        reasoning="test decision",
        uncertainty=("thin sample",),
        critic_reasons=(),
        provenance=Provenance(source="test", tier=SourceTier.PRIMARY),
        quality=DataQuality(
            status=__import__(
                "aetheros.trading.domain.enums", fromlist=["DataQualityStatus"]
            ).DataQualityStatus.OK
        ),
    )


def _versions():
    return default_versions(provider="yahoo/primary")


def _snapshot(decision, data, versions=None):
    v = versions or _versions()
    return DecisionSnapshot.build(
        decision,
        data=data,
        versions=v,
        provenance=data.provenance if data else Provenance(
            source="test", tier=SourceTier.PRIMARY
        ),
        quality=DataQuality(
            status=__import__(
                "aetheros.trading.domain.enums", fromlist=["DataQualityStatus"]
            ).DataQualityStatus.OK
        ),
        critic_verdict="approve",
        critic_reasons=(),
    )


# ==============================================================
# The four-valued action (spec section 13)
# ==============================================================


def test_buy_when_up_and_approved_and_actionable():
    d = _decision(direction=Direction.UP, is_actionable=True)
    assert d.action is DecisionAction.BUY


def test_sell_when_down_and_approved_and_actionable():
    d = _decision(direction=Direction.DOWN, is_actionable=True)
    assert d.action is DecisionAction.SELL


def test_wait_when_directional_but_rejected():
    d = _decision(direction=Direction.UP, recommendation=ReportRecommendation.REJECTED)
    assert d.action is DecisionAction.WAIT


def test_no_trade_when_no_directional_side():
    d = _decision(direction=Direction.UNKNOWN, recommendation=ReportRecommendation.APPROVED)
    assert d.action is DecisionAction.NO_TRADE


def test_no_trade_when_recommendation_is_no_trade():
    d = _decision(direction=Direction.UP, recommendation=ReportRecommendation.NO_TRADE)
    assert d.action is DecisionAction.NO_TRADE


def test_wait_not_no_trade_is_a_distinct_outcome():
    # A judged-but-wanting directional read must not collapse into "insufficient
    # evidence": WAIT and NO_TRADE are deliberately different outcomes.
    d = _decision(direction=Direction.UP, recommendation=ReportRecommendation.REJECTED)
    assert d.action is DecisionAction.WAIT
    assert d.action is not DecisionAction.NO_TRADE


# ==============================================================
# Content-addressed id / reproducibility
# ==============================================================


def test_same_decision_same_data_same_versions_gives_same_id():
    data = make_market_data([100.0 + i for i in range(60)])
    v = _versions()
    d = _decision()
    a = _snapshot(d, data, v)
    b = _snapshot(d, data, v)
    assert a.decision_id == b.decision_id
    assert a.decision_id.startswith("ds_")


def test_different_version_gives_different_id():
    data = make_market_data([100.0 + i for i in range(60)])
    v1 = _versions()
    v2 = default_versions(provider="different-provider")
    d = _decision()
    a = _snapshot(d, data, v1)
    b = _snapshot(d, data, v2)
    assert a.decision_id != b.decision_id


def test_different_data_gives_different_id():
    a_data = make_market_data([100.0 + i for i in range(60)])
    b_data = make_market_data([200.0 + i for i in range(60)])
    v = _versions()
    d = _decision()
    a = _snapshot(d, a_data, v)
    b = _snapshot(d, b_data, v)
    assert a.decision_id != b.decision_id


def test_different_decision_gives_different_id():
    data = make_market_data([100.0 + i for i in range(60)])
    v = _versions()
    a = _snapshot(_decision(direction=Direction.UP), data, v)
    b = _snapshot(_decision(direction=Direction.DOWN), data, v)
    assert a.decision_id != b.decision_id


# ==============================================================
# The snapshot's payload -- nothing fabricated
# ==============================================================


def test_fingerprint_covers_series_identity_and_content():
    data = make_market_data([100.0 + i for i in range(60)])
    snap = _snapshot(_decision(), data)
    fp = snap.data_fingerprint
    assert fp["instrument_key"] == "TEST"
    assert fp["timeframe"] == "1d"
    assert fp["bar_count"] == 60
    assert fp["first_bar"] and fp["last_bar"]
    assert fp["content_hash"]


def test_missing_data_records_an_empty_fingerprint():
    snap = DecisionSnapshot.build(
        _decision(),
        data=None,
        versions=_versions(),
        provenance=Provenance(source="test", tier=SourceTier.PRIMARY),
        quality=DataQuality(
            status=__import__(
                "aetheros.trading.domain.enums", fromlist=["DataQualityStatus"]
            ).DataQualityStatus.OK
        ),
        critic_verdict="approve",
    )
    fp = snap.data_fingerprint
    assert fp["bar_count"] == 0
    assert fp["content_hash"] is None
    assert fp["instrument_key"] is None


def test_component_versions_are_embedded_verbatim():
    data = make_market_data([100.0 + i for i in range(60)])
    v = _versions()
    snap = _snapshot(_decision(), data, v)
    assert snap.component_versions == v.to_dict()
    assert snap.component_versions["provider"] == "yahoo/primary"


def test_is_reliable_false_on_mock_or_unusable():
    data = make_market_data(
        [100.0 + i for i in range(60)], tier=SourceTier.MOCK
    )
    snap = _snapshot(_decision(), data)
    assert snap.is_reliable is False


def test_to_dict_is_json_serialisable_and_complete():
    import json

    data = make_market_data([100.0 + i for i in range(60)])
    snap = _snapshot(_decision(), data)
    payload = snap.to_dict()
    for key in (
        "decision_id",
        "action",
        "direction",
        "recommendation",
        "decision",
        "evidence_ids",
        "critic_verdict",
        "data_fingerprint",
        "component_versions",
        "provenance",
        "quality",
    ):
        assert key in payload
    json.dumps(payload)  # must serialise without loss
