from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskContext:
    user_goal: str

    current_state: dict[str, Any] = field(default_factory=dict)

    observations: list[dict[str, Any]] = field(default_factory=list)

    tool_results: list[dict[str, Any]] = field(default_factory=list)

    completed_steps: list[str] = field(default_factory=list)

    failed_steps: list[str] = field(default_factory=list)

    important_facts: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    def add_observation(self, observation: dict[str, Any]) -> None:
        self.observations.append(observation)

    def add_tool_result(self, result: dict[str, Any]) -> None:
        self.tool_results.append(result)

    def mark_step_completed(self, step_id: str) -> None:
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)

    def mark_step_failed(self, step_id: str) -> None:
        if step_id not in self.failed_steps:
            self.failed_steps.append(step_id)

    def set_fact(self, key: str, value: Any) -> None:
        self.important_facts[key] = value