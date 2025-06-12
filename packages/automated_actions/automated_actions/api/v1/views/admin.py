import logging
from datetime import datetime as dt

from fastapi import APIRouter
from pydantic import BaseModel

from automated_actions.api.v1.dependencies import BearerTokenAuthDep, UserDep

router = APIRouter()
log = logging.getLogger(__name__)


class CreateTokenParam(BaseModel):
    name: str
    username: str
    email: str
    expiration: dt


@router.post(
    "/admin/token",
    operation_id="create-token",
    tags=["Admin"],
)
def create_token(
    param: CreateTokenParam, user: UserDep, token_auth: BearerTokenAuthDep
) -> str:
    """Create a token for a service account."""
    log.info(f"Token {param} creation by {user.username}")
    return token_auth.create_token(
        name=param.name,
        username=param.username,
        email=param.email,
        expiration=param.expiration,
    )
