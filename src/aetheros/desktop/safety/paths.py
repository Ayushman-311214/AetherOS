"""
Path validation for the filesystem and application tools.

A model that can write and delete files is one bad inference away from
``delete_file("C:\\Windows\\System32")``. This module is the single place that
decides whether a path may be read, written, or deleted, so that decision cannot
be re-implemented (and re-broken) per tool.

Three separate concerns are enforced here, and they are not the same rule:

Protected locations
    OS and installed-program directories. Writable by an administrator, and
    catastrophic to touch. Blocked for write and delete, allowed for read,
    because listing ``C:\\Windows`` is a reasonable thing for an agent to do and
    corrupting it is not.

Secret-bearing files
    ``.env``, private keys, credential stores. Blocked for *read* as well, which
    is the unusual one: a tool result travels to the LLM provider, so
    ``read_file(".env")`` would ship every API key in this project off the
    machine. The rest of AetherOS is careful never to log secrets; a readable
    ``.env`` would make that care pointless.

Root confinement
    Optional. When ``DESKTOP_FILE_ROOTS`` is set, writes are confined to those
    trees regardless of everything above.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ...config.config_loader import get_settings
from ...core.errors.desktop_error import DesktopError


class PathAccess(str, Enum):
    """What the caller intends to do with the path."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


# ==============================================================
# Static rule tables
# ==============================================================

# Directory *names* that are protected wherever they appear directly under a
# drive root. Matched case-insensitively against resolved paths rather than
# hard-coded to C: because a Windows install is not always on C:, and a machine
# with the user profile on D: would otherwise be entirely unguarded.
_PROTECTED_ROOT_CHILDREN: frozenset[str] = frozenset(
    {
        "windows",
        "program files",
        "program files (x86)",
        "programdata",
        "system volume information",
        "$recycle.bin",
        "recovery",
        "perflogs",
        "boot",
    }
)

# POSIX system trees. AetherOS is Windows-first, but the tools import and run
# under pytest on Linux CI, and a guard that silently does nothing off-Windows
# is worse than no guard at all.
_PROTECTED_POSIX_PREFIXES: tuple[str, ...] = (
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/lib",
    "/proc",
    "/sbin",
    "/sys",
    "/usr",
    "/var",
)

# Exact filenames that carry credentials. Checked case-insensitively against the
# final path component.
_SECRET_FILENAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        ".netrc",
        "_netrc",
        ".pgpass",
        ".htpasswd",
        "credentials",
        "credentials.json",
        "client_secret.json",
        "service-account.json",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        ".git-credentials",
        "secrets.yaml",
        "secrets.yml",
        "secrets.json",
    }
)

# Suffixes that are almost always key material.
_SECRET_SUFFIXES: tuple[str, ...] = (
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".keystore",
    ".jks",
)


@dataclass(frozen=True, slots=True)
class PathVerdict:
    """
    The outcome of validating one path against one intended access.

    Returned rather than raised by :meth:`PathGuard.inspect` so the health check
    and the ``dry_run`` mode can ask "would this be allowed?" without triggering
    an exception, and so the reason can be reported to the model verbatim.
    """

    path: Path
    access: PathAccess
    allowed: bool
    reason: str | None = None


