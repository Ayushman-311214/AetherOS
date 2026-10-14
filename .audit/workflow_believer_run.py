"""
Phase 5 runner for Task 4: execute ONE real automation workflow against the
real desktop using ONLY the existing AetherOS automation framework.

This is an audit/execution harness (same role as .audit/vision_bench.py), NOT a
new automation framework. It:

  1. Brings up the minimal container the engine needs (config -> container ->
     events -> desktop services -> tool registry). No LLM/vision-model/network.
  2. Builds ONE Workflow with the real ``Workflow`` / ``Step`` value objects.
  3. Runs ``automation_engine.validate()`` (static, no side effects) to prove the
     workflow is well-formed against the real engine.
  4. Runs ``automation_engine.execute()`` against the REAL desktop.

Goal workflow: open YouTube in Brave and search "Believer Imagine Dragons".
The final "click the result to play it" step is expressed with the framework's
designed tool -- ``click_grounded_target`` -- which needs the vision models
(ultralytics + paddleocr). Those are absent here, so that step is expected to
fail honestly; ``stop_on_failure=False`` lets the engine attempt every step and
report each outcome rather than aborting.
"""

from __future__ import annotations

import asyncio
import json

from aetheros.bootstrap.bootstrapper import Bootstrapper
from aetheros.desktop.automation.engine import automation_engine
from aetheros.desktop.automation.workflow import Step, Workflow


SEARCH_URL = (
    "https://youtu.be/uasPNAFLucA"
)


def build_workflow() -> Workflow:
    """
    The one real workflow, built with the actual Step/Workflow API, using the
    framework's *designed* tools:

    * ``launch_application`` -- the intended way to open a named app. The search
      query is baked into the URL, so a single launch opens Brave AND lands on
      the YouTube results for "Believer Imagine Dragons".
    * ``click_grounded_target`` -- the intended way to act on a semantic on-screen
      target (the first result), instead of guessing pixels.

    ``stop_on_failure=False`` + ``continue_on_failure`` let the engine attempt
    every step and report each outcome honestly rather than aborting on the first
    environment-limited step.
    """

    return Workflow(
        name="open_youtube_believer_in_brave",
        description="Open YouTube in Brave and play Busy Chillin Official Music Video | Yuvan | Arry Gill | Fuego | Punjabi Music .",
        stop_on_failure=False,  # attempt every step; report each honestly
        steps=(
            Step(
                name="open_brave_on_youtube_search",
                tool="launch_application",
                arguments={
                    "name": "brave",
                    "args": [SEARCH_URL],
                    "wait_for_window": False,
                    "confirm": True,  # launch_application is MEDIUM_RISK-gated
                },
                wait_after=8.0,
                continue_on_failure=True,
            ),
            Step(
                name="play_first_believer_result",
                tool="click_grounded_target",
                arguments={
                    "target": "the first Believer by Imagine Dragons video result"
                },
                continue_on_failure=True,
            ),
        ),
    )



def brave_windows() -> list[str]:
    """Ground truth from the real desktop: titles of visible Brave windows."""

    import win32gui

    found: list[str] = []

    def _cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title and ("Brave" in title or "YouTube" in title):
                found.append(title)

    win32gui.EnumWindows(_cb, None)
    return found


async def main() -> None:
    boot = Bootstrapper()

    await boot._bootstrap_config()
    await boot._bootstrap_logging()
    await boot._bootstrap_container()
    await boot._bootstrap_events()
    await boot._bootstrap_desktop()
    await boot._bootstrap_vision()
    await boot._bootstrap_tools()

    workflow = build_workflow()

    print("=== STATIC VALIDATION (automation_engine.validate) ===")
    validation = await automation_engine.validate(workflow)
    print(json.dumps(validation.to_dict(), indent=2, default=str))

    print("\n=== REAL EXECUTION (automation_engine.execute) ===")
    result = await automation_engine.execute(workflow)
    print(json.dumps(result.to_dict(), indent=2, default=str))

    print("\n=== GROUND TRUTH: Brave/YouTube windows on the real desktop ===")
    print(json.dumps(brave_windows(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
