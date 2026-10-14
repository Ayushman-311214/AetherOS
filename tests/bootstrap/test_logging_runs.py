"""
Run-directory lifecycle regression tests (spec: one process -> one run folder).

The guarantee being pinned is ``1 process -> 1 run folder -> everything in it``.
These tests reset the logging module's global state between cases (the run dir
and the configured flag are deliberately process-wide), exercise the real
``setup_logging``/``configure_handlers`` path, and assert on the filesystem:

- a single startup produces exactly one ``logs/run_<ts>_<pid>/`` folder;
- repeated logging init in one process reuses that folder (no second folder,
  no duplicate sinks);
- traces live inside the active run folder, never a top-level ``logs/traces``;
- retention keeps only the newest N *completed* runs and never deletes the
  live one, and honours a different configured count;
- run names carry the PID, so same-second restarts cannot collide.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
from loguru import logger

from aetheros.core.logging import handlers
from aetheros.core.logging import logger as logmod


@pytest.fixture()
def fresh_logging(tmp_path, monkeypatch):
    """
    Point logging at a temp root and reset all process-global run state.

    The logging modules read ``settings`` once at import, so the fixture
    overrides the bound module attributes directly -- the same seams the
    configuration feeds. Yields the temp log root and restores nothing (each
    test gets its own tmp_path and a clean global).
    """
    root = tmp_path / "logs"
    monkeypatch.setattr(handlers, "LOG_DIR", root)
    monkeypatch.setattr(handlers, "LOG_RUNS_TO_KEEP", 3)
    monkeypatch.setattr(handlers, "_ACTIVE_RUN", None)
    monkeypatch.setattr(logmod, "_CONFIGURED", False)
    yield root
    # Teardown: drop the sinks this test added so they don't leak into the
    # next test (and don't hold open files on the temp dir).
    logger.remove()
    monkeypatch.undo()


def _run_folders(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        p for p in root.iterdir() if p.is_dir() and p.name.startswith("run_")
    )


# ----------------------------------------------------------------------
# Test 1 -- a single startup creates exactly one run folder
# ----------------------------------------------------------------------


def test_one_startup_creates_one_run_folder(fresh_logging):
    run_dir = logmod.setup_logging()
    assert run_dir is not None
    assert run_dir.parent == fresh_logging
    assert run_dir.name.startswith("run_")
    # One folder, holding the run's log sinks.
    folders = _run_folders(fresh_logging)
    assert len(folders) == 1
    assert folders[0] == run_dir


def test_run_folder_name_carries_the_pid(fresh_logging):
    run_dir = logmod.setup_logging()
    # run_YYYYMMDD_HHMMSS_PID -- the PID suffix prevents same-second collisions.
    suffix = run_dir.name.rsplit("_", 1)[-1]
    assert suffix == str(os.getpid())


# ----------------------------------------------------------------------
# Test 2 -- repeated init in one process reuses the same folder
# ----------------------------------------------------------------------


def test_repeated_setup_reuses_one_run_folder(fresh_logging):
    first = logmod.setup_logging()
    sinks_after_first = len(logger._core.handlers)
    for _ in range(3):
        again = logmod.setup_logging()
        assert again == first
    # Still one folder and one set of sinks -- no duplicate init.
    assert len(_run_folders(fresh_logging)) == 1
    assert len(logger._core.handlers) == sinks_after_first


def test_get_logger_does_not_create_a_second_run(fresh_logging):
    first = logmod.get_logger("a")
    run_dir = handlers.current_run_dir()
    # get_logger lazily configures once; further calls must not mint folders.
    logmod.get_logger("b")
    logmod.get_logger("c")
    assert handlers.current_run_dir() == run_dir
    assert len(_run_folders(fresh_logging)) == 1


# ----------------------------------------------------------------------
# Test 3 -- traces live inside the active run folder
# ----------------------------------------------------------------------


def test_trace_dir_is_inside_the_run(fresh_logging):
    run_dir = logmod.setup_logging()
    td = logmod.trace_dir()
    assert td == run_dir / "traces"
    assert str(td).startswith(str(run_dir))
    # And it is never the shared top-level folder.
    assert td != fresh_logging / "traces"


# ----------------------------------------------------------------------
# Test 4 / 5 -- retention honours the configured count and spares the live run
# ----------------------------------------------------------------------


@pytest.mark.parametrize("keep", [3, 5])
def test_retention_keeps_only_the_newest_n_runs(fresh_logging, keep):
    monkey_keep = keep
    handlers.LOG_RUNS_TO_KEEP = monkey_keep

    # Seed more runs than the limit, oldest first by mtime.
    for i in range(keep + 2):
        p = fresh_logging / f"run_2020010{i}_000000_{1000 + i}"
        p.mkdir(parents=True)
        os.utime(p, (1_000_000 + i, 1_000_000 + i))

    # A new live run is created, then retention runs.
    live = handlers.create_run_directory()
    handlers._ACTIVE_RUN = live
    handlers.cleanup_old_runs(keep=monkey_keep, current=live)

    survivors = _run_folders(fresh_logging)
    assert len(survivors) == monkey_keep
    assert live in survivors  # the active run is never deleted


def test_retention_never_deletes_the_current_run(fresh_logging):
    handlers.LOG_RUNS_TO_KEEP = 1
    # An older, completed run.
    old = fresh_logging / "run_20200101_000000_9999"
    old.mkdir(parents=True)
    os.utime(old, (1_000_000, 1_000_000))

    live = handlers.create_run_directory()
    handlers._ACTIVE_RUN = live
    # Make the live folder look older than the completed one; it must still win.
    os.utime(live, (1, 1))
    handlers.cleanup_old_runs(keep=1, current=live)

    assert live.exists()
    assert live in _run_folders(fresh_logging)


# ----------------------------------------------------------------------
# Test 6 -- distinct processes get distinct run folders (PID-tagged)
# ----------------------------------------------------------------------


def test_run_names_embed_pid_so_processes_do_not_collide(fresh_logging, monkeypatch):
    # Two "processes": same second, different PIDs -> different folders.
    monkeypatch.setattr(os, "getpid", lambda: 1111)
    a = handlers.create_run_directory()
    monkeypatch.setattr(os, "getpid", lambda: 2222)
    b = handlers.create_run_directory()
    assert a != b
    assert a.name.endswith("_1111")
    assert b.name.endswith("_2222")
