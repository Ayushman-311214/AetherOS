"""
The trace event vocabulary (PHASE 1).

``TraceEvent`` is the single class every stage travels as; these tests pin the
things the rest of the system relies on: the discriminator enum's wire values,
the correlation defaults (``task_id`` mirrors ``run_id``, the stage label is
derived from the type) and the JSONL-ready ``to_dict`` projection.
"""

from __future__ import annotations

import datetime as dt

from aetheros.core.observability import TraceEvent, TraceEventType, TraceStatus
from aetheros.runtime.events.events import Event


class TestTraceEventType:
    def test_it_covers_the_whole_pipeline(self) -> None:
        # The stages PHASE 14's E2E asserts on must all exist as members.
        for name in (
            "INPUT_RECEIVED",
            "AGENT_STARTED",
            "LLM_REQUEST_STARTED",
            "LLM_RESPONSE_RECEIVED",
            "PLANNER_DECISION",
            "TOOL_SELECTED",
            "TOOL_EXECUTION_STARTED",
            "TOOL_EXECUTION_COMPLETED",
            "TOOL_EXECUTION_FAILED",
            "OBSERVATION_CREATED",
            "FINAL_RESPONSE_CREATED",
        ):
            assert hasattr(TraceEventType, name)

    def test_the_wire_values_are_terse_strings(self) -> None:
        # str-valued, so a serialized event reads {"event_type": "tool_selected"}.
        assert TraceEventType.TOOL_SELECTED.value == "tool_selected"
        assert isinstance(TraceEventType.TOOL_SELECTED, str)


class TestTraceEventCreate:
    def test_it_is_an_event_subclass(self) -> None:
        # Inheriting the frozen/slots Event base is what gives it event_id and
        # timestamp and lets the EventBus dispatch it.
        event = TraceEvent.create(TraceEventType.INPUT_RECEIVED)
        assert isinstance(event, Event)
        assert event.event_id
        assert isinstance(event.timestamp, dt.datetime)

    def test_task_id_defaults_to_run_id(self) -> None:
        # PHASE 13: task_id is reserved for multi-agent orchestration and mirrors
        # run_id until that exists.
        event = TraceEvent.create(TraceEventType.AGENT_STARTED, run_id="run-1")
        assert event.run_id == "run-1"
        assert event.task_id == "run-1"

    def test_an_explicit_task_id_is_kept(self) -> None:
        event = TraceEvent.create(
            TraceEventType.AGENT_STARTED, run_id="run-1", task_id="task-9"
        )
        assert event.task_id == "task-9"

    def test_the_stage_label_defaults_from_the_type(self) -> None:
        event = TraceEvent.create(TraceEventType.TOOL_SELECTED)
        assert event.stage == "Tool selected"

    def test_an_explicit_stage_wins(self) -> None:
        event = TraceEvent.create(
            TraceEventType.TOOL_SELECTED, stage="Custom stage"
        )
        assert event.stage == "Custom stage"

    def test_metadata_and_payload_are_copied_not_shared(self) -> None:
        # A frozen event must not alias a caller's dict, or a later mutation
        # would edit the record after the fact.
        meta = {"tool_name": "mouse_position"}
        event = TraceEvent.create(TraceEventType.TOOL_SELECTED, metadata=meta)
        meta["tool_name"] = "mutated"
        assert event.metadata == {"tool_name": "mouse_position"}

    def test_it_is_immutable(self) -> None:
        event = TraceEvent.create(TraceEventType.INPUT_RECEIVED)
        try:
            event.message = "changed"  # type: ignore[misc]
        except (AttributeError, TypeError):
            return
        raise AssertionError("TraceEvent should be frozen.")


class TestTraceEventToDict:
    def test_enums_become_wire_strings_and_timestamp_iso(self) -> None:
        event = TraceEvent.create(
            TraceEventType.TOOL_EXECUTION_COMPLETED,
            message="mouse_position",
            status=TraceStatus.SUCCESS,
            run_id="run-1",
            iteration=2,
            duration_ms=12.5,
            metadata={"tool_name": "mouse_position"},
            payload={"result_preview": "{'x': 500, 'y': 300}"},
        )

        row = event.to_dict()

        assert row["event_type"] == "tool_execution_completed"
        assert row["status"] == "success"
        assert row["run_id"] == "run-1"
        assert row["task_id"] == "run-1"
        assert row["iteration"] == 2
        assert row["duration_ms"] == 12.5
        assert row["metadata"] == {"tool_name": "mouse_position"}
        assert row["payload"] == {"result_preview": "{'x': 500, 'y': 300}"}
        # ISO-8601 string, round-trippable.
        assert dt.datetime.fromisoformat(row["timestamp"]) == event.timestamp

    def test_a_bare_event_serializes_with_null_correlation(self) -> None:
        row = TraceEvent.create(TraceEventType.WARNING).to_dict()
        assert row["run_id"] is None
        assert row["task_id"] is None
        assert row["iteration"] is None
        assert row["error"] is None
