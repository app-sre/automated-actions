import logging
from typing import Annotated

from fastapi import APIRouter, Query

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
    ActionStatus,
)

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/actions", operation_id="action-list")
def action_list(
    user: UserDep,
    status: Annotated[ActionStatus | None, Query()] = ActionStatus.RUNNING,
) -> list[ActionSchemaOut]:
    """List all user actions."""
    return [
        action.dump()
        for action in Action.owner_index.query(user.email, Action.status == status)
    ]


@router.get("/actions/{action_id}", operation_id="action-detail")
def action_detail(action_id: str) -> ActionSchemaOut:
    """Retrieve an action."""
    return Action.get_or_404(action_id).dump()


@router.post("/actions/{action_id}", operation_id="action-cancel", status_code=202)
def action_cancel(action_id: str) -> ActionSchemaOut:
    """Cancel an action."""
    action = Action.get_or_404(action_id)
    action.set_status(ActionStatus.CANCELLED)
    return action.dump()
