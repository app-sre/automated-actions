import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from automated_actions.api.v1.dependencies import OpaInstanceDep, UserDep
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
    ActionStatus,
)
from automated_actions.db.models._action import ActionManager, get_action_manager

router = APIRouter()
# action-detail/action-cancel authorize via get_authorized_action (which performs
# its own OPA call with the action's owner) instead of the generic router-level
# authz dependency, so they get their own router.
owner_scoped_router = APIRouter()
log = logging.getLogger(__name__)


async def get_authorized_action(
    request: Request,
    user: UserDep,
    authz: OpaInstanceDep,
    action_id: str,
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)],
) -> Action:
    """Fetch the action and authorize access to it, scoped by its owner.

    OPA's default role only allows a user to act on their own actions; the
    action's owner isn't part of the request (unlike action-list's action_user
    filter), so it has to be looked up here and passed to OPA explicitly.
    """
    action = action_mgr.get_or_404(action_id)
    await authz(request, user, extra_params={"owner": action.owner})
    return action


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


@owner_scoped_router.get(
    "/actions/{action_id}",
    operation_id="action-detail",
    tags=["General"],
)
def action_detail(
    action: Annotated[Action, Depends(get_authorized_action)],
) -> ActionSchemaOut:
    """Retrieves the details of a specific action by its ID."""
    return action.dump()


@owner_scoped_router.post(
    "/actions/{action_id}",
    operation_id="action-cancel",
    status_code=202,
    tags=["General"],
)
def action_cancel(
    action: Annotated[Action, Depends(get_authorized_action)],
) -> ActionSchemaOut:
    """Cancels a pending or running action by its ID."""
    action.set_status(ActionStatus.CANCELLED)
    return action.dump()
