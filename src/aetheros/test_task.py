
# from aetheros.agents.tasks.manager import TaskManager
from aetheros.agents.tasks.manager import TaskManager

from .core.logging import get_logger

from .core.container import container as sc
logger = get_logger("test_task")



def test_task():
    logger.info("Testing TaskManager.atus}")

    logger.debug("Starting task...")
    task_manager.start_task(task.id)

    logger.debug("Retrieving task status...")
    logger.debug(f"Task Status: {task_manager.get_task(task.id).status}")

if __name__ == "__main__":
    test_task() 