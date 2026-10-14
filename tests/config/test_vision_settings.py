"""
Configuration-layer tests for the Vision performance settings.

These pin the contract the vision-optimisation task named: every new
``VISION_*`` knob has a default that preserves the historical behaviour, both
env spellings (``AETHEROS_VISION_*`` and the bare name) resolve, and an
out-of-range value fails *here*, at configuration load, rather than degrading a
vision run at some unpredictable later point.

Every construction passes ``_env_file=None`` so the developer's local ``.env``
cannot leak a value in and make a case pass or fail for the wrong reason.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aetheros.config.settings import Settings

_VISION_ENV = (
    "AETHEROS_VISION_PROFILE", "VISION_PROFILE",
    "AETHEROS_VISION_WIDTH", "VISION_WIDTH",
    "AETHEROS_VISION_FRAME_TTL_MS", "VISION_FRAME_TTL_MS",
    "AETHEROS_VISION_MODEL", "VISION_MODEL",
    "AETHEROS_VISION_DETECTION_CONFIDENCE", "VISION_DETECTION_CONFIDENCE",
    "AETHEROS_VISION_DETECTION_IMGSZ", "VISION_DETECTION_IMGSZ",
    "AETHEROS_VISION_DETECTION_DEVICE", "VISION_DETECTION_DEVICE",
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _VISION_ENV:
        monkeypatch.delenv(name, raising=False)


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


class TestDefaultsPreserveHistoricalBehaviour:
    """The defaults must reproduce the pre-optimisation behaviour exactly."""

    def test_profiling_off(self) -> None:
        assert _settings().VISION_PROFILE is False

    def test_width_zero_means_full_resolution(self) -> None:
        # 0 == no downscale == full native resolution == old behaviour.
        assert _settings().VISION_WIDTH == 0

    def test_frame_ttl_default(self) -> None:
        assert _settings().VISION_FRAME_TTL_MS == 300

    def test_model_default_is_nano(self) -> None:
        assert _settings().VISION_MODEL == "yolo11n.pt"

    def test_detection_confidence_default(self) -> None:
        assert _settings().VISION_DETECTION_CONFIDENCE == pytest.approx(0.25)

    def test_detection_imgsz_default(self) -> None:
        assert _settings().VISION_DETECTION_IMGSZ == 640

    def test_detection_device_default_is_auto(self) -> None:
        # Empty string == "auto": CUDA if available else CPU (resolved later).
        assert _settings().VISION_DETECTION_DEVICE == ""


class TestValidValues:

    def test_profile_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AETHEROS_VISION_PROFILE", "true")
        assert _settings().VISION_PROFILE is True

    def test_width_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AETHEROS_VISION_WIDTH", "1280")
        assert _settings().VISION_WIDTH == 1280

    def test_frame_ttl_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AETHEROS_VISION_FRAME_TTL_MS", "500")
        assert _settings().VISION_FRAME_TTL_MS == 500

    def test_frame_ttl_zero_disables_cache(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AETHEROS_VISION_FRAME_TTL_MS", "0")
        assert _settings().VISION_FRAME_TTL_MS == 0

    def test_confidence_bounds_are_inclusive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AETHEROS_VISION_DETECTION_CONFIDENCE", "1.0")
        assert _settings().VISION_DETECTION_CONFIDENCE == pytest.approx(1.0)

    def test_device_pin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AETHEROS_VISION_DETECTION_DEVICE", "cuda:0")
        assert _settings().VISION_DETECTION_DEVICE == "cuda:0"


class TestUnprefixedAliases:

    def test_bare_width(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VISION_WIDTH", "960")
        assert _settings().VISION_WIDTH == 960

    def test_bare_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VISION_MODEL", "yolo11s.pt")
        assert _settings().VISION_MODEL == "yolo11s.pt"


class TestInvalidValuesFailAtConfigLoad:

    @pytest.mark.parametrize("bad", ["-1", "-100"])
    def test_negative_width_rejected(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv("AETHEROS_VISION_WIDTH", bad)
        with pytest.raises(ValidationError):
            _settings()

    def test_negative_ttl_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AETHEROS_VISION_FRAME_TTL_MS", "-1")
        with pytest.raises(ValidationError):
            _settings()

    @pytest.mark.parametrize("bad", ["-0.1", "1.5", "2"])
    def test_confidence_out_of_range_rejected(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv("AETHEROS_VISION_DETECTION_CONFIDENCE", bad)
        with pytest.raises(ValidationError):
            _settings()

    @pytest.mark.parametrize("bad", ["32", "0", "-64"])
    def test_imgsz_below_floor_rejected(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        # ge=64: a smaller inference size is almost certainly a misconfiguration.
        monkeypatch.setenv("AETHEROS_VISION_DETECTION_IMGSZ", bad)
        with pytest.raises(ValidationError):
            _settings()
