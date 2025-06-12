import logging

from fastapi import APIRouter

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.db.models import UserSchemaOut

router = APIRouter()
log = logging.getLogger(__name__)


@router.get(
    "/me",
    operation_id="me",
    tags=["General"],
)
def me(user: UserDep) -> UserSchemaOut:
    """Get the current user information."""
    return user.dump()
