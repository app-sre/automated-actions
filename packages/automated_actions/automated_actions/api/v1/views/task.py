import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from automated_actions.api.models import (
    Task,
    TaskSchemaOut,
    TaskStatus,
    User,
)
from automated_actions.api.v1.auth import oidc

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/tasks", operation_id="task_list")
def task_list(
    user: Annotated[User, Depends(oidc)],
    status: Annotated[TaskStatus | None, Query()] = TaskStatus.RUNNING,
) -> list[TaskSchemaOut]:
    """List all user tasks."""
    return [
        task.dump()
        for task in Task.owner_index.query(user.email, Task.status == status)
    ]


@router.get("/tasks/{pk}", operation_id="task_detail")
def task_detail(pk: str) -> TaskSchemaOut:
    """Retrieve an task."""
    return Task.get_or_404(pk).dump()


@router.post("/tasks/{pk}", operation_id="task_cancel", status_code=202)
def task_cancel(pk: str) -> TaskSchemaOut:
    """Cancel an action."""
    action = Task.get_or_404(pk)
    action.set_status(TaskStatus.CANCELLED)
    return action.dump()
