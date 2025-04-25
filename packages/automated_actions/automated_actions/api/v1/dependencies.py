from typing import Annotated

from fastapi import Depends, Request

from automated_actions.auth import OPA
from automated_actions.db.models import Action, ActionSchemaIn, User


async def get_user(request: Request) -> User:
    return await request.app.state.oidc(request)


UserDep = Annotated[User, Depends(get_user)]


async def get_authz(request: Request, user: UserDep) -> OPA:
    return await request.app.state.authz(request, user)


AuthZDep = Annotated[OPA, Depends(get_authz)]


class ActionLog:
    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, user: UserDep) -> Action:
        return Action.create(ActionSchemaIn(name=self.name, owner=user.email))
