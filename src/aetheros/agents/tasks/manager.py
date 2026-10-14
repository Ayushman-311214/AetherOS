from uuid import uuid4

from .exceptions import (
    InvalidTaskStateError,
    TaskNotFoundError,
)
from .models import Task
from .state import TaskStatus


class TaskManager:

    def __init__(self, event_bus=None):
        self._tasks: dict[str, Task] = {}
        self._event_bus = event_bus

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    def create_task(
        self,
        goal: str,
        *,
        metadata: dict | None = None,
    ) -> Task:

        task = Task(
            id=f"task_{uuid4().hex[:12]}",
            goal=goal,
            metadata=metadata or {},
        )

        self._tasks[task.id] = task

        self._emit(
            "TASK_CREATED",
            task,
        )

        return task

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    def get_task(self, task_id: str) -> Task:

        task = self._tasks.get(task_id)

        if task is None:
            raise TaskNotFoundError(
                f"Task not found: {task_id}"
            )

        return task

    # ---------------------------------------------------------
    # DELETE
    # ---------------------------------------------------------

    def remove_task(self, task_id: str) -> None:

        task = self.get_task(task_id)

        del self._tasks[task.id]

    # ---------------------------------------------------------
    # STATE TRANSITIONS
    # ---------------------------------------------------------

    def set_status(
        self,
        task_id: str,
        status: TaskStatus,
    ) -> Task:

        task = self.get_task(task_id)

        self._validate_transition(
            task.status,
            status,
        )

        previous_status = task.status

        task.status = status
        task.update_timestamp()

        self._emit(
            "TASK_STATUS_CHANGED",
            task,
            {
                "previous_status": previous_status.value,
                "new_status": status.value,
            },
        )

        return task

    def set_plan(self, task_id: str, plan_id: str) -> Task:
        task = self.get_task(task_id)
        task.plan_id = plan_id
        task.update_timestamp()
        return task

    # ---------------------------------------------------------
    # START
    # ---------------------------------------------------------

    def start_task(self, task_id: str) -> Task:

        return self.set_status(
            task_id,
            TaskStatus.PLANNING,
        )

    # ---------------------------------------------------------
    # PAUSE
    # ---------------------------------------------------------

    def pause_task(self, task_id: str) -> Task:

        return self.set_status(
            task_id,
            TaskStatus.PAUSED,
        )

    # ---------------------------------------------------------
    # RESUME
    # ---------------------------------------------------------

    def resume_task(self, task_id: str) -> Task:

        task = self.get_task(task_id)

        if task.status != TaskStatus.PAUSED:
            raise InvalidTaskStateError(
                f"Cannot resume task from {task.status.value}"
            )

        return self.set_status(
            task_id,
            TaskStatus.EXECUTING,
        )

    # ---------------------------------------------------------
    # COMPLETE
    # ---------------------------------------------------------

    def complete_task(self, task_id: str) -> Task:

        return self.set_status(
            task_id,
            TaskStatus.COMPLETED,
        )

    # ---------------------------------------------------------
    # FAIL
    # ---------------------------------------------------------

    def fail_task(
        self,
        task_id: str,
        error: str,
    ) -> Task:

        task = self.get_task(task_id)

        task.error = error
        task.update_timestamp()

        self.set_status(
            task_id,
            TaskStatus.FAILED,
        )

        return task

    # ---------------------------------------------------------
    # CANCEL
    # ---------------------------------------------------------

    def cancel_task(self, task_id: str) -> Task:

        return self.set_status(
            task_id,
            TaskStatus.CANCELLED,
        )

    # ---------------------------------------------------------
    # CURRENT STEP
    # ---------------------------------------------------------

    def set_current_step(
        self,
        task_id: str,
        step_id: str | None,
    ) -> Task:

        task = self.get_task(task_id)

        task.current_step_id = step_id
        task.update_timestamp()

        self._emit(
            "TASK_STEP_CHANGED",
            task,
            {
                "step_id": step_id,
            },
        )

        return task

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    def add_observation(
        self,
        task_id: str,
        observation: dict,
    ) -> Task:

        task = self.get_task(task_id)

        task.context.add_observation(
            observation
        )

        task.update_timestamp()

        self._emit(
            "TASK_OBSERVATION_ADDED",
            task,
            {
                "observation": observation,
            },
        )

        return task

    def add_tool_result(
        self,
        task_id: str,
        result: dict,
    ) -> Task:

        task = self.get_task(task_id)

        task.context.add_tool_result(
            result
        )

        task.update_timestamp()

        self._emit(
            "TASK_TOOL_RESULT_ADDED",
            task,
            {
                "result": result,
            },
        )

        return task

    # ---------------------------------------------------------
    # LIST
    # ---------------------------------------------------------

    def list_tasks(self) -> list[Task]:

        return list(self._tasks.values())

    # ---------------------------------------------------------
    # EVENT
    # ---------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        task: Task,
        data: dict | None = None,
    ) -> None:

        if self._event_bus is None:
            return

        payload = {
            "task_id": task.id,
            "goal": task.goal,
            "status": task.status.value,
            **(data or {}),
        }

        # Adapt this call to your existing EventBus API.
        self._event_bus.emit(
            event_type,
            payload,
        )

    # ---------------------------------------------------------
    # TRANSITION VALIDATION
    # ---------------------------------------------------------

    @staticmethod
    def _validate_transition(
        current: TaskStatus,
        target: TaskStatus,
    ) -> None:

        if current == target:
            return

        allowed = {
            TaskStatus.CREATED: {
                TaskStatus.PLANNING,
                TaskStatus.CANCELLED,
            },

            TaskStatus.PLANNING: {
                TaskStatus.READY,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },

            TaskStatus.READY: {
                TaskStatus.EXECUTING,
                TaskStatus.CANCELLED,
            },

            TaskStatus.EXECUTING: {
                TaskStatus.OBSERVING,
                TaskStatus.EVALUATING,
                TaskStatus.PAUSED,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },

            TaskStatus.OBSERVING: {
                TaskStatus.EVALUATING,
                TaskStatus.EXECUTING,
                TaskStatus.FAILED,
            },

            TaskStatus.EVALUATING: {
                TaskStatus.EXECUTING,
                TaskStatus.REPLANNING,
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
            },

            TaskStatus.REPLANNING: {
                TaskStatus.READY,
                TaskStatus.EXECUTING,
                TaskStatus.FAILED,
            },

            TaskStatus.PAUSED: {
                TaskStatus.EXECUTING,
                TaskStatus.CANCELLED,
            },

            TaskStatus.COMPLETED: set(),

            TaskStatus.FAILED: {
                TaskStatus.REPLANNING,
                TaskStatus.CANCELLED,
            },

            TaskStatus.CANCELLED: set(),
        }

        if target not in allowed[current]:
            raise InvalidTaskStateError(
                f"Invalid task transition: "
                f"{current.value} -> {target.value}"
            )
            
# task = TaskManager()
# res = task.create_task("Open chrome and navigate to https://www.example.com")
# # print(res.id)

# # print(task.get_task(res.id))/

# print(task.start_task(res.id))