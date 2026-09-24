from __future__ import annotations

import pytest

from aetheros.agents.observation import (
    Observation,
    ObservationLog,
    ObservationSource,
    browser_observation,
    screenshot_observation,
    tool_observation,
    vision_observation,
)
from aetheros.agents.state import Observation as StateObservation
from aetheros.core.errors.agent_error import AgentError
from aetheros.tools.executor import ToolExecutionResult
from aetheros.agents.state import ToolResultRecord
from aetheros.vision.models import Detection, TemplateMatch, TextBlock


# ==============================================================
# Tool observations
# ==============================================================

def test_tool_observation_from_execution_result():
    result = ToolExecutionResult(name="read_price", ok=True, value={"px": 100})

    obs = tool_observation(result)

    assert obs.source is ObservationSource.TOOL
    assert obs.data["tool"] == "read_price"
    assert obs.data["ok"] is True
    assert obs.data["value"] == {"px": 100}
    assert "read_price" in obs.description
    # A tool result carries no inherent confidence.
    assert obs.confidence is None


def test_tool_observation_from_result_record_keeps_failure():
    record = ToolResultRecord(
        call_id="c1",
        name="open_chart",
        ok=False,
        content="",
        error="window not found",
        error_type="DesktopError",
    )

    obs = tool_observation(record)

    assert obs.source is ObservationSource.TOOL
    assert obs.data["ok"] is False
    assert obs.data["error"] == "window not found"
    assert "failed" in obs.description


def test_tool_observation_rejects_unrelated_object():
    with pytest.raises(TypeError):
        tool_observation({"tool": "nope"})


# ==============================================================
# Screenshot observations
# ==============================================================

def test_screenshot_observation_records_artifact_and_size():
    obs = screenshot_observation(
        path="/tmp/frame.png",
        width=1920,
        height=1080,
    )

    assert obs.source is ObservationSource.SCREENSHOT
    assert obs.artifact_path == "/tmp/frame.png"
    assert obs.data["width"] == 1920
    assert obs.data["height"] == 1080
    assert "region" not in obs.data


def test_screenshot_observation_includes_region_when_given():
    obs = screenshot_observation(
        path="/tmp/region.png",
        width=200,
        height=100,
        region=(10, 20, 200, 100),
    )

    assert obs.data["region"] == {
        "left": 10,
        "top": 20,
        "width": 200,
        "height": 100,
    }


# ==============================================================
# Vision observations
# ==============================================================

def test_vision_observation_averages_confidence_and_serialises_readings():
    blocks = [
        TextBlock(text="BUY", confidence=0.9, left=0, top=0, right=10, bottom=5),
        TextBlock(text="SELL", confidence=0.7, left=0, top=6, right=10, bottom=11),
    ]
    detections = [
        Detection(label="button", confidence=0.8, left=0, top=0, right=4, bottom=4),
    ]

    obs = vision_observation(
        text_blocks=blocks,
        detections=detections,
        artifact_path="/tmp/frame.png",
    )

    assert obs.source is ObservationSource.VISION
    assert obs.artifact_path == "/tmp/frame.png"
    assert len(obs.data["text_blocks"]) == 2
    assert len(obs.data["detections"]) == 1
    assert obs.confidence == pytest.approx((0.9 + 0.7 + 0.8) / 3)
    # Description must not leak recognised text (a screen may hold a secret).
    assert "BUY" not in obs.description
    assert "SELL" not in obs.description


def test_vision_observation_with_no_readings_has_no_confidence():
    obs = vision_observation()

    assert obs.confidence is None
    assert obs.data["text_blocks"] == []
    assert obs.data["matches"] == []


def test_vision_observation_accepts_template_matches():
    matches = [TemplateMatch(x=0, y=0, width=10, height=10, confidence=0.95)]

    obs = vision_observation(matches=matches)

    assert len(obs.data["matches"]) == 1
    assert obs.confidence == pytest.approx(0.95)


