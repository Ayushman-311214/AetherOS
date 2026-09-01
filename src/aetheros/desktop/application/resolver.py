"""
Application name resolution.

The model asks for "notepad", or "calculator", or "the browser". None of those are
paths, and ``subprocess`` needs a path. Resolution happens in four steps, cheapest
and most predictable first:

1. **An explicit path**, used as given. If the caller knows the exact executable,
   nothing here should second-guess it.
2. **PATH**, via ``shutil.which``. This is what typing the name in a terminal
   would do, so it is what the caller most likely means.
3. **A small alias table** for the Windows applications that have a name everyone
   uses and an executable nobody remembers -- ``write.exe`` for WordPad,
   ``msedge.exe`` for Edge, ``taskmgr.exe`` for Task Manager.
4. **The App Paths registry**, which is how the Run dialog finds installed
   applications that are not on PATH. This is where Chrome, Firefox and most
   third-party installs live.

If all four miss, resolution fails and says which name it could not find. It does
*not* fall back to handing the string to a shell and hoping -- that turns a typo
into an arbitrary command.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ...core.errors.desktop_error import DesktopError

try:
    import winreg

    _HAVE_REGISTRY = True

except ImportError:  # pragma: no cover - non-Windows
    winreg = None  # type: ignore[assignment]

    _HAVE_REGISTRY = False


# Friendly name -> executable. Deliberately small: it covers the built-in Windows
# applications whose executable name is unguessable, and nothing else. A long
# curated list of third-party applications would go stale, and the App Paths
# lookup below finds those correctly anyway.
_ALIASES: dict[str, str] = {
    "notepad": "notepad.exe",
    "wordpad": "write.exe",
    "write": "write.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "registry editor": "regedit.exe",
    "snipping tool": "snippingtool.exe",
    "character map": "charmap.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "brave": "brave.exe",
    "vscode": "code.cmd",
    "vs code": "code.cmd",
    "visual studio code": "code.cmd",
}

# Where the Run dialog looks. Both hives, because per-user installs (which is how
# Chrome installs by default) land in HKCU and machine-wide ones in HKLM.
_APP_PATHS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"

# A URI scheme: a letter, then letters/digits/+-. , then a colon -- and at least
# two characters before the colon, so a drive letter is not mistaken for one.
_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]+:")


def _from_registry(executable: str) -> str | None:
    """
    Look one executable up in App Paths, returning its full path.

    The value is the default (unnamed) one under the key, and it is frequently
    quoted -- ``"C:\\Program Files\\...\\chrome.exe"`` -- so the quotes are
    stripped. Passing them through would make the path itself part of the
    filename.
    """

    if not _HAVE_REGISTRY:
        return None

    name = executable if executable.lower().endswith(".exe") else f"{executable}.exe"

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):

        try:
            with winreg.OpenKey(hive, rf"{_APP_PATHS}\{name}") as key:

                value, _kind = winreg.QueryValueEx(key, "")

        except (FileNotFoundError, OSError):
            continue

        if not value:
            continue

        candidate = Path(str(value).strip().strip('"'))

        if candidate.is_file():
            return str(candidate)

    return None


def is_uri(target: str) -> bool:
    """
    Whether a target is a shell URI (``ms-settings:``, ``mailto:``) rather than a
    path.

    A single-letter scheme is rejected, which is the whole subtlety here:
    ``C:\\Windows\\notepad.exe`` matches every other definition of "has a scheme"
    and must not be handed to the shell as a URI. Real schemes are two characters
    or more.
    """

    return bool(_URI_SCHEME.match(target))


def resolve_application(name: str) -> str:
    """
    Turn an application name into something that can actually be launched.

    Returns an absolute path where one was found, and otherwise the bare
    executable name -- which ``CreateProcess`` resolves against PATH itself, so a
    name that ``which`` missed for environment reasons still has a chance.

    A URI such as ``ms-settings:`` is returned unchanged: those are opened by the
    shell rather than executed, and the caller routes them accordingly.
    """

    requested = name.strip()

    if not requested:
        raise DesktopError(
            code="APPLICATION_NAME_EMPTY",
            message="No application was named.",
            hint="Pass an application name such as 'notepad', or a full path.",
        )

    # 0. A URI, which the shell opens rather than executes.
    if is_uri(requested):
        return requested

    # 1. An explicit path, honoured as given.
    direct = Path(requested).expanduser()

    if direct.is_file():
        return str(direct)

    lowered = requested.lower()

    # 2. PATH.
    found = shutil.which(requested)

    if found:
        return found

    # 3. Aliases, then PATH and the registry again for whatever the alias named.
    alias = _ALIASES.get(lowered)

    if alias:

        if is_uri(alias):
            return alias

        aliased = shutil.which(alias)

        if aliased:
            return aliased

        from_registry = _from_registry(alias)

        if from_registry:
            return from_registry

        # The alias is a real Windows executable that ``which`` can miss when
        # PATHEXT or the System32 entry is unusual. CreateProcess still finds it.
        return alias

    # 4. App Paths.
    from_registry = _from_registry(requested)

    if from_registry:
        return from_registry

    raise DesktopError(
        code="APPLICATION_NOT_FOUND",
        message=f"Could not find an application called {requested!r}.",
        hint=(
            "Pass the full path to the executable, or the exact executable name "
            "(for example 'msedge.exe'). Nothing was launched."
        ),
    )


__all__ = ["is_uri", "resolve_application"]
