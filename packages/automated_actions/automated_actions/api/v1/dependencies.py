from typing import Annotated

from fastapi import Depends, Request

from automated_actions.api.models import Task, TaskSchemaIn, User


async def get_user(request: Request) -> User:
    return await request.app.state.oidc(request)


UserDep = Annotated[User, Depends(get_user)]


class TaskLog:
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, user: UserDep) -> Task:
        return Task.create(TaskSchemaIn(name=self.name, owner=user.email))