# ==============================================================
# Browser seam
# ==============================================================

def test_browser_observation_seam():
    obs = browser_observation(
        url="https://tradingview.com",
        title="RELIANCE",
        data={"symbol": "RELIANCE"},
    )

    assert obs.source is ObservationSource.BROWSER
    assert obs.data["url"] == "https://tradingview.com"
    assert obs.data["title"] == "RELIANCE"
    assert obs.data["symbol"] == "RELIANCE"


# ==============================================================
# Serialization
# ==============================================================

def test_observation_round_trips_through_dict():
    obs = Observation(
        source=ObservationSource.VISION,
        data={"detections": 3},
        description="three things",
        artifact_path="/tmp/x.png",
        confidence=0.5,
    )

    restored = Observation.from_dict(obs.to_dict())

    assert restored == obs


def test_observation_to_dict_does_not_alias_data():
    obs = Observation(source=ObservationSource.AGENT, data={"k": [1, 2]})

    dumped = obs.to_dict()
    dumped["data"]["k"].append(3)

    # Mutating the dump must not reach the frozen observation.
    assert obs.data["k"] == [1, 2]


def test_from_dict_coerces_string_source():
    obs = Observation.from_dict({"source": "tool", "data": {"tool": "x"}})

    assert obs.source is ObservationSource.TOOL


def test_observation_bridges_to_state_observation():
    obs = tool_observation(
        ToolExecutionResult(name="read_price", ok=True, value=1)
    )

    bridged = obs.to_state_observation(iteration=4)

    assert isinstance(bridged, StateObservation)
    assert bridged.source == "tool"
    assert bridged.iteration == 4
    assert bridged.metadata["observation_id"] == obs.id


# ==============================================================
# Multiple observations
# ==============================================================

def test_observation_log_records_and_filters_by_source():
    log = ObservationLog()
    log.record(tool_observation(ToolExecutionResult(name="a", ok=True)))
    log.record(screenshot_observation(path="/tmp/s.png", width=1, height=1))
    log.record(tool_observation(ToolExecutionResult(name="b", ok=True)))

    assert len(log) == 3
    assert len(log.by_source(ObservationSource.TOOL)) == 2
    assert len(log.by_source("screenshot")) == 1


def test_observation_log_latest_is_newest_last():
    log = ObservationLog()
    first = log.record(tool_observation(ToolExecutionResult(name="a", ok=True)))
    second = log.record(tool_observation(ToolExecutionResult(name="b", ok=True)))

    assert log.latest(1) == (second,)
    assert log.latest() == (first, second)
    assert log.latest(0) == ()


def test_observation_log_round_trips():
    log = ObservationLog()
    log.record(screenshot_observation(path="/tmp/s.png", width=800, height=600))
    log.record(browser_observation(url="https://example.com"))

    restored = ObservationLog.from_dict(log.to_dict())

    assert [o.to_dict() for o in restored] == [o.to_dict() for o in log]


# ==============================================================
# Invalid observations
# ==============================================================

def test_invalid_source_is_rejected():
    with pytest.raises(AgentError, match="source"):
        Observation(source="telepathy")


def test_non_dict_data_is_rejected():
    with pytest.raises(AgentError, match="data"):
        Observation(source=ObservationSource.AGENT, data=["not", "a", "dict"])


def test_confidence_out_of_range_is_rejected():
    with pytest.raises(AgentError, match="confidence"):
        Observation(source=ObservationSource.VISION, confidence=1.5)


def test_from_dict_rejects_unknown_field():
    with pytest.raises(AgentError, match="Unknown observation field"):
        Observation.from_dict(
            {"source": "tool", "data": {}, "mystery": 1}
        )


def test_from_dict_requires_source():
    with pytest.raises(AgentError, match="source"):
        Observation.from_dict({"data": {}})


def test_log_rejects_non_observation_entry():
    log = ObservationLog()
    with pytest.raises(AgentError, match="Observation"):
        log.record({"source": "tool"})
