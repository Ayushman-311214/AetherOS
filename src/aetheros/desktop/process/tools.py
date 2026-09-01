"""
Process and command tools.

Risk is graded rather than uniform, because these tools are not equally dangerous
and treating them as if they were would either block ordinary work or wave through
the things that need a decision:

* Reading -- listing, inspecting, existence, waiting -- is ``SAFE``. It changes
  nothing.
* Launching a program is ``MEDIUM_RISK``. It starts something, but starting the
  wrong thing is recoverable.
* Terminating, killing and restarting are ``HIGH_RISK``. They destroy unsaved work
  in whatever they stop, and there is no undo.
* Shell execution requires the ``SHELL`` capability, off unless configuration
  enables it. A shell string can be several commands, and anything interpolated
  into it can add more.

Backing all of that, the psutil backend refuses to stop critical system processes,
this process, or its parent -- regardless of what the policy layer decides.
Confirmation protects against a caller who means something slightly different; the
backend guard protects against a caller who means exactly what they said and is
wrong about what it does.
"""

from __future__ import annotations

from typing import Any

from ...core.container import container
from ...tools import tool

from ..safety.policy import Capability, RiskLevel, safety_policy

from .controller import ProcessService
from .terminal import TerminalService

# How many processes a bare list_processes returns. A live desktop runs 200-400,
# and returning all of them with eight fields each fills the model's context with
# service hosts it will never act on. The count is always exact; the list is
# capped, and says so.
_DEFAULT_LIMIT = 40


async def _processes() -> ProcessService:

    return container.resolve(ProcessService)


async def _terminal() -> TerminalService:

    return container.resolve(TerminalService)


# ==============================================================
# Discovery
# ==============================================================


