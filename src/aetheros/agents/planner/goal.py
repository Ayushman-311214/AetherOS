from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Goal:
    """
    Represents the user's objective.
    """

    instruction: str

    priority: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    completed: bool = False

    failed: bool = False