import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.celery.no_op.tasks import no_op as no_op_task
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
)
from automated_actions.db.models._action import ActionManager, get_action_manager

router = APIRouter()
log = logging.getLogger(__name__)

NO_OP = "no-op"


def get_action(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Creates a new action record for a no-op operation."""
    return action_mgr.create_action(name=NO_OP, owner=user)


@router.post(f"/{NO_OP}", operation_id=NO_OP, status_code=202)
def no_op(action: Annotated[Action, Depends(get_action)]) -> ActionSchemaOut:
    """Initiates a no-operation action.

    This action performs no actual operation but can be used for testing.
    """
    log.info(f"{NO_OP}: action_id={action.action_id}")
    no_op_task.apply_async(
        kwargs={"action": action},
        task_id=action.action_id,
    )
    return action.dump()
