import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.db.models import (
    ActionSchemaOut,
    ActionStatus,
)
from automated_actions.db.models._action import ActionManager, get_action_manager

router = APIRouter()
log = logging.getLogger(__name__)


@router.get(
    "/actions",
    operation_id="action-list",
    tags=["General"],
)
def action_list(
    user: UserDep,
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)],
    status: Annotated[
        ActionStatus | None, Query(description="Filter actions by their status")
    ] = None,
    action_user: Annotated[
        str | None,
        Query(
            description="Filter actions by username instead of the current authenticated user"
        ),
    ] = None,
    max_age_minutes: Annotated[
        int | None,
        Query(
            description="Filter actions by their age in minutes. Actions updated more than this many minutes ago will be excluded.",
            ge=0,
        ),
    ] = None,
) -> list[ActionSchemaOut]:
    """Lists actions, optionally filtered by status, user, or age."""
    return [
        action.dump()
        for action in action_mgr.get_user_actions(
            action_user or user.username,
            status,
            max_age=max_age_minutes * 60 if max_age_minutes else max_age_minutes,
        )
    ]


@router.get(
    "/actions/{action_id}",
    operation_id="action-detail",
    tags=["General"],
)
def action_detail(
    action_id: str, action_mgr: Annotated[ActionManager, Depends(get_action_manager)]
) -> ActionSchemaOut:
    """Retrieves the details of a specific action by its ID."""
    return action_mgr.get_or_404(action_id).dump()


@router.post(
    "/actions/{action_id}",
    operation_id="action-cancel",
    status_code=202,
    tags=["General"],
)
def action_cancel(
    action_id: str, action_mgr: Annotated[ActionManager, Depends(get_action_manager)]
) -> ActionSchemaOut:
    """Cancels a pending or running action by its ID."""
    action = action_mgr.get_or_404(action_id)
    action.set_status(ActionStatus.CANCELLED)
    return action.dump()
