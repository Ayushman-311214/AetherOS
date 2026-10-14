"""
Decision-snapshot value object (spec section 15 -- reproducible reconstruction).

A :class:`DecisionSnapshot` is the audit-grade *bundle* of everything that
drove a single decision: the market-data fingerprint the read was computed
over, the component versions that produced it, the evidence that fed it, the
verdict trail, and the decision it settled on. Where the existing
:class:`~aetheros.trading.domain.prediction.PredictionRecord` flattens a
*report* into the section-8 contract, a snapshot captures the *decision* (which
may carry a strategy setup and hybrid visual note) plus the data/version
provenance needed to reproduce *why it decided what it did*.

It assembles; it computes nothing. The decision, evidence ids, direction and
recommendation are lifted verbatim from the already-produced objects; the data
fingerprint is a deterministic hash of the candle series' identity (symbol,
timeframe, bar timestamps) and *content* (close/volume), never the raw series;
the component versions are read straight off the shared
:class:`~aetheros.trading.domain.versions.ComponentVersions` manifest so the
replay can detect a rule/model/config change between runs (spec section 16).

The id is content-addressed: the same decision over the same data and the same
component versions rebuilds to the same snapshot id, independent of wall-clock.
That is what makes a past decision *reconstructable* -- re-running the same
input under the same versions reproduces the same record, while a version or
data change yields a *different* id (the spec's reproducibility guarantee, not
a duplicate).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .decision import TradingDecision
from .enums import DecisionAction, Direction, ReportRecommendation
from .instrument import Instrument
from .market_data import MarketData
from .provenance import DataQuality, Provenance
from .versions import ComponentVersions


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _stable_id(*, parts: tuple[str, ...]) -> str:
    payload = "|".join(parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"ds_{digest[:16]}"


def _data_fingerprint(data: MarketData | None) -> dict[str, Any]:
    """
    A deterministic fingerprint of the series the decision was computed over.

    Never embeds the raw candles (that would re-embed the whole series); it
    hashes the series' identity (instrument, timeframe, bar timestamps) and
    the close/volume vectors so two reads of the *same underlying series* share
    a fingerprint while a shifted or repriced series does not.
    """
    if data is None or not data.candles:
        return {
            "instrument_key": None,
            "timeframe": None,
            "bar_count": 0,
            "first_bar": None,
            "last_bar": None,
            "content_hash": None,
        }
    closes = ",".join(f"{c.close:g}" for c in data.candles)
    volumes = ",".join(f"{c.volume:g}" for c in data.candles)
    timestamps = ",".join(c.timestamp.isoformat() for c in data.candles)
    payload = "|".join(
        (
            data.instrument.key,
            data.timeframe.value,
            timestamps,
            closes,
            volumes,
        )
    )
    return {
        "instrument_key": data.instrument.key,
        "timeframe": data.timeframe.value,
        "bar_count": data.count,
        "first_bar": data.candles[0].timestamp.isoformat(),
        "last_bar": data.candles[-1].timestamp.isoformat(),
        "content_hash": hashlib.sha1(payload.encode("utf-8")).hexdigest(),
    }


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    """
    A reproducible reconstruction of one decision and everything that drove it.

    ``decision_id`` mirrors the content-addressed ids used across the trading
    domain (``ev_`` / ``pred_`` / ``su_`` / ``ds_``), so a stored snapshot can be
    deduplicated and cross-referenced without a database round-trip.
    """

    # Identity of the reconstructed decision.
    decision_id: str
    instrument_key: str
    timeframe: str

    # The decision itself, verbatim (BUY/SELL/WAIT/NO_TRADE plus its record).
    action: DecisionAction
    direction: Direction
    recommendation: ReportRecommendation
    is_actionable: bool
    decision: TradingDecision

    # What drove it: the evidence ledger ids (so the full claims stay in their
    # single source of truth) and the critic verdict trail.
    evidence_ids: tuple[str, ...]
    critic_verdict: str
    critic_reasons: tuple[str, ...]

    # Provenance & reproducibility: the data fingerprint the read rested on and
    # the component versions that produced it (section 15/16).
    data_fingerprint: dict[str, Any]
    component_versions: dict[str, str]

    provenance: Provenance
    quality: DataQuality
    limitations: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=_utcnow)

    @property
    def is_reliable(self) -> bool:
        """Whether this snapshot rests on trustworthy, non-mock, usable data."""
        return self.quality.usable and not self.provenance.is_mock

    @classmethod
    def build(
        cls,
        decision: TradingDecision,
        *,
        data: MarketData | None,
        versions: ComponentVersions,
        provenance: Provenance,
        quality: DataQuality,
        critic_verdict: str,
        critic_reasons: tuple[str, ...] = (),
        limitations: tuple[str, ...] = (),
    ) -> DecisionSnapshot:
        """
        Assemble a snapshot from an already-produced decision plus its drivers.

        The ``action`` is derived deterministically from the decision's
        direction + recommendation (the four-valued spec vocabulary); the data
        fingerprint and versions are read off the supplied series and manifest.
        """
        action = decision.action
        evidence_ids = tuple(
            r.reason_id or f"{r.type}:{r.detail}" for r in decision.supporting
        ) + tuple(
            r.reason_id or f"{r.type}:{r.detail}" for r in decision.contradictory
        )
        fingerprint = _data_fingerprint(data)
        version_map = versions.to_dict()
        # The full version map goes into the id: any component revision change
        # (indicator rules, strategy rules, calibration, risk policy, provider
        # lineage...) yields a different snapshot id, which is exactly the
        # reproducibility contract -- a changed input is a *different* record.
        decision_id = _stable_id(
            parts=(
                decision.instrument.key,
                decision.timeframe_value,
                action.value,
                decision.direction.value,
                decision.recommendation.value,
                fingerprint.get("content_hash") or "",
                "|".join(
                    f"{k}={version_map[k]}" for k in sorted(version_map)
                ),
                tuple(evidence_ids).__repr__(),
            )
        )
        return cls(
            decision_id=decision_id,
            instrument_key=decision.instrument.key,
            timeframe=decision.timeframe_value,
            action=action,
            direction=decision.direction,
            recommendation=decision.recommendation,
            is_actionable=decision.is_actionable,
            decision=decision,
            evidence_ids=evidence_ids,
            critic_verdict=critic_verdict,
            critic_reasons=critic_reasons,
            data_fingerprint=fingerprint,
            component_versions=version_map,
            provenance=provenance,
            quality=quality,
            limitations=limitations,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "instrument_key": self.instrument_key,
            "timeframe": self.timeframe,
            "action": self.action.value,
            "direction": self.direction.value,
            "recommendation": self.recommendation.value,
            "is_actionable": self.is_actionable,
            "decision": self.decision.to_dict(),
            "evidence_ids": list(self.evidence_ids),
            "critic_verdict": self.critic_verdict,
            "critic_reasons": list(self.critic_reasons),
            "data_fingerprint": self.data_fingerprint,
            "component_versions": self.component_versions,
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.to_dict(),
            "limitations": list(self.limitations),
            "created_at": self.created_at.isoformat(),
        }
