"""
Configuration-layer tests for the canonical ``MAX_TOOL_CALLS`` budget.

``Settings.MAX_TOOL_CALLS`` (env ``AETHEROS_MAX_TOOL_CALLS``) is the single
source of truth for how many tool-calling iterations one agent run may take.
These tests pin the contract the task named: valid values pass through, a
missing value falls back to the documented default, and an out-of-range or
non-integer value fails *here*, at configuration load, rather than degrading a
run at some unpredictable later point.

Every construction passes ``_env_file=None`` so the developer's local ``.env``
cannot leak a value in and make a case pass or fail for the wrong reason -- the
only input is what each test sets on the environment.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aetheros.config.settings import Settings

# Both spellings the field accepts, cleared before every case so nothing from
# the ambient environment survives into a test.
_ENV_ALIASES = ("AETHEROS_MAX_TOOL_CALLS", "MAX_TOOL_CALLS")


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_ALIASES:
        monkeypatch.delenv(name, raising=False)


def _settings() -> Settings:
    # _env_file=None: read only the process environment, never the local .env.
    return Settings(_env_file=None)  # type: ignore[call-arg]


class TestValidValues:

    def test_thirty_two_is_accepted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AETHEROS_MAX_TOOL_CALLS", "32")

        assert _settings().MAX_TOOL_CALLS == 32

    def test_fifty_is_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AETHEROS_MAX_TOOL_CALLS", "50")

        assert _settings().MAX_TOOL_CALLS == 50

    def test_value_above_safety_ceilings_is_still_valid_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 100 exceeds both downstream ceilings (planner 32, loop 50). The config
        # layer accepts it; clamping to the ceiling is the consumers' job, not a
        # configuration error.
        monkeypatch.setenv("AETHEROS_MAX_TOOL_CALLS", "100")

        assert _settings().MAX_TOOL_CALLS == 100

    def test_unprefixed_alias_also_works(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MAX_TOOL_CALLS", "16")

        assert _settings().MAX_TOOL_CALLS == 16


class TestDefault:

    def test_missing_value_falls_back_to_eight(self) -> None:
        # Nothing set (the autouse fixture cleared both aliases): the historical
        # budget of 8 is preserved, so an install that never sets the variable
        # behaves exactly as before.
        assert _settings().MAX_TOOL_CALLS == 8


class TestInvalidValuesFailAtConfigLoad:

    @pytest.mark.parametrize("bad", ["0", "-1", "-5"])
    def test_non_positive_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv("AETHEROS_MAX_TOOL_CALLS", bad)

        with pytest.raises(ValidationError):
            _settings()

    @pytest.mark.parametrize("bad", ["abc", "3.5.1", ""])
    def test_non_integer_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv("AETHEROS_MAX_TOOL_CALLS", bad)

        with pytest.raises(ValidationError):
            _settings()
