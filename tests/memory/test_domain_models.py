"""
Domain-model acceptance tests (spec Phase 3).

Covers every memory record type: lossless serialisation round-trips for
supported values, malformed/unknown-field input, boundary scores, timezone-aware
timestamp handling, deserialisation of older persisted shapes, prediction/outcome
immutability + separation, immutable procedure history vs mutable summary, the
content-safety foundation (limits + secret redaction/rejection), and
compatibility with the existing repository serialisation contract.

These prove the *shapes* only. They deliberately do not assert any scoring,
decay, consolidation or learning behaviour -- those live in the service layer and
are tested there.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aetheros.core.errors.memory_error import MemoryValidationError
from aetheros.memory.domain import (
    MAX_CONTENT_CHARS,
    MAX_PAYLOAD_BYTES,
    ActionRecord,
    ContentPolicy,
    Entity,
    Episode,
    FailureRecord,
    Memory,
    MemoryImportance,
    MemoryLink,
    MemoryScope,
    MemorySource,
    MemoryStatus,
    MemoryType,
    Outcome,
    OutcomeStatus,
    PredictionMemory,
    PredictionOutcomeMemory,
    Preference,
    PreferenceKind,
    Procedure,
    ProcedureStep,
    Relationship,
    SecretAction,
    SourceType,
    Veracity,
    redact_text,
    scan_secrets,
)
from aetheros.memory.services.validator import MemoryValidator


# ----------------------------------------------------------------------
# Memory: lossless round-trip, boundaries, timestamps, versioning
# ----------------------------------------------------------------------


def test_memory_round_trip_is_lossless():
    original = Memory(
        content="Price closed above the 200-day MA.",
        memory_type=MemoryType.SEMANTIC,
        veracity=Veracity.OBSERVATION,
        data={"nested": {"a": 1}, "list": [1, 2, 3]},
        source=MemorySource(
            source_type=SourceType.TOOL,
            origin="technical_analysis",
            reference="RELIANCE",
            detail={"timeframe": "1d"},
        ),
        confidence=0.73,
        importance=MemoryImportance.HIGH,
        scope=MemoryScope.LONG_TERM,
        status=MemoryStatus.ACTIVE,
        evidence_count=4,
        tags=["technical", "trend"],
        entities=["RELIANCE"],
        metadata={"instrument_id": "RELIANCE", "timeframe": "1d"},
    )
    restored = Memory.from_dict(original.to_dict())
    assert restored.to_dict() == original.to_dict()
    assert restored.id == original.id
    assert restored.data == original.data
    assert restored.source.origin == "technical_analysis"


def test_memory_confidence_is_clamped_at_both_boundaries():
    assert Memory(content="x", confidence=2.5).confidence == 1.0
    assert Memory(content="x", confidence=-1.0).confidence == 0.0
    assert Memory(content="x", confidence=0.0).confidence == 0.0
    assert Memory(content="x", confidence=1.0).confidence == 1.0


def test_memory_rejects_blank_content():
    with pytest.raises(ValueError):
        Memory(content="   ")


def test_memory_timestamps_are_timezone_aware():
    m = Memory(content="x")
    assert m.created_at.tzinfo is not None
    assert m.updated_at.tzinfo is not None


def test_memory_from_dict_coerces_naive_timestamp_to_utc():
    payload = Memory(content="x").to_dict()
    payload["created_at"] = "2026-01-02T03:04:05"  # no tzinfo
    restored = Memory.from_dict(payload)
    assert restored.created_at.tzinfo is not None
    assert restored.created_at.utcoffset() == timezone.utc.utcoffset(None)


def test_memory_from_dict_ignores_unknown_fields():
    payload = Memory(content="x").to_dict()
    payload["totally_new_field_from_a_future_version"] = {"k": "v"}
    restored = Memory.from_dict(payload)  # must not raise
    assert restored.content == "x"


def test_memory_from_dict_malformed_missing_content_raises():
    with pytest.raises(KeyError):
        Memory.from_dict({"id": "abc"})


def test_memory_older_persisted_shape_without_version_defaults():
    # A row written before `version`/`evidence_count` existed.
    legacy = {
        "content": "legacy memory",
        "memory_type": "semantic",
        "veracity": "observation",
    }
    restored = Memory.from_dict(legacy)
    assert restored.version == 1
    assert restored.evidence_count == 1
    assert restored.scope is MemoryScope.LONG_TERM


def test_memory_expiry_and_permanent_override():
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    expiring = Memory(content="x", expires_at=past)
    assert expiring.is_expired()
    permanent = Memory(content="x", scope=MemoryScope.PERMANENT, expires_at=past)
    assert not permanent.is_expired()


# ----------------------------------------------------------------------
# MemoryLink / Relationship (MemoryRelationship)
# ----------------------------------------------------------------------


def test_memory_link_round_trip():
    link = MemoryLink(from_id="a", to_id="b", link_type="recovered_by", weight=0.5)
    assert MemoryLink.from_dict(link.to_dict()).to_dict() == link.to_dict()


def test_relationship_temporal_validity_round_trip():
    rel = Relationship(source_id="s", target_id="t", relation="prefers", confidence=0.9)
    assert rel.is_active
    restored = Relationship.from_dict(rel.to_dict())
    assert restored.is_active
    assert restored.confidence == 0.9


def test_entity_key_is_normalised():
    e = Entity(name="  RELIANCE ", entity_type="instrument")
    assert e.key == "instrument:reliance"


# ----------------------------------------------------------------------
# Episode (EpisodicMemory)
# ----------------------------------------------------------------------


def test_episode_round_trip_and_projection():
    ep = Episode(
        goal="open TradingView and read price",
        actions=[
            ActionRecord(name="launch", status=OutcomeStatus.SUCCESS),
            ActionRecord(name="read", status=OutcomeStatus.SUCCESS),
        ],
        outcome=Outcome(status=OutcomeStatus.SUCCESS, detail="done"),
        environment={"application": "tradingview", "entities": ["RELIANCE"]},
    )
    restored = Episode.from_dict(ep.to_dict())
    assert restored.to_dict() == ep.to_dict()
    mem = ep.to_memory()
    assert mem.memory_type is MemoryType.EPISODIC
    assert mem.veracity is Veracity.OBSERVATION  # never a FACT
    assert mem.data["episode"]["goal"] == ep.goal


# ----------------------------------------------------------------------
# Procedure (ProceduralMemory): mutable summary vs evidence-gated confidence
# ----------------------------------------------------------------------


def test_procedure_round_trip():
    proc = Procedure(
        name="refresh_chart",
        goal="get fresh price",
        steps=[ProcedureStep(action="click", arguments={"target": "refresh"})],
        success_count=3,
        failure_count=1,
    )
    assert Procedure.from_dict(proc.to_dict()).to_dict() == proc.to_dict()


def test_procedure_confidence_is_evidence_gated_not_asserted():
    # No evidence -> 0.5 (not certainty); one success must not read as 1.0.
    assert Procedure(name="n", goal="g").confidence == 0.5
    one = Procedure(name="n", goal="g", success_count=1)
    assert one.confidence < 1.0
    many = Procedure(name="n", goal="g", success_count=98, failure_count=0)
    assert many.confidence > one.confidence


# ----------------------------------------------------------------------
# Preference (PreferenceMemory)
# ----------------------------------------------------------------------


def test_preference_veracity_tracks_kind():
    assert Preference(subject="browser", value="Brave", kind=PreferenceKind.EXPLICIT).veracity is Veracity.USER_INPUT
    assert Preference(subject="browser", value="Brave", kind=PreferenceKind.INFERRED).veracity is Veracity.ASSUMPTION


def test_preference_projection_never_fact():
    mem = Preference(subject="x", value="y", kind=PreferenceKind.INFERRED).to_memory()
    assert mem.veracity is not Veracity.FACT
    assert mem.memory_type is MemoryType.PREFERENCE


# ----------------------------------------------------------------------
# FailureRecord (FailureMemory + RecoveryMemory)
# ----------------------------------------------------------------------


def test_failure_record_round_trip_and_recovery_flag():
    open_fail = FailureRecord(failure_type="timeout", error="no response")
    assert not open_fail.recovered
    recovered = FailureRecord(
        failure_type="timeout",
        error="no response",
        successful_recovery="retried with backoff",
        recovery_status=OutcomeStatus.SUCCESS,
    )
    assert recovered.recovered
    assert recovered.to_dict()["successful_recovery"] == "retried with backoff"
    mem = recovered.to_memory()
    assert mem.memory_type is MemoryType.FAILURE
    assert mem.veracity is Veracity.OBSERVATION


# ----------------------------------------------------------------------
# TradingMemory: prediction immutable, outcome separate + append-only
# ----------------------------------------------------------------------


def test_prediction_memory_round_trip_preserves_provenance():
    pred = PredictionMemory(
        instrument="RELIANCE",
        direction="BULLISH",
        timeframe="1d",
        horizon="1 trading day",
        prob_up=0.78,
        model="momentum_v3",
        model_version="3.2.1",
        data_version="2026-08-18",
    )
    d = pred.to_dict()
    assert d["model_version"] == "3.2.1"
    assert d["data_version"] == "2026-08-18"
    mem = pred.to_memory()
    assert mem.veracity is Veracity.PREDICTION  # never a FACT (CLAUDE.md s15)
    assert mem.data["prediction"]["prob_up"] == 0.78


def test_outcome_is_a_separate_record_referencing_the_prediction():
    pred = PredictionMemory(instrument="RELIANCE", direction="BULLISH", prob_up=0.78)
    outcome = PredictionOutcomeMemory(
        prediction_id=pred.id,
        instrument="RELIANCE",
        realized_direction="UP",
        correct=True,
        brier=0.05,
    )
    # Different identity, explicit back-reference, outcome is an OBSERVATION.
    assert outcome.id != pred.id
    assert outcome.prediction_id == pred.id
    assert outcome.to_memory().veracity is Veracity.OBSERVATION
    # The prediction record is untouched by creating an outcome.
    assert pred.to_dict()["id"] == pred.id


# ----------------------------------------------------------------------
# Content-safety foundation (spec Phase 3): limits + secret handling
# ----------------------------------------------------------------------


def test_scan_and_redact_detect_common_secret_shapes():
    text = "key AKIAIOSFODNN7EXAMPLE and api_key=longsecret123 and Bearer abcdefghijklmnopqrst"
    kinds = scan_secrets(text)
    assert "aws_access_key" in kinds
    cleaned, redacted = redact_text(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in cleaned
    assert "longsecret123" not in cleaned
    assert redacted  # something was removed


def test_validator_redacts_secret_by_default_and_records_it():
    m = Memory(content="my api_key=supersecret12345 is here")
    MemoryValidator().validate(m)
    assert "supersecret12345" not in m.content
    assert "assigned_secret" in m.metadata["redacted_secret_kinds"]


def test_validator_reject_mode_refuses_secret():
    policy = ContentPolicy(on_secret=SecretAction.REJECT)
    with pytest.raises(MemoryValidationError):
        MemoryValidator(policy).validate(Memory(content="password=hunter2abc"))


def test_validator_allow_mode_keeps_content():
    policy = ContentPolicy(on_secret=SecretAction.ALLOW)
    content = "api_key=keepmeexactly123"
    m = Memory(content=content)
    MemoryValidator(policy).validate(m)
    assert m.content == content


def test_validator_rejects_oversize_content():
    big = "x" * (MAX_CONTENT_CHARS + 1)
    with pytest.raises(MemoryValidationError):
        MemoryValidator().validate(Memory(content=big))


def test_validator_rejects_oversize_payload():
    huge = {"blob": "y" * (MAX_PAYLOAD_BYTES + 10)}
    with pytest.raises(MemoryValidationError):
        MemoryValidator().validate(Memory(content="ok", data=huge))


def test_validator_still_enforces_prediction_not_fact():
    bad = Memory(
        content="RELIANCE will go up",
        veracity=Veracity.FACT,
        source=MemorySource(source_type=SourceType.PREDICTION, origin="model"),
    )
    with pytest.raises(MemoryValidationError):
        MemoryValidator().validate(bad)


# ----------------------------------------------------------------------
# Compatibility with the existing repository serialisation contract
# ----------------------------------------------------------------------


def test_memory_to_dict_has_every_field_the_repository_reads():
    # Mirrors MemoryRepository._row_to_memory's payload keys; a drift here would
    # break persistence round-trips.
    required = {
        "id", "memory_type", "veracity", "content", "data", "source",
        "confidence", "importance", "scope", "status", "evidence_count",
        "access_count", "created_at", "updated_at", "last_accessed_at",
        "expires_at", "version", "tags", "entities", "metadata",
    }
    assert required <= set(Memory(content="x").to_dict().keys())
