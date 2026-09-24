"""
The execution-pipeline projection.

These tests hold the *observational* fold to its contract: it turns a window of
trace events into an ordered, connected flow without inventing stages, groups
per agent-loop iteration, surfaces the currently-active stage, propagates
failures, and -- the security invariant -- never carries argument *values*, only
names. They assert on the model, not on rendered pixels (the renderer's own
contract lives in ``test_trace_ui.py``).
"""

from __future__ import annotations

from aetheros.core.observability import (
    ExecutionPipeline,
    PipelineStatus,
    StageKind,
    TraceEvent,
    TraceEventType,
    TraceStatus,
)


def _ev(event_type: TraceEventType, **kwargs) -> TraceEvent:
    kwargs.setdefault("run_id", "run-1")
    return TraceEvent.create(event_type, **kwargs)


def _single_tool_run() -> list[TraceEvent]:
    return [
        _ev(TraceEventType.INPUT_RECEIVED, message="what is my mouse position?"),
        _ev(TraceEventType.AGENT_STARTED, status=TraceStatus.STARTED),
        _ev(TraceEventType.AGENT_ITERATION_STARTED, status=TraceStatus.STARTED, iteration=1),
        _ev(
            TraceEventType.LLM_RESPONSE_RECEIVED,
            message="anthropic answered",
            status=TraceStatus.SUCCESS,
            iteration=1,
            duration_ms=500,
            metadata={"provider": "anthropic", "model": "claude"},
        ),
        _ev(
            TraceEventType.PLANNER_DECISION,
            message="Planner decided: tool_call",
            status=TraceStatus.SUCCESS,
            iteration=1,
            metadata={"type": "tool_call", "tool_name": "mouse_position"},
        ),
        _ev(
            TraceEventType.TOOL_SELECTED,
            message="mouse_position",
            status=TraceStatus.INFO,
            iteration=1,
            metadata={"tool_name": "mouse_position", "argument_names": ["x", "y"]},
        ),
        _ev(
            TraceEventType.TOOL_EXECUTION_STARTED,
            message="mouse_position",
            status=TraceStatus.STARTED,
            iteration=1,
            metadata={"tool_name": "mouse_position"},
        ),
        _ev(
            TraceEventType.TOOL_EXECUTION_COMPLETED,
            message="mouse_position",
            status=TraceStatus.SUCCESS,
            iteration=1,
            duration_ms=12,
            payload={"result_preview": '{"x": 785, "y": 963}'},
        ),
        _ev(
            TraceEventType.OBSERVATION_CREATED,
            message="mouse at (785, 963)",
            status=TraceStatus.SUCCESS,
            iteration=1,
            metadata={"tool_name": "mouse_position"},
        ),
    ]


class TestFold:
    def test_stages_appear_in_flow_order(self) -> None:
        pipeline = ExecutionPipeline.from_events(_single_tool_run())
        kinds = [s.kind for s in pipeline.visible_stages()]
        assert kinds == [
            StageKind.USER,
            StageKind.AGENT,
            StageKind.LLM,
            StageKind.PLANNER,
            StageKind.ACTION,
            StageKind.TOOL_EXEC,
            StageKind.TOOL_RESULT,
            StageKind.OBSERVATION,
        ]

    def test_absent_subsystems_produce_no_stage(self) -> None:
        # No STT/TTS events were emitted, so those stages must not be faked.
        pipeline = ExecutionPipeline.from_events(_single_tool_run())
        kinds = {s.kind for s in pipeline.stages}
        assert StageKind.STT not in kinds
        assert StageKind.TTS not in kinds

    def test_run_is_scoped_to_the_latest_request(self) -> None:
        old = [_ev(TraceEventType.INPUT_RECEIVED, message="old", run_id="run-0")]
        new = [_ev(TraceEventType.INPUT_RECEIVED, message="new", run_id="run-1")]
        pipeline = ExecutionPipeline.from_events(old + new)
        assert pipeline.run_id == "run-1"
        assert [s.description for s in pipeline.stages] == ["new"]

    def test_empty_window_is_safe(self) -> None:
        pipeline = ExecutionPipeline.from_events([])
        assert pipeline.stages == []
        assert pipeline.complete is False


