"""
Application tools.

These are the tools a model reaches for first -- "open Notepad", "is Chrome
running", "close the editor" -- and they are deliberately name-based. A pid is not
something a model knows, and the process tools already cover the case where it
does.

Two things separate them from the process tools underneath:

* **Launching waits for a window by default.** Returning as soon as the process
  exists is technically correct and practically useless: the next step types into
  whatever had focus before. The wait is bounded and its outcome is reported, so a
  slow application is visible rather than silently assumed.
* **Closing and terminating are different tools, not a flag.** ``close_application``
  goes through the windows, which lets the application prompt about unsaved work.
  ``terminate_application`` does not, and says so. Collapsing them into one call
  with ``force=true`` makes the destructive path the easy one to reach by accident.
"""

from __future__ import annotations

from typing import Any

from ...core.container import container
from ...tools import tool

from ..safety.policy import RiskLevel, safety_policy

from .controller import ApplicationService


async def _service() -> ApplicationService:

    return container.resolve(ApplicationService)


# ==============================================================
# Launching
# ==============================================================


@tool(
    category="desktop.application",
    description=(
        "Launch an application by name and wait for its window. Accepts a "
        "friendly name ('notepad', 'calculator', 'chrome'), an executable name, "
        "or a full path; installed applications not on PATH are found through the "
        "registry. Returns the new window when one appears within timeout, and "
        "window_appeared=false with a note when it does not -- which means the "
        "application is slow or has no window, not that the launch failed. Do not "
        "trust pid as the application's identity: many applications hand off to a "
        "second process and the launcher exits immediately. Set "
        "wait_for_window=false only when the program has no UI."
    ),
)
async def launch_application(
    name: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    wait_for_window: bool = True,
    timeout: float = 15.0,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"launch_application({name})",
        RiskLevel.MEDIUM_RISK,
        confirmed=confirm,
    )

    applications = await _service()

    return await applications.launch(
        name,
        args=args,
        cwd=cwd,
        wait_for_window=wait_for_window,
        timeout=timeout,
    )


@tool(
    category="desktop.application",
    description=(
        "Open a URL in the default browser. Only http, https and mailto URLs are "
        "accepted. pid comes back null on purpose: the browser is usually already "
        "running, so the new tab belongs to a process this call did not create -- "
        "use list_windows or wait_for_window to find the resulting window."
    ),
)
async def launch_url(
    url: str,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"launch_url({url})",
        RiskLevel.MEDIUM_RISK,
        confirmed=confirm,
    )

    applications = await _service()

    return await applications.launch_url(url)


# ==============================================================
# State
# ==============================================================


@tool(
    category="desktop.application",
    description=(
        "Check whether an application is running, by name. Returns running=false "
        "rather than failing, so this is the safe way to confirm something "
        "started or stopped. process_count is often greater than one: browsers and "
        "editors run many processes, and all of them are the same application."
    ),
)
async def is_application_running(name: str) -> dict[str, Any]:

    applications = await _service()

    return await applications.is_running(name)


@tool(
    category="desktop.application",
    description=(
        "Get the processes and windows belonging to an application, with "
        "total_memory_usage summed across its processes. window_count=0 with "
        "running=true means it is running without a visible window, which is "
        "normal for background applications and also what a still-starting "
        "application looks like."
    ),
)
async def get_application_info(name: str) -> dict[str, Any]:

    applications = await _service()

    return await applications.info(name)


@tool(
    category="desktop.application",
    description=(
        "Wait until an application is running, then return its pids. Use this "
        "instead of a fixed sleep after launching something. Fails with a timeout "
        "error if it never appears. Note that this waits for the process, not the "
        "window -- use wait_for_window when the next step needs the UI. The "
        "timeout is capped at 120 seconds."
    ),
)
async def wait_for_application(
    name: str,
    timeout: float = 15.0,
) -> dict[str, Any]:

    applications = await _service()

    return await applications.wait_for(name, timeout=timeout)


# ==============================================================
# Closing
# ==============================================================


@tool(
    category="desktop.application",
    description=(
        "Ask an application to close, through its windows, so it can prompt about "
        "unsaved work and shut down normally. Prefer this over "
        "terminate_application. windows_remaining greater than zero usually means "
        "a save prompt is waiting -- that is the application behaving correctly, "
        "not a failure; handle the prompt and check again. still_running reports "
        "whether any of its processes survived, which is normal for applications "
        "that keep a background process."
    ),
)
async def close_application(
    name: str,
    timeout: float = 10.0,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"close_application({name})",
        RiskLevel.MEDIUM_RISK,
        confirmed=confirm,
    )

    applications = await _service()

    return await applications.close(name, timeout=timeout)


@tool(
    category="desktop.application",
    description=(
        "Stop every process belonging to an application immediately. Unsaved work "
        "is lost: there is no prompt and no shutdown sequence, so use "
        "close_application first and come here only if that reported the "
        "application still running. Each process's outcome is listed separately, "
        "and fully_stopped=false means some survived -- protected system processes "
        "are refused outright. force=true skips even the request to exit and can "
        "leave files on disk half-written."
    ),
)
async def terminate_application(
    name: str,
    force: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"terminate_application({name}, force={force})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
    )

    applications = await _service()

    return await applications.terminate(name, force=force)


@tool(
    category="desktop.application",
    description=(
        "Stop an application and start it again, returning what was stopped and "
        "what was launched. The launch target is resolved before anything is "
        "stopped, so a name that cannot be relaunched fails without leaving the "
        "application closed. Unsaved work is lost -- this terminates rather than "
        "asking politely. An application that is not running is simply launched."
    ),
)
async def restart_application(
    name: str,
    timeout: float = 15.0,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"restart_application({name})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
    )

    applications = await _service()

    return await applications.restart(name, timeout=timeout)
