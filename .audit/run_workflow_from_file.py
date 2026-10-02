"""
Run a workflow defined in a JSON file THROUGH the run_workflow tool.

This demonstrates the exact mental model:
  1. the automation is authored in a file (notepad_clipboard_demo.json),
  2. and run manually via the run_workflow tool -- the same tool the LLM calls.

The tool itself (desktop.automation.run_workflow) parses the JSON steps with
Step.from_dict, builds a Workflow, and hands it to automation_engine.execute.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from aetheros.bootstrap.bootstrapper import Bootstrapper
from aetheros.desktop.automation.tools import run_workflow


async def main(spec_path: str) -> None:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))

    boot = Bootstrapper()
    await boot._bootstrap_config()
    await boot._bootstrap_logging()
    await boot._bootstrap_container()
    await boot._bootstrap_events()
    await boot._bootstrap_desktop()
    await boot._bootstrap_tools()

    # Manual run via the run_workflow tool -- identical call the LLM would make.
    result = await run_workflow(
        name=spec["name"],
        steps=spec["steps"],
        description=spec.get("description", ""),
        stop_on_failure=spec.get("stop_on_failure", True),
        rollback_on_failure=spec.get("rollback_on_failure", False),
        dry_run=spec.get("dry_run", False),
    )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else ".audit/notepad_clipboard_demo.json"
    asyncio.run(main(path))