class TestStatus:
    def test_active_stage_is_running_and_history_completed(self) -> None:
        # Truncate mid-execution: the last stage is live, earlier ones are done.
        events = _single_tool_run()[:-2]  # up to TOOL_EXECUTION_STARTED
        pipeline = ExecutionPipeline.from_events(events)
        stages = pipeline.visible_stages()
        assert stages[-1].kind is StageKind.TOOL_EXEC
        assert stages[-1].status is PipelineStatus.RUNNING
        assert all(s.status is PipelineStatus.COMPLETED for s in stages[:-1])
        assert pipeline.complete is False

    def test_completed_run_reports_completed(self) -> None:
        events = _single_tool_run() + [
            _ev(
                TraceEventType.FINAL_RESPONSE_CREATED,
                message="Your mouse is at (785, 963).",
                status=TraceStatus.SUCCESS,
                iteration=1,
            )
        ]
        pipeline = ExecutionPipeline.from_events(events)
        assert pipeline.complete is True
        assert pipeline.status is PipelineStatus.COMPLETED

    def test_failed_tool_marks_stage_and_pipeline_failed(self) -> None:
        events = _single_tool_run()[:-2] + [
            _ev(
                TraceEventType.TOOL_EXECUTION_FAILED,
                message="mouse_position",
                status=TraceStatus.FAILED,
                iteration=1,
                error="ToolError: boom",
            )
        ]
        pipeline = ExecutionPipeline.from_events(events)
        result = [s for s in pipeline.stages if s.kind is StageKind.TOOL_RESULT][0]
        assert result.status is PipelineStatus.FAILED
        assert pipeline.status is PipelineStatus.FAILED
        assert any("ToolError: boom" in d for d in result.details)

    def test_error_event_is_its_own_visible_stage(self) -> None:
        events = [
            _ev(TraceEventType.INPUT_RECEIVED, message="go"),
            _ev(
                TraceEventType.ERROR,
                message="LLM request failed",
                status=TraceStatus.FAILED,
                error="ProviderError: 500",
            ),
        ]
        pipeline = ExecutionPipeline.from_events(events)
        diags = [s for s in pipeline.stages if s.kind is StageKind.DIAGNOSTIC]
        assert len(diags) == 1
        assert diags[0].status is PipelineStatus.FAILED


class TestIterations:
    def test_loop_marker_hidden_on_first_iteration_shown_after(self) -> None:
        events = _single_tool_run() + [
            _ev(TraceEventType.AGENT_ITERATION_STARTED, status=TraceStatus.STARTED, iteration=2),
            _ev(TraceEventType.LLM_RESPONSE_RECEIVED, message="answered", status=TraceStatus.SUCCESS, iteration=2),
            _ev(TraceEventType.FINAL_RESPONSE_CREATED, message="done", status=TraceStatus.SUCCESS, iteration=2),
        ]
        pipeline = ExecutionPipeline.from_events(events)
        loops = [s for s in pipeline.visible_stages() if s.kind is StageKind.LOOP]
        assert len(loops) == 1
        assert loops[0].iteration == 2

    def test_iterations_are_not_merged(self) -> None:
        events = _single_tool_run() + [
            _ev(TraceEventType.AGENT_ITERATION_STARTED, status=TraceStatus.STARTED, iteration=2),
            _ev(TraceEventType.LLM_RESPONSE_RECEIVED, message="second", status=TraceStatus.SUCCESS, iteration=2),
        ]
        pipeline = ExecutionPipeline.from_events(events)
        llm_iters = sorted(s.iteration for s in pipeline.stages if s.kind is StageKind.LLM)
        assert llm_iters == [1, 2]


class TestSafety:
    def test_argument_values_never_appear_only_names(self) -> None:
        # TOOL_SELECTED carries names ["x", "y"]; the fold must show the names and
        # nothing that looks like a value, honouring the redaction invariant.
        pipeline = ExecutionPipeline.from_events(_single_tool_run())
        action = [s for s in pipeline.stages if s.kind is StageKind.ACTION][0]
        joined = " ".join(action.details)
        assert "x, y" in joined
        assert "names only" in joined
