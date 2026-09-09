from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .context import TaskContext
from .state import TaskStatus


@dataclass
class Task:
    id: str
    goal: str

    status: TaskStatus = TaskStatus.CREATED

    context: TaskContext | None = None

    plan_id: str | None = None

    current_step_id: str | None = None

    error: str | None = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.context is None:
             self.context = TaskContext(
                user_goal=self.goal
            )

    def update_timestamp(self) -> None:
        self.updated_at = datetime.now(timezone.utc)