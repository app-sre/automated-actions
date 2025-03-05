import logging
from typing import Annotated

from fastapi import APIRouter, Query

from automated_actions.api.models import (
    Task,
    TaskSchemaOut,
    TaskStatus,
)
from automated_actions.api.v1.dependencies import UserDep

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/tasks", operation_id="task-list")
def task_list(
    user: UserDep,
    status: Annotated[TaskStatus | None, Query()] = TaskStatus.RUNNING,
) -> list[TaskSchemaOut]:
    """List all user tasks."""
    return [
        task.dump()
        for task in Task.owner_index.query(user.email, Task.status == status)
    ]


@router.get("/tasks/{task_id}", operation_id="task-detail")
def task_detail(task_id: str) -> TaskSchemaOut:
    """Retrieve an task."""
    return Task.get_or_404(task_id).dump()


@router.post("/tasks/{task_id}", operation_id="task-cancel", status_code=202)
def task_cancel(task_id: str) -> TaskSchemaOut:
    """Cancel an action."""
    task = Task.get_or_404(task_id)
    task.set_status(TaskStatus.CANCELLED)
    return task.dump()
