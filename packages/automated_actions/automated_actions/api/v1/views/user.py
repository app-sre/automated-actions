import logging

from fastapi import APIRouter

from automated_actions.api.models import UserSchemaOut
from automated_actions.api.v1.dependencies import UserDep

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/me", operation_id="me")
def me(user: UserDep) -> UserSchemaOut:
    return user.dump()
