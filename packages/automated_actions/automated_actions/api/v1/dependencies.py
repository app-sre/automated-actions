from typing import Annotated

from fastapi import Depends

from automated_actions.api.models import Task, TaskSchemaIn, User
from automated_actions.api.v1.auth import oidc


class TaskLog:
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, user: Annotated[User, Depends(oidc)]) -> Task:
        return Task.create(TaskSchemaIn(name=self.name, owner=user.email))