@tool(
    category="desktop.process",
    description=(
        "List running processes. Pass name to filter (case-insensitive "
        "substring, with or without '.exe') and get every match; without a "
        "filter, returns the largest processes by memory up to limit. Each entry "
        "has pid, name, executable, status, cpu_percent, memory_usage, "
        "created_at and username; fields the current user may not read come back "
        "as null. total always reports the true count even when the list is "
        "capped."
    ),
)
async def list_processes(
    name: str | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> dict[str, Any]:

    processes = await _processes()

    if name:

        matches = await processes.find_by_name(name)

        return {
            "filter": name,
            "total": len(matches),
            "returned": len(matches),
            "truncated": False,
            "processes": matches,
        }

    everything = await processes.list_processes()

    cap = max(1, min(limit, 200))

    # Sorted by memory so the cap keeps the processes worth looking at rather
    # than whichever ones happen to have low pids. None sorts last.
    ordered = sorted(
        everything,
        key=lambda entry: entry.get("memory_usage") or 0,
        reverse=True,
    )

    return {
        "filter": None,
        "total": len(everything),
        "returned": min(cap, len(ordered)),
        "truncated": len(ordered) > cap,
        "processes": ordered[:cap],
    }


@tool(
    category="desktop.process",
    description=(
        "Get everything readable about one process by pid: name, executable, "
        "status, cpu_percent, memory_usage in bytes, created_at as a unix "
        "timestamp, and username. cpu_percent is 0.0 on the first reading for a "
        "process -- it is measured as a change between two samples, so call twice "
        "if the value matters."
    ),
)
async def get_process_info(pid: int) -> dict[str, Any]:

    processes = await _processes()

    return await processes.info(pid)


@tool(
    category="desktop.process",
    description=(
        "Check whether a process is running, by pid or by name. Returns "
        "running=false rather than failing, so this is the safe way to confirm "
        "something stopped. A process that has exited but whose status nobody "
        "collected counts as not running."
    ),
)
async def process_exists(
    pid: int | None = None,
    name: str | None = None,
) -> dict[str, Any]:

    processes = await _processes()

    if pid is not None:
        return {"pid": pid, "running": await processes.is_running(pid)}

    if not name:
        return {
            "running": False,
            "error": "Pass either pid or name.",
        }

    matches = await processes.find_by_name(name)

    return {
        "name": name,
        "running": bool(matches),
        "count": len(matches),
        "pids": [entry["pid"] for entry in matches],
    }


# ==============================================================
# Launching
# ==============================================================


@tool(
    category="desktop.process",
    description=(
        "Start a program in the background and return its pid. The program keeps "
        "running after this returns; its output is not captured, so use "
        "execute_command instead when you need to read what it printed. Pass "
        "args as a list rather than putting arguments in command -- command is "
        "not split, so a path containing spaces works only that way. No shell is "
        "involved: characters like && and | become literal arguments."
    ),
)
async def start_process(
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"start_process({command})",
        RiskLevel.MEDIUM_RISK,
        confirmed=confirm,
    )

    processes = await _processes()

    pid = await processes.start(
        [command, *args] if args else command,
        cwd=cwd,
    )

    return {
        "pid": pid,
        "command": command,
        "args": args or [],
        # Read back: a process can be created and exit immediately, and a bare
        # pid would look like a success either way.
        "running": await processes.is_running(pid),
    }


# ==============================================================
# Stopping
# ==============================================================


@tool(
    category="desktop.process",
    description=(
        "Stop a process by pid: asks it to exit, and forces it only if asking "
        "did not work. Unsaved work in the program is lost -- to let the user "
        "save, use close_window instead. The result reports exited and forced, "
        "read back from the system rather than assumed. Critical system "
        "processes, this agent's own process and its parent are always refused."
    ),
)
async def stop_process(
    pid: int,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"stop_process(pid={pid})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
    )

    processes = await _processes()

    return await processes.stop(pid)


@tool(
    category="desktop.process",
    description=(
        "Ask a process to exit, without escalating to a forced kill. Reports "
        "exited=false when the process ignored it, which is the honest answer "
        "and not an error -- follow with kill_process if it must go. Unsaved "
        "work is lost."
    ),
)
async def terminate_process(
    pid: int,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"terminate_process(pid={pid})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
    )

    processes = await _processes()

    return await processes.terminate(pid)


@tool(
    category="desktop.process",
    description=(
        "Force a process to exit immediately, with no chance for it to save or "
        "clean up. Use only after terminate_process has been given time and "
        "reported exited=false. Data loss and corrupted files on disk are both "
        "possible outcomes."
    ),
)
async def kill_process(
    pid: int,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"kill_process(pid={pid})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
    )

    processes = await _processes()

    return await processes.kill(pid)


@tool(
    category="desktop.process",
    description=(
        "Stop a process and start its executable again, returning the new pid. "
        "Its command line is captured first: if that cannot be read, nothing is "
        "stopped, because a restart that terminates and then cannot relaunch is "
        "worse than a refusal. Unsaved work is lost."
    ),
)
async def restart_process(
    pid: int,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"restart_process(pid={pid})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
    )

    processes = await _processes()

    return await processes.restart(pid)


# ==============================================================
# Waiting
# ==============================================================


@tool(
    category="desktop.process",
    description=(
        "Wait until at least one process with this name is running, then return "
        "the matches. Use this after starting an application instead of a fixed "
        "sleep. Fails with a timeout error if nothing appears. The timeout is "
        "capped at 300 seconds."
    ),
)
async def wait_for_process(
    name: str,
    timeout: float = 30.0,
) -> dict[str, Any]:

    processes = await _processes()

    return await processes.wait_for_process(name, timeout=timeout)


@tool(
    category="desktop.process",
    description=(
        "Wait until a process exits, identified by pid. Use this after asking a "
        "program to close, to confirm it actually went before continuing. Fails "
        "with a timeout error if it is still running when time runs out. The "
        "timeout is capped at 300 seconds."
    ),
)
async def wait_for_process_exit(
    pid: int,
    timeout: float = 30.0,
) -> dict[str, Any]:

    processes = await _processes()

    return await processes.wait_for_exit(pid, timeout=timeout)


# ==============================================================
# Command execution
# ==============================================================


@tool(
    category="desktop.process",
    description=(
        "Run a program, wait for it, and return exit_code, stdout, stderr and "
        "duration. Check exit_code: a non-zero code means the command ran and "
        "failed, and succeeded=false says so explicitly -- do not read stdout as "
        "success on its own. Pass arguments in args rather than inside command; "
        "command is split on spaces, so a path containing spaces must go through "
        "args. No shell, so pipes, redirection, && and shell builtins like 'dir' "
        "do not work -- use execute_shell for those. Output over 20000 "
        "characters is truncated, and stdout_truncated says when. The timeout is "
        "capped at 600 seconds."
    ),
)
async def execute_command(
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    timeout: float = 60.0,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"execute_command({command})",
        RiskLevel.MEDIUM_RISK,
        confirmed=confirm,
    )

    terminal = await _terminal()

    result = await terminal.run(
        [command, *args] if args else command,
        cwd=cwd,
        timeout=timeout,
    )

    return result.to_dict()


@tool(
    category="desktop.process",
    description=(
        "Run a command string through the system shell, so pipes, redirection, "
        "&&, ; and builtins all work. Disabled unless configuration enables "
        "shell execution, because one string can be several commands. Prefer "
        "execute_command for anything that does not need shell syntax. Check "
        "exit_code and succeeded in the result: a non-zero code means the "
        "command ran and failed. The timeout is capped at 600 seconds."
    ),
)
async def execute_shell(
    command: str,
    cwd: str | None = None,
    timeout: float = 60.0,
    confirm: bool = False,
) -> dict[str, Any]:

    safety_policy.require(
        f"execute_shell({command})",
        RiskLevel.HIGH_RISK,
        confirmed=confirm,
        capability=Capability.SHELL,
    )

    terminal = await _terminal()

    result = await terminal.run_shell(
        command,
        cwd=cwd,
        timeout=timeout,
    )

    return result.to_dict()
