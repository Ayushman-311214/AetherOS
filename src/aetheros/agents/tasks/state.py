from enum import Enum


class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    READY = "ready"
    EXECUTING = "executing"
    OBSERVING = "observing"
    EVALUATING = "evaluating"
    REPLANNING = "replanning"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"