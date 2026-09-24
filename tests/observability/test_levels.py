"""
Trace verbosity levels and the per-event filter (PHASE 8, PHASE 12).

``resolve_level`` must be tolerant -- it takes a value straight from the
environment or a CLI command -- and ``level_for_event`` must pull any failure
down to the ERROR floor so an error surfaces even at a low verbosity.
"""

from __future__ import annotations

import pytest

from aetheros.core.observability import (
    TraceEventType,
    TraceStatus,
    level_for_event,
    resolve_level,
)
from aetheros.core.observability.levels import TraceLevel


class TestResolveLevel:
    def test_none_defaults_to_normal(self) -> None:
        assert resolve_level(None) is TraceLevel.NORMAL

    def test_an_unknown_string_falls_back_to_normal(self) -> None:
        # A typo in TRACE_LEVEL must not crash a run.
        assert resolve_level("lowd") is TraceLevel.NORMAL

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("off", TraceLevel.OFF),
            ("none", TraceLevel.OFF),
            ("error", TraceLevel.ERROR),
            ("minimal", TraceLevel.MINIMAL),
            ("normal", TraceLevel.NORMAL),
            ("default", TraceLevel.NORMAL),
            ("debug", TraceLevel.DEBUG),
            ("verbose", TraceLevel.VERBOSE),
            ("all", TraceLevel.VERBOSE),
            ("  VERBOSE  ", TraceLevel.VERBOSE),
        ],
    )
    def test_aliases_and_whitespace(self, value: str, expected: TraceLevel) -> None:
        assert resolve_level(value) is expected

    def test_an_int_maps_onto_the_scale(self) -> None:
        assert resolve_level(5) is TraceLevel.VERBOSE

    def test_an_out_of_range_int_falls_back_to_normal(self) -> None:
        assert resolve_level(99) is TraceLevel.NORMAL

    def test_a_level_passes_through(self) -> None:
        assert resolve_level(TraceLevel.DEBUG) is TraceLevel.DEBUG

    def test_the_scale_is_ordered(self) -> None:
        assert (
            TraceLevel.OFF
            < TraceLevel.ERROR
            < TraceLevel.MINIMAL
            < TraceLevel.NORMAL
            < TraceLevel.DEBUG
            < TraceLevel.VERBOSE
        )


class TestLevelForEvent:
    def test_a_normal_stage_is_normal(self) -> None:
        assert (
            level_for_event(TraceEventType.TOOL_SELECTED, TraceStatus.INFO)
            is TraceLevel.NORMAL
        )

    def test_a_major_stage_shows_early(self) -> None:
        # INPUT_RECEIVED / AGENT_STARTED / FINAL_RESPONSE_CREATED are visible even
        # at MINIMAL.
        assert (
            level_for_event(TraceEventType.INPUT_RECEIVED, TraceStatus.INFO)
            <= TraceLevel.MINIMAL
        )
        assert (
            level_for_event(
                TraceEventType.FINAL_RESPONSE_CREATED, TraceStatus.SUCCESS
            )
            <= TraceLevel.MINIMAL
        )

    def test_bookkeeping_is_verbose(self) -> None:
        # Argument validation is fine-grained -- only shown at VERBOSE.
        assert (
            level_for_event(
                TraceEventType.TOOL_ARGUMENTS_VALIDATED, TraceStatus.INFO
            )
            is TraceLevel.VERBOSE
        )

    def test_a_failed_status_rides_the_error_floor(self) -> None:
        # PHASE 12: any error surfaces even at a low level. A stage that is
        # normally VERBOSE, once it FAILED, is pulled down to ERROR.
        assert (
            level_for_event(
                TraceEventType.TOOL_ARGUMENTS_VALIDATED, TraceStatus.FAILED
            )
            is TraceLevel.ERROR
        )
        assert (
            level_for_event(TraceEventType.ERROR, TraceStatus.ERROR)
            is TraceLevel.ERROR
        )
