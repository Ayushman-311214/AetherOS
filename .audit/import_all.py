"""Level 1 (Import) for every module in the package.

Walks the filesystem rather than pkgutil: half of AetherOS's subdirectories have
no __init__.py, and pkgutil.walk_packages both skips those and silently swallows
ImportError while recursing, so it reported 34 of the repository's modules.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

SKIP_DIRS = {
    "__pycache__",
    ".cache",
    "logs",
    "tests",
    "scripts",
    "data",
}

names: list[str] = []

for path in sorted((SRC / "aetheros").rglob("*.py")):

    rel = path.relative_to(SRC)

    if any(part in SKIP_DIRS for part in rel.parts):
        continue

    parts = list(rel.with_suffix("").parts)

    if parts[-1] == "__init__":
        parts.pop()

    names.append(".".join(parts))

failed: list[tuple[str, str]] = []

for name in names:
    try:
        importlib.import_module(name)
    except BaseException:  # noqa: BLE001 - reporting, not swallowing
        line = traceback.format_exc().strip().splitlines()[-1]
        failed.append((name, line))

print(f"modules scanned : {len(names)}")
print(f"import failures : {len(failed)}")
print()

for name, line in failed:
    print(f"  [FAIL] {name}")
    print(f"         {line}")
