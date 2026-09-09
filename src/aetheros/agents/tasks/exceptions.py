class TaskError(Exception):
    """Base exception for task subsystem."""


class TaskNotFoundError(TaskError):
    """Raised when a task cannot be found."""


class InvalidTaskStateError(TaskError):
    """Raised when an invalid state transition is requested."""