from src.aetheros.agents.tasks.manager import TaskManager
from src.aetheros.agents.tasks.models import TaskStatus


class FakeEventBus:
    """Minimal event bus for isolated TaskManager tests."""

    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


def create_manager() -> TaskManager:
    return TaskManager(
        event_bus=FakeEventBus(),
    )


def test_create_task():
    manager = create_manager()

    task = manager.create_task(
        "Open chrome and navigate to https://www.example.com"
    )

    assert task.id
    assert task.goal == (
        "Open chrome and navigate to https://www.example.com"
    )
    assert task.status == TaskStatus.CREATED
    assert task.context is not None


def test_start_task_moves_to_planning():
    manager = create_manager()

    task = manager.create_task(
        "Open chrome and navigate to https://www.example.com"
    )

    manager.start_task(task.id)

    updated = manager.get_task(task.id)

    assert updated.status == TaskStatus.PLANNING


def test_get_task():
    manager = create_manager()

    task = manager.create_task("Test task")

    result = manager.get_task(task.id)

    assert result is task


def test_list_tasks():
    manager = create_manager()

    task1 = manager.create_task("Task 1")
    task2 = manager.create_task("Task 2")

    tasks = manager.list_tasks()

    assert len(tasks) == 2
    assert task1 in tasks
    assert task2 in tasks


def test_cancel_task():
    manager = create_manager()

    task = manager.create_task("Test cancellation")

    manager.cancel_task(task.id)

    updated = manager.get_task(task.id)

    assert updated.status == TaskStatus.CANCELLED


def test_fail_task():
    manager = create_manager()

    task = manager.create_task("Test failure")

    manager.fail_task(
        task.id,
        error="Something went wrong",
    )

    updated = manager.get_task(task.id)

    assert updated.status == TaskStatus.FAILED
    assert updated.error == "Something went wrong"


def test_complete_task():
    manager = create_manager()

    task = manager.create_task("Test completion")

    # Move into an executable state first if your
    # state-transition rules require it.
    manager.start_task(task.id)

    # Adjust intermediate transitions here if your
    # TaskManager requires them.
    manager.complete_task(task.id)

    updated = manager.get_task(task.id)

    assert updated.status == TaskStatus.COMPLETED