class PathGuard:
    """
    Validates filesystem paths before any tool acts on them.

    Reads its rules from configuration on every call rather than caching them at
    construction: ``get_settings`` is itself ``lru_cache``-d, so the cost is a
    dict lookup, and a guard that snapshotted its rules would ignore a policy
    change made after bootstrap.
    """

    # ==========================================================
    # Resolution
    # ==========================================================

    def resolve(self, path: str | os.PathLike[str]) -> Path:
        """
        Normalise a caller-supplied path without requiring it to exist.

        ``expanduser`` first so ``~/notes.txt`` works, then ``resolve`` to
        collapse ``..`` segments. The collapse is the security-relevant half:
        without it, ``C:\\Users\\me\\..\\..\\Windows\\System32`` would slip past
        every prefix check below.

        ``strict=False`` because write and create targets legitimately do not
        exist yet.
        """

        text = str(path).strip()

        if not text:
            raise DesktopError(
                code="INVALID_PATH",
                message="Path is empty.",
                hint="Pass an absolute or user-relative path, e.g. 'C:/Users/me/notes.txt'.",
            )

        # A NUL byte terminates the string inside the Win32 API, so
        # "safe.txt\x00C:/Windows/evil" would validate as safe.txt and act on
        # something else entirely.
        if "\x00" in text:
            raise DesktopError(
                code="INVALID_PATH",
                message="Path contains a NUL byte.",
                hint="Remove the embedded null character.",
            )

        try:
            return Path(text).expanduser().resolve(strict=False)

        except (OSError, RuntimeError) as exc:
            # RuntimeError covers an unresolvable symlink loop; OSError covers
            # an invalid drive or a name the OS rejects outright.
            raise DesktopError(
                code="INVALID_PATH",
                message=f"Path could not be resolved: {text}",
                hint="Check for invalid characters or a non-existent drive.",
                cause=exc,
            ) from exc

    # ==========================================================
    # Inspection
    # ==========================================================

    def inspect(
        self,
        path: str | os.PathLike[str],
        access: PathAccess,
    ) -> PathVerdict:
        """
        Decide whether ``access`` on ``path`` is permitted, without raising.
        """

        resolved = self.resolve(path)

        reason = self._reject_reason(resolved, access)

        return PathVerdict(
            path=resolved,
            access=access,
            allowed=reason is None,
            reason=reason,
        )

    def ensure(
        self,
        path: str | os.PathLike[str],
        access: PathAccess,
    ) -> Path:
        """
        Validate a path and return it resolved, raising if it is not permitted.

        The raise is the point: every filesystem tool calls this before touching
        the disk, so a rejected path fails before any side effect rather than
        halfway through one.
        """

        verdict = self.inspect(path, access)

        if not verdict.allowed:
            raise DesktopError(
                code="PATH_NOT_PERMITTED",
                message=(
                    f"{access.value.capitalize()} access to "
                    f"'{verdict.path}' is not permitted: {verdict.reason}"
                ),
                hint=(
                    "Choose a path outside the protected system directories, "
                    "or adjust DESKTOP_PROTECTED_PATHS / DESKTOP_FILE_ROOTS."
                ),
                context=None,
            )

        return verdict.path

    # ==========================================================
    # Individual rules
    # ==========================================================

    def _reject_reason(
        self,
        resolved: Path,
        access: PathAccess,
    ) -> str | None:
        """
        The first rule that rejects this path, or None if all of them pass.

        Ordered cheapest-and-most-severe first so the reported reason is the
        most useful one rather than whichever happened to be checked last.
        """

        if self._is_secret(resolved):
            # Applies to READ too — see the module docstring.
            return (
                "the file appears to hold credentials, and tool results are "
                "sent to the language model provider"
            )

        if access is PathAccess.READ:
            # Reading a system directory is legitimate; nothing below applies.
            return None

        if self._is_drive_root(resolved):
            return "it is a drive or filesystem root"

        if self._is_protected_system_path(resolved):
            return "it is inside a protected operating-system directory"

        if reason := self._violates_configured_protection(resolved):
            return reason

        if reason := self._violates_configured_roots(resolved):
            return reason

        return None

    def _is_drive_root(self, resolved: Path) -> bool:
        """
        True for ``C:\\``, ``\\\\server\\share`` and ``/``.

        Checked separately from the protected-directory list because deleting a
        drive root is not "inside" any protected directory — it *is* the
        directory, and ``parents`` would be empty.
        """

        return resolved == resolved.anchor or resolved.parent == resolved

    def _is_protected_system_path(self, resolved: Path) -> bool:
        """
        True when the path is a protected system tree or lives inside one.
        """

        parts = [part.lower() for part in resolved.parts]

        if len(parts) >= 2 and parts[1].rstrip("\\/") in _PROTECTED_ROOT_CHILDREN:
            return True

        if not sys.platform.startswith("win"):

            text = resolved.as_posix()

            for prefix in _PROTECTED_POSIX_PREFIXES:
                if text == prefix or text.startswith(f"{prefix}/"):
                    return True

        return False

    def _violates_configured_protection(self, resolved: Path) -> str | None:
        """
        Check the operator's own ``DESKTOP_PROTECTED_PATHS`` list.
        """

        for protected in self._configured_paths(
            get_settings().DESKTOP_PROTECTED_PATHS
        ):
            if resolved == protected or self._is_within(resolved, protected):
                return f"it is inside the protected path '{protected}'"

        return None

    def _violates_configured_roots(self, resolved: Path) -> str | None:
        """
        Enforce ``DESKTOP_FILE_ROOTS`` confinement when it is configured.
        """

        roots = self._configured_paths(get_settings().DESKTOP_FILE_ROOTS)

        if not roots:
            return None

        for root in roots:
            if resolved == root or self._is_within(resolved, root):
                return None

        allowed = ", ".join(str(root) for root in roots)

        return f"writes are confined to: {allowed}"

    # ==========================================================
    # Helpers
    # ==========================================================

    def _is_secret(self, resolved: Path) -> bool:

        name = resolved.name.lower()

        if name in _SECRET_FILENAMES:
            return True

        if name.startswith(".env."):
            # Catches .env.staging and friends without listing every variant.
            return True

        return name.endswith(_SECRET_SUFFIXES)

    def _is_within(self, candidate: Path, ancestor: Path) -> bool:
        """
        Whether ``candidate`` sits under ``ancestor``.

        ``Path.is_relative_to`` rather than string prefixing, which would treat
        ``C:\\Data2`` as inside ``C:\\Data``.
        """

        try:
            return candidate.is_relative_to(ancestor)

        except (OSError, ValueError):
            # Different drives on Windows, or an unrepresentable comparison.
            return False

    def _configured_paths(self, raw: str) -> tuple[Path, ...]:
        """
        Parse a semicolon-separated setting into resolved paths.

        A malformed entry is skipped rather than raised: an unparseable path in
        an operator's ``.env`` should not take the whole desktop subsystem down,
        and the entries that do parse still protect what they name.
        """

        paths: list[Path] = []

        for entry in raw.split(";"):

            entry = entry.strip()

            if not entry:
                continue

            try:
                paths.append(Path(entry).expanduser().resolve(strict=False))

            except (OSError, RuntimeError):
                continue

        return tuple(paths)


path_guard = PathGuard()
"""Process-wide guard. Stateless, so a single instance is safe to share."""
