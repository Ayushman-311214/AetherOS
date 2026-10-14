"""Level 1+2: import every tool module, report registration.

The module list is discovered rather than hard-coded: a hard-coded list is what
let desktop/screenshot and browser sit broken, since a module nobody imports
cannot fail loudly.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aetheros.tools.registry import tool_registry  # noqa: E402

SKIP_DIRS = {"__pycache__", ".cache", "logs", "tests", "scripts", "data"}

MODULES: list[str] = []

for path in sorted((ROOT / "src" / "aetheros").rglob("tools.py")):
    rel = path.relative_to(ROOT / "src")
    if any(part in SKIP_DIRS for part in rel.parts):
        continue
    MODULES.append(".".join(rel.with_suffix("").parts))

print("=" * 66)
print("LEVEL 1/2 — MODULE IMPORT + REGISTRATION")
print("=" * 66)

failures = 0

for mod in MODULES:
    before = tool_registry.count
    try:
        importlib.import_module(mod)
        after = tool_registry.count
        print(f"  IMPORT PASS  {mod:42} +{after - before} tools")
    except Exception as exc:
        failures += 1
        after = tool_registry.count
        print(f"  IMPORT FAIL  {mod:42} +{after - before} tools")
        print(f"      {type(exc).__name__}: {exc}")
        for line in traceback.format_exc().strip().splitlines()[-4:]:
            print(f"      | {line}")

print()
print(f"MODULES: {len(MODULES)}    IMPORT FAILURES: {failures}")
print(f"TOTAL REGISTERED: {tool_registry.count}")
print()

for cat in tool_registry.categories():
    names = sorted(t.name for t in tool_registry.by_category(cat))
    print(f"  {cat:22} {len(names):>2}  {', '.join(names)}")
