import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.celery.external_resource.tasks import (
    external_resource_rds_reboot as external_resource_rds_reboot_task,
)
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
)
from automated_actions.db.models._action import ActionManager, get_action_manager

router = APIRouter()
log = logging.getLogger(__name__)


def get_action(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Get a new action object for the user."""
    return action_mgr.create_action(
        name="external-resource-rds-reboot", owner=user.email
    )


@router.post(
    "/external-resource/rds-reboot/{account}/{identifier}",
    operation_id="external-resource-rds-reboot",
    status_code=202,
)
def external_resource_rds_reboot(
    account: Annotated[str, Path(description="AWS account name")],
    identifier: Annotated[str, Path(description="RDS instance identifier")],
    action: Annotated[Action, Depends(get_action)],
    force_failover: Annotated[
        bool,
        Query(
            description="Enforce DB failover. Your RDS must be confiugred for Multi-AZ!"
        ),
    ] = False,
) -> ActionSchemaOut:
    """Reboot an RDS instance."""
    log.info(f"Restarting RDS {identifier} in AWS account {account}")
    external_resource_rds_reboot_task.apply_async(
        kwargs={
            "account": account,
            "identifier": identifier,
            "force_failover": force_failover,
            "action": action,
        },
        task_id=action.action_id,
    )
    return action.dump()
