import logging
from typing import Annotated

from fastapi import Depends, Request

from automated_actions.auth import OPA, BearerTokenAuth
from automated_actions.db.models import User

log = logging.getLogger(__name__)


async def get_user(request: Request) -> User:
    if user := await request.app.state.token(request):
        return user
    return await request.app.state.oidc(request)


UserDep = Annotated[User, Depends(get_user)]


def get_bearer_token_auth(request: Request) -> BearerTokenAuth:
    return request.app.state.token


BearerTokenAuthDep = Annotated[BearerTokenAuth, Depends(get_bearer_token_auth)]


async def get_authz(request: Request, user: UserDep) -> OPA:
    return await request.app.state.authz(request, user)


AuthZDep = Annotated[OPA, Depends(get_authz)]
