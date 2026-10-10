import logging
from datetime import date as date_type
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from automated_actions.api.v1.dependencies import (
    UserDep,  # ruff: ignore[typing-only-first-party-import]
)
from automated_actions.celery.payload_tracker.tasks import (
    payload_tracker_create_partition as payload_tracker_create_partition_task,
)
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
)
from automated_actions.db.models._action import ActionManager, get_action_manager

router = APIRouter()
log = logging.getLogger(__name__)

PAYLOAD_TRACKER_CREATE_PARTITION_ID = "payload-tracker-create-partition"


def get_action_payload_tracker_create_partition(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Creates a new action record for a payload-tracker create-partition operation."""
    return action_mgr.create_action(
        name=PAYLOAD_TRACKER_CREATE_PARTITION_ID, owner=user
    )


@router.post(
    "/payload-tracker/create-partition/{cluster}/{namespace}/{date}",
    operation_id=PAYLOAD_TRACKER_CREATE_PARTITION_ID,
    status_code=202,
    tags=["Actions"],
)
def payload_tracker_create_partition(
    cluster: Annotated[str, Path(description="OpenShift cluster name")],
    namespace: Annotated[str, Path(description="payload-tracker namespace")],
    date: Annotated[
        date_type,
        Path(description="Date of the partition to create (YYYY-MM-DD)"),
    ],
    action: Annotated[Action, Depends(get_action_payload_tracker_create_partition)],
) -> ActionSchemaOut:
    """Create a payload-tracker database partition for a given date.

    Runs a one-off Job in the payload-tracker namespace that calls the
    idempotent create_partition SQL function for the requested date. Useful to
    recover a partition that the daily vacuum cronjob failed to create.
    """
    log.info(
        f"Creating partition for {date} in {cluster}/{namespace}: "
        f"action_id={action.action_id}"
    )
    payload_tracker_create_partition_task.apply_async(
        kwargs={
            "cluster": cluster,
            "namespace": namespace,
            "date": date.isoformat(),
            "action": action,
        },
        task_id=action.action_id,
    )
    return action.dump()
