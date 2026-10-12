"""
Trading-history adapter (Phase 16).

The Memory-owned seam between the trading subsystem and durable history:
idempotent ingestion of predictions, outcomes, regimes, analyses, strategy
observations, calibration records and reasoning summaries, plus as-of
retrieval that prevents future-outcome leakage into historical tests.

Decoupling rule: the adapter accepts plain data (dicts / the memory-domain
records in ``..domain.trading``), never trading-package objects. Callers
translate their value objects (``PredictionRecord``, ``RegimeAnalysis``,
``TradingAnalysis``, ``StrategyEvaluation``, calibration audits) with the
``from_*`` constructors, which copy fields verbatim and never recompute
trading results. If the trading interfaces change shape, only the
constructors need attention -- the stored rows and retrieval contract are
stable.

Time discipline (the core of this phase):

* ``event_time`` -- when the market event happened. As-of retrieval
  (``history_as_of``) serves only rows with ``event_time <= as_of`` (rows
  without an event time are excluded from as-of queries -- undated rows
  must never leak into a historical test either).
* ``ingested_at`` -- set at write time, always "now".
* ``evaluation_time`` -- the outcome's ``resolved_at``; outcomes sort by it.

Immutability: predictions are stored once and never edited (re-ingesting
the same id returns the stored row). Outcomes append as separate rows
linked ``has_outcome`` to their prediction. Out-of-order arrival works
both ways: an outcome arriving before its prediction is stored
immediately (it is observed fact) and linked when the prediction lands;
a prediction landing when outcomes already exist backfills the links.
``remember_prediction_outcome`` (the single-shot path) keeps working;
rows it wrote read back through this adapter.

Scope isolation: every row carries ``instrument_id`` (+ ``timeframe`` /
``venue`` where available) in indexed metadata, and history queries scope
by instrument -- one instrument's history never appears in another's.

No second bus: everything persists through ``store``/``link``/``get``,
announced by the existing ``MemoryStored`` contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ...core.logging import get_logger
from .._clock import utcnow
from ..domain.enums import MemoryType
from ..domain.memory import Memory
from ..domain.trading import (
    AnalysisSnapshotMemory,
    CalibrationRecordMemory,
    MarketRegimeMemory,
    PredictionMemory,
    PredictionOutcomeMemory,
    ReasoningSummaryMemory,
    StrategyObservationMemory,
)
from ..storage.repository import MemoryRepository
from .results import WriteStatus

if TYPE_CHECKING:
    from .manager import MemoryManager

logger = get_logger("memory.trading_history")

_HISTORY_KINDS = (
    "prediction",
    "outcome",
    "regime",
    "analysis",
    "strategy_observation",
    "calibration",
    "reasoning_summary",
)


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


class TradingHistoryAdapter:
    """Idempotent trading-history ingestion + as-of retrieval.

    Constructed once by :class:`MemoryManager` (see the
    ``trading_history`` accessor); holds no row state itself.
    """

    def __init__(self, manager: MemoryManager, repository: MemoryRepository) -> None:
        self._manager = manager
        self._repo = repository

    # ------------------------------------------------------------------
    # from_* constructors: trading shapes in, memory records out.
    # Each copies fields verbatim (never recomputes) and tolerates
    # missing keys (defaults), so a trading-side shape change degrades
    # to a thinner row rather than a failed ingest.
    # ------------------------------------------------------------------

    @staticmethod
    def prediction_from_dict(data: dict[str, Any]) -> PredictionMemory:
        """Build a PredictionMemory from a trading prediction mapping.

        Accepts the memory-domain field names directly, plus the trading
        ``PredictionRecord`` shape (``instrument_key``/``symbol``,
        ``created_at``, ``probability_up``, ``confidence`` label,
        ``risk_reward_ratio``, ``overall_risk``). Caller-computed numbers
        pass through untouched.
        """
        get = data.get
        return PredictionMemory(
            # Deterministic id when the trading side supplies one
            # (PredictionRecord ids are content digests): re-ingesting the
            # same prediction is a safe no-op, never a duplicate row.
            id=str(get("id") or get("prediction_id") or Memory.new_id()),
            instrument=str(
                get("instrument") or get("symbol") or get("instrument_key") or ""
            ),
            direction=str(get("direction") or get("recommendation") or ""),
            timeframe=str(get("timeframe") or ""),
            horizon=str(get("horizon") or get("horizon_bars") or ""),
            prob_up=get("prob_up", get("probability_up")),
            prob_sideways=get("prob_sideways", get("probability_sideways")),
            prob_down=get("prob_down", get("probability_down")),
            confidence=str(get("confidence") or ""),
            risk_reward=get("risk_reward", get("risk_reward_ratio")),
            invalidation=str(get("invalidation") or ""),
            regime=str(get("regime") or ""),
            evidence=list(get("evidence") or get("evidence_refs") or []),
            model=str(get("model") or get("model_pipeline") or ""),
            model_version=str(get("model_version") or ""),
            data_version=str(get("data_version") or ""),
            source_tier=str(get("source_tier") or ""),
            predicted_at=_parse_dt(get("predicted_at") or get("created_at"))
            or utcnow(),
        )

    @staticmethod
    def outcome_from_dict(data: dict[str, Any]) -> PredictionOutcomeMemory:
        """Build an outcome record from a trading outcome mapping."""
        get = data.get
        return PredictionOutcomeMemory(
            id=str(get("id") or Memory.new_id()),
            prediction_id=str(get("prediction_id") or ""),
            instrument=str(
                get("instrument") or get("symbol") or get("instrument_key") or ""
            ),
            realized_direction=str(
                get("realized_direction") or get("direction") or ""
            ),
            correct=get("correct"),
            realized_return=get("realized_return"),
            brier=get("brier"),
            predicted_prob_up=get("predicted_prob_up", get("probability_up")),
            notes=str(get("notes") or ""),
            resolved_at=_parse_dt(get("resolved_at") or get("evaluation_time"))
            or utcnow(),
        )

    @staticmethod
    def regime_from_dict(data: dict[str, Any]) -> MarketRegimeMemory:
        """Build a regime record from a RegimeAnalysis-style mapping."""
        get = data.get
        instrument = data.get("instrument")
        if isinstance(instrument, dict):
            symbol = str(
                instrument.get("symbol") or instrument.get("instrument_key") or ""
            )
        else:
            symbol = str(instrument or get("symbol") or "")
        return MarketRegimeMemory(
            id=str(get("id") or Memory.new_id()),
            instrument=symbol,
            regime=str(get("regime") or ""),
            timeframe=str(get("timeframe") or get("timeframe_value") or ""),
            venue=get("venue"),
            direction=str(get("direction") or ""),
            adx=get("adx"),
            atr_pct=get("atr_pct"),
            reliable=bool(get("reliable", get("is_reliable", True))),
            source_tier=str(get("source_tier") or ""),
            model_version=str(get("model_version") or ""),
            data_version=str(get("data_version") or ""),
            event_time=_parse_dt(get("event_time") or get("created_at")),
        )

    @staticmethod
    def analysis_from_dict(data: dict[str, Any]) -> AnalysisSnapshotMemory:
        """Build an analysis snapshot from a TradingAnalysis-style mapping."""
        get = data.get
        instrument = data.get("instrument")
        if isinstance(instrument, dict):
            symbol = str(
                instrument.get("symbol") or instrument.get("instrument_key") or ""
            )
        else:
            symbol = str(instrument or get("symbol") or "")
        return AnalysisSnapshotMemory(
            id=str(get("id") or Memory.new_id()),
            instrument=symbol,
            direction=str(get("direction") or ""),
            timeframe=str(get("timeframe") or get("timeframe_value") or ""),
            venue=get("venue"),
            last_price=get("last_price"),
            directional_score=get("directional_score"),
            confidence_label=str(get("confidence") or get("confidence_label") or ""),
            evidence_refs=list(get("evidence_refs") or get("evidence") or []),
            limitations=list(get("limitations") or []),
            actionable=bool(get("actionable", get("is_actionable", False))),
            source_tier=str(get("source_tier") or ""),
            model_version=str(get("model_version") or ""),
            data_version=str(get("data_version") or ""),
            event_time=_parse_dt(get("event_time") or get("created_at")),
        )

    @staticmethod
    def strategy_from_dict(data: dict[str, Any]) -> StrategyObservationMemory:
        """Build a strategy observation from a StrategyEvaluation mapping."""
        get = data.get
        return StrategyObservationMemory(
            id=str(get("id") or Memory.new_id()),
            strategy_id=str(get("strategy_id") or ""),
            instrument=str(
                get("instrument") or get("symbol") or get("instrument_key") or ""
            ),
            strategy_name=str(get("strategy_name") or ""),
            timeframe=str(get("timeframe") or ""),
            venue=get("venue"),
            fired=bool(get("fired", get("setup") is not None)),
            rules_matched=list(get("rules_matched") or get("rules") or []),
            setup_ref=get("setup_ref") or (
                str(get("setup")) if get("setup") is not None else None
            ),
            limitations=list(get("limitations") or []),
            event_time=_parse_dt(get("event_time") or get("created_at")),
        )

    @staticmethod
    def calibration_from_dict(data: dict[str, Any]) -> CalibrationRecordMemory:
        """Build a calibration record from a calibration-audit mapping.

        Numbers pass through verbatim -- this row never computes
        calibration itself (contract: do not invent calibration
        algorithms).
        """
        get = data.get
        return CalibrationRecordMemory(
            id=str(get("id") or Memory.new_id()),
            scope=str(get("scope") or get("instrument_key") or "global"),
            instrument=str(get("instrument") or get("symbol") or ""),
            timeframe=str(get("timeframe") or ""),
            sample_size=int(get("sample_size") or 0),
            brier=get("brier"),
            baseline_brier=get("baseline_brier"),
            mean_predicted=get("mean_predicted"),
            realised_rate=get("realised_rate", get("base_rate")),
            bias=str(get("bias") or ""),
            trustworthy=bool(get("trustworthy", False)),
            proposed_correction=dict(get("proposed_correction") or {}),
            model_version=str(get("model_version") or ""),
            data_version=str(get("data_version") or ""),
            event_time=_parse_dt(get("event_time") or get("created_at")),
        )

    @staticmethod
    def reasoning_from_dict(data: dict[str, Any]) -> ReasoningSummaryMemory:
        """Build a reasoning summary (conclusion + source refs, never invented)."""
        get = data.get
        return ReasoningSummaryMemory(
            id=str(get("id") or Memory.new_id()),
            conclusion=str(get("conclusion") or ""),
            instrument=str(
                get("instrument") or get("symbol") or get("instrument_key") or ""
            ),
            timeframe=str(get("timeframe") or ""),
            venue=get("venue"),
            source_refs=list(get("source_refs") or []),
            limitations=list(get("limitations") or []),
            event_time=_parse_dt(get("event_time")),
        )

    # ------------------------------------------------------------------
    # Ingestion (idempotent, order-independent)
    # ------------------------------------------------------------------

    async def ingest_prediction(self, data: dict[str, Any]) -> Memory:
        """Store a prediction once; re-ingesting the id returns the row."""
        record = self.prediction_from_dict(data)
        memory = record.to_memory()
        result = await self._manager.store(memory, idempotency_key=record.id)
        if result.status is WriteStatus.STORED:
            await self._backfill_outcome_links(record.id)
            stored = result.memory
            assert stored is not None
            return stored
        if result.memory is not None:
            return result.memory
        return memory

    async def ingest_outcome(self, data: dict[str, Any]) -> Memory:
        """Append an outcome; link now or when the prediction lands.

        Out-of-order safe: an outcome arriving before its prediction is
        stored immediately (observed fact waits for nothing) and linked by
        ``_backfill_outcome_links`` when the prediction is ingested. A
        re-ingested outcome id returns the stored row (no duplicate).
        """
        record = self.outcome_from_dict(data)
        memory = record.to_memory()
        result = await self._manager.store(memory, idempotency_key=record.id)
        stored = result.memory if result.memory is not None else memory
        if result.status is WriteStatus.STORED:
            if await self._repo.exists(record.prediction_id):
                await self._manager.link(
                    record.prediction_id, stored.id, link_type="has_outcome"
                )
        return stored

    async def _backfill_outcome_links(self, prediction_id: str) -> int:
        """Link already-stored outcomes to a newly landed prediction."""
        linked = 0
        for outcome_row in await self._repo.find_by_metadata(
            "prediction_id", prediction_id
        ):
            if outcome_row.id == prediction_id:
                continue
            neighbours = await self._repo.linked_ids(prediction_id)
            if any(nid == outcome_row.id for nid, _, _ in neighbours):
                continue
            await self._manager.link(
                prediction_id, outcome_row.id, link_type="has_outcome"
            )
            linked += 1
        return linked

    async def ingest_regime(self, data: dict[str, Any]) -> Memory:
        return await self._ingest_simple(self.regime_from_dict(data))

    async def ingest_analysis(self, data: dict[str, Any]) -> Memory:
        return await self._ingest_simple(self.analysis_from_dict(data))

    async def ingest_strategy(self, data: dict[str, Any]) -> Memory:
        return await self._ingest_simple(self.strategy_from_dict(data))

    async def ingest_calibration(self, data: dict[str, Any]) -> Memory:
        return await self._ingest_simple(self.calibration_from_dict(data))

    async def ingest_reasoning(self, data: dict[str, Any]) -> Memory:
        record = self.reasoning_from_dict(data)
        stored = await self._ingest_simple(record)
        # Link the summary to each cited source that exists (missing refs
        # are skipped -- a summary must never fail because a cited row is
        # gone; the ref list in the payload preserves the citation).
        for ref in record.source_refs:
            try:
                target = await self._manager.get(ref)
            except Exception:  # noqa: BLE001 - defensive, never block ingest
                target = None
            if target is None:
                logger.warning("Reasoning source %r missing; link skipped.", ref)
                continue
            await self._manager.link(
                stored.id, ref, link_type="references",
                metadata={"kind": "reasoning_evidence"},
            )
        return stored

    async def _ingest_simple(self, record: Any) -> Memory:
        memory = record.to_memory()
        result = await self._manager.store(memory, idempotency_key=record.id)
        if result.memory is not None:
            return result.memory
        return memory

    # ------------------------------------------------------------------
    # Retrieval (scoped, as-of)
    # ------------------------------------------------------------------

    async def outcomes_for(self, prediction_id: str) -> list[Memory]:
        """Outcome rows linked to one prediction (missing prediction -> [])."""
        rows = await self._repo.find_by_metadata("prediction_id", prediction_id)
        return [r for r in rows if r.id != prediction_id]

    async def history_as_of(
        self,
        instrument: str,
        as_of: datetime,
        *,
        timeframe: str | None = None,
        kinds: list[str] | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        """Rows for one instrument with ``event_time <= as_of``.

        The anti-leakage query: future outcomes can never appear in a
        historical test because rows without an event time, and rows dated
        after ``as_of``, are excluded. Undated rows are excluded (not
        included) -- an undated row in a backtest is a leak vector, and
        predictions carry ``predicted_at``.... except predictions predate
        this phase's event_time stamping (their payload uses
        ``predicted_at``), so prediction rows fall back to it.
        """
        bound = max(1, int(limit))
        wanted = set(kinds) if kinds else set(_HISTORY_KINDS)
        candidates = await self._repo.find_by_metadata("instrument_id", instrument)
        out: list[tuple[str, Memory]] = []
        for row in candidates:
            if row.memory_type is not MemoryType.TRADING:
                continue
            kind = self._kind_of(row)
            if kind not in wanted:
                continue
            if timeframe is not None and row.metadata.get("timeframe") != timeframe:
                continue
            event_time = self._event_time_of(row)
            if event_time is None:
                continue  # undated rows never leak into as-of history
            if event_time > as_of:
                continue
            out.append((event_time.isoformat(), row))
        out.sort(key=lambda pair: pair[0])
        return [row for _, row in out[:bound]]

    @staticmethod
    def _kind_of(row: Memory) -> str:
        for kind in _HISTORY_KINDS:
            if kind in row.data:
                return kind
        tags = {t.strip().lower() for t in row.tags}
        if "prediction" in tags:
            return "prediction"
        if "outcome" in tags:
            return "outcome"
        return "unknown"

    @staticmethod
    def _event_time_of(row: Memory) -> datetime | None:
        meta_time = _parse_dt(row.metadata.get("event_time"))
        if meta_time is not None:
            return meta_time
        # Pre-Phase-16 prediction rows stamp predicted_at in the payload.
        payload = row.data.get("prediction")
        if isinstance(payload, dict):
            return _parse_dt(payload.get("predicted_at"))
        return None

    async def get_record(self, memory_id: str) -> Memory | None:
        """One history row by id (TRADING rows only; else None)."""
        try:
            row = await self._manager.get(memory_id)
        except Exception:  # noqa: BLE001 - reads degrade to absent
            return None
        if row is None or row.memory_type is not MemoryType.TRADING:
            return None
        return row

    async def verify_consumer_contract(self) -> dict[str, Any]:
        """Report which trading interfaces this adapter was verified against.

        Honest integration ledger (contract: report unverified consumer
        integration explicitly). Each entry names the trading shape, whether
        a live trading object was exercised, and what stood in for it.
        """
        return {
            "adapter": "TradingHistoryAdapter",
            "consumer_integration": "plain-dict seam (no trading imports)",
            "verified_live": [
                "PredictionMemory/PredictionOutcomeMemory round-trip "
                "(memory-domain records, exercised in tests)",
                "remember_prediction_outcome link shape (existing manager "
                "verb, exercised in tests)",
            ],
            "unverified_live_trading_objects": [
                "PredictionRecord.from_report (trading-owned; constructor "
                "accepts its to_dict()/asdict shape but no live TradingReport "
                "was exercised -- trading package owned by another agent)",
                "RegimeAnalysis / TradingAnalysis / StrategyEvaluation / "
                "CalibrationAudit live objects (same status: dict-shape "
                "constructors tested with representative mappings, not live "
                "trading instances)",
            ],
        }
