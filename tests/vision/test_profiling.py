"""
Tests for the opt-in vision profiler.

The contract these pin, from §11 of the vision-optimisation spec:

- disabled (the default): ``stage`` is a true no-op -- it records nothing and
  takes no timing, so production behaviour is byte-for-byte unchanged;
- enabled: each stage's wall-clock is measured and accumulated into the
  supplied :class:`StageTimings`, with repeated stages summed rather than
  overwritten (so duplicate work is visible, not hidden).
"""

from __future__ import annotations

import time

from aetheros.vision.profiling import (
    StageTimings,
    VisionProfiler,
    get_profiler,
)


class TestStageTimings:

    def test_record_sums_repeated_stages(self) -> None:
        t = StageTimings()
        t.record("ocr", 10.0)
        t.record("ocr", 5.0)

        # Summed, not overwritten -- two OCR passes in one request should show
        # as the total work done, which is the point of profiling.
        assert t.stages["ocr"] == 15.0

    def test_as_dict_rounds(self) -> None:
        t = StageTimings()
        t.record("capture", 1.23456)

        assert t.as_dict() == {"capture": 1.23}

    def test_total_ms_sums_all_stages(self) -> None:
        t = StageTimings()
        t.record("capture", 2.0)
        t.record("ocr", 3.0)

        assert t.total_ms == 5.0


class TestDisabledProfilerIsANoop:

    def test_stage_records_nothing_when_disabled(self) -> None:
        profiler = VisionProfiler(enabled=False)
        timings = StageTimings()

        with profiler.stage("ocr", timings):
            pass

        assert profiler.enabled is False
        assert timings.stages == {}
        assert timings.as_dict() == {}

    def test_stage_yields_the_body_when_disabled(self) -> None:
        profiler = VisionProfiler(enabled=False)
        ran = []

        with profiler.stage("ocr"):
            ran.append(True)

        assert ran == [True]


class TestEnabledProfilerRecords:

    def test_stage_records_a_positive_duration(self) -> None:
        profiler = VisionProfiler(enabled=True)
        timings = StageTimings()

        with profiler.stage("work", timings):
            time.sleep(0.005)

        assert "work" in timings.stages
        # Slept ~5ms; assert it recorded a real, non-trivial duration without
        # pinning an exact number a slow CI box could miss.
        assert timings.stages["work"] >= 1.0

    def test_stage_without_timings_still_runs_the_body(self) -> None:
        profiler = VisionProfiler(enabled=True)
        ran = []

        # timings=None: the block must still execute and time cleanly, it just
        # has nowhere to accumulate.
        with profiler.stage("work"):
            ran.append(True)

        assert ran == [True]

    def test_timing_spans_an_exception_and_still_records(self) -> None:
        profiler = VisionProfiler(enabled=True)
        timings = StageTimings()

        try:
            with profiler.stage("boom", timings):
                raise RuntimeError("stage failed")
        except RuntimeError:
            pass

        # finally-block recording means a failed stage is still measured.
        assert "boom" in timings.stages


class TestGetProfiler:

    def test_reads_flag_from_settings(self, monkeypatch) -> None:
        import aetheros.vision.profiling as profiling

        class _S:
            VISION_PROFILE = True

        monkeypatch.setattr(profiling, "get_settings", lambda: _S())

        assert get_profiler().enabled is True
