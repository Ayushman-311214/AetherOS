"""
JSON-Lines persistence of a run's trace (PHASES 9, 13).

The writer is the audit trail the brief asks for: one file per run, one event
per line, flushed as it goes so a crash mid-run still leaves an ordered, readable
record. It must be filename-safe (a stray path separator in a run id cannot let a
trace escape its directory) and it must never raise into the run it is recording.
"""

from __future__ import annotations

import json
from pathlib import Path

from aetheros.core.observability import TraceEvent, TraceEventType, TraceStatus
from aetheros.core.observability.persistence import (
    _UNKNOWN_RUN,
    TraceFileWriter,
    _safe_name,
)


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class TestTraceFileWriter:
    def test_events_for_one_run_land_in_one_ordered_file(self, tmp_path: Path) -> None:
        writer = TraceFileWriter(tmp_path)
        writer.write(TraceEvent.create(TraceEventType.INPUT_RECEIVED, run_id="run-1"))
        writer.write(
            TraceEvent.create(
                TraceEventType.FINAL_RESPONSE_CREATED,
                run_id="run-1",
                status=TraceStatus.SUCCESS,
            )
        )
        writer.close()

        rows = _read_lines(tmp_path / "run-1.jsonl")
        assert [r["event_type"] for r in rows] == [
            "input_received",
            "final_response_created",
        ]
        assert all(r["run_id"] == "run-1" for r in rows)

    def test_separate_runs_get_separate_files(self, tmp_path: Path) -> None:
        writer = TraceFileWriter(tmp_path)
        writer.write(TraceEvent.create(TraceEventType.AGENT_STARTED, run_id="run-a"))
        writer.write(TraceEvent.create(TraceEventType.AGENT_STARTED, run_id="run-b"))
        writer.close()

        assert (tmp_path / "run-a.jsonl").exists()
        assert (tmp_path / "run-b.jsonl").exists()

    def test_a_run_without_a_correlation_id_still_persists(
        self, tmp_path: Path
    ) -> None:
        # A bare event (no run_id) must go somewhere rather than crash on a None
        # filename.
        writer = TraceFileWriter(tmp_path)
        writer.write(TraceEvent.create(TraceEventType.WARNING))
        writer.close()

        rows = _read_lines(tmp_path / f"{_UNKNOWN_RUN}.jsonl")
        assert rows[0]["event_type"] == "warning"

    def test_the_directory_is_created_lazily(self, tmp_path: Path) -> None:
        nested = tmp_path / "logs" / "traces"
        writer = TraceFileWriter(nested)
        # Nothing touched the disk until the first write.
        assert not nested.exists()
        writer.write(TraceEvent.create(TraceEventType.AGENT_STARTED, run_id="run-1"))
        writer.close()
        assert (nested / "run-1.jsonl").exists()

    def test_close_is_idempotent(self, tmp_path: Path) -> None:
        writer = TraceFileWriter(tmp_path)
        writer.write(TraceEvent.create(TraceEventType.AGENT_STARTED, run_id="run-1"))
        writer.close()
        # A second close must not raise on already-closed handles.
        writer.close()


class TestSafeName:
    def test_a_tame_run_id_is_left_alone(self) -> None:
        assert _safe_name("state-abc_123.1") == "state-abc_123.1"

    def test_path_separators_and_drive_colons_are_neutralised(self) -> None:
        # The hard boundary: a run id can never steer the file out of trace_dir.
        # Dots are safe on both platforms and survive; the separators do not.
        assert _safe_name("a/b\\c") == "a_b_c"
        assert _safe_name("C:\\runs\\x") == "C__runs_x"
        assert "/" not in _safe_name("../../etc/passwd")
        assert "\\" not in _safe_name("..\\..\\secret")

    def test_an_empty_run_id_falls_back(self) -> None:
        assert _safe_name("") == _UNKNOWN_RUN
