import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.celery.external_resource.tasks import (
    external_resource_flush_elasticache as external_resource_flush_elasticache_task,
)
from automated_actions.celery.external_resource.tasks import (
    external_resource_rds_logs as external_resource_rds_logs_task,
)
from automated_actions.celery.external_resource.tasks import (
    external_resource_rds_reboot as external_resource_rds_reboot_task,
)
from automated_actions.celery.external_resource.tasks import (
    external_resource_rds_snapshot as external_resource_rds_snapshot_task,
)
from automated_actions.db.models import Action, ActionSchemaOut
from automated_actions.db.models._action import ActionManager, get_action_manager

router = APIRouter()
log = logging.getLogger(__name__)

EXTERNAL_RESOURCE_FLUSH_ELASTICACHE_ACTION_ID = "external-resource-flush-elasticache"
EXTERNAL_RESOURCE_RDS_LOGS_ACTION_ID = "external-resource-rds-logs"
EXTERNAL_RESOURCE_RDS_REBOOT_ACTION_ID = "external-resource-rds-reboot"
EXTERNAL_RESOURCE_RDS_SNAPSHOT_ACTION_ID = "external-resource-rds-snapshot"


def get_action_external_resource_rds_logs(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Get a new action object for the user.

    Args:
        action_mgr: The action manager dependency.
        user: The user dependency.

    Returns:
        A new Action object.
    """
    return action_mgr.create_action(
        name=EXTERNAL_RESOURCE_RDS_LOGS_ACTION_ID, owner=user
    )


@router.post(
    "/external-resource/rds-logs/{account}/{identifier}",
    operation_id=EXTERNAL_RESOURCE_RDS_LOGS_ACTION_ID,
    status_code=202,
    tags=["Actions"],
)
def external_resource_rds_logs(
    account: Annotated[str, Path(description="AWS account name")],
    identifier: Annotated[str, Path(description="RDS instance identifier")],
    action: Annotated[Action, Depends(get_action_external_resource_rds_logs)],
    expiration_days: Annotated[
        int, Query(description="Expiration time in days", ge=1, le=7)
    ] = 7,
    s3_file_name: Annotated[
        str | None,
        Query(
            description="The S3 target file name. Defaults to '{account}-{identifier}.zip' if not provided."
        ),
    ] = None,
) -> ActionSchemaOut:
    """Get RDS logs for an instance.

    This action retrieves logs from a specified RDS instance in a given AWS account and stores them in an S3 bucket.
    """
    log.info(
        f"Getting logs for RDS {identifier} in AWS account {account}. action_id={action.action_id}"
    )
    external_resource_rds_logs_task.apply_async(
        kwargs={
            "account": account,
            "identifier": identifier,
            "expiration_days": expiration_days,
            "s3_file_name": s3_file_name,
            "action": action,
        },
        task_id=action.action_id,
    )
    return action.dump()


def get_action_external_resource_rds_reboot(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Get a new action object for the user.

    Args:
        action_mgr: The action manager dependency.
        user: The user dependency.

    Returns:
        A new Action object.
    """
    return action_mgr.create_action(
        name=EXTERNAL_RESOURCE_RDS_REBOOT_ACTION_ID, owner=user
    )


@router.post(
    "/external-resource/rds-reboot/{account}/{identifier}",
    operation_id=EXTERNAL_RESOURCE_RDS_REBOOT_ACTION_ID,
    status_code=202,
    tags=["Actions"],
)
def external_resource_rds_reboot(
    account: Annotated[str, Path(description="AWS account name")],
    identifier: Annotated[str, Path(description="RDS instance identifier")],
    action: Annotated[Action, Depends(get_action_external_resource_rds_reboot)],
    *,
    force_failover: Annotated[
        bool,
        Query(
            description="Enforce DB failover. Your RDS must be confiugred for Multi-AZ!"
        ),
    ] = False,
) -> ActionSchemaOut:
    """Reboot an RDS instance.

    This action initiates a reboot of a specified RDS instance in a given AWS account.
    """
    log.info(
        f"Restarting RDS {identifier} in AWS account {account}. action_id={action.action_id}"
    )
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


def get_action_external_resource_rds_snapshot(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Get a new action object for the user.

    Args:
        action_mgr: The action manager dependency.
        user: The user dependency.

    Returns:
        A new Action object.
    """
    return action_mgr.create_action(
        name=EXTERNAL_RESOURCE_RDS_SNAPSHOT_ACTION_ID, owner=user
    )


@router.post(
    "/external-resource/rds-snapshot/{account}/{identifier}/{snapshot_identifier}",
    operation_id=EXTERNAL_RESOURCE_RDS_SNAPSHOT_ACTION_ID,
    status_code=202,
    tags=["Actions"],
)
def external_resource_rds_snapshot(
    account: Annotated[str, Path(description="AWS account name")],
    identifier: Annotated[str, Path(description="RDS instance identifier")],
    snapshot_identifier: Annotated[str, Path(description="Snapshot identifier")],
    action: Annotated[Action, Depends(get_action_external_resource_rds_snapshot)],
) -> ActionSchemaOut:
    """Create a snapshot of an RDS instance.

    This action initiates a snapshot of a specified RDS instance in a given AWS account.
    """
    log.info(
        f"Creating snapshot of RDS {identifier} in AWS account {account}. action_id={action.action_id}"
    )
    external_resource_rds_snapshot_task.apply_async(
        kwargs={
            "account": account,
            "identifier": identifier,
            "snapshot_identifier": snapshot_identifier,
            "action": action,
        },
        task_id=action.action_id,
    )
    return action.dump()


def get_action_external_resource_flush_elasticache(
    action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
) -> Action:
    """Get a new action object for the user.

    Args:
        action_mgr: The action manager dependency.
        user: The user dependency.

    Returns:
        A new Action object.
    """
    return action_mgr.create_action(
        name=EXTERNAL_RESOURCE_FLUSH_ELASTICACHE_ACTION_ID, owner=user
    )


@router.post(
    "/external-resource/flush-elasticache/{account}/{identifier}",
    operation_id=EXTERNAL_RESOURCE_FLUSH_ELASTICACHE_ACTION_ID,
    status_code=202,
    tags=["Actions"],
)
def external_resource_flush_elasticache(
    account: Annotated[str, Path(description="AWS account name")],
    identifier: Annotated[str, Path(description="RDS instance identifier")],
    action: Annotated[Action, Depends(get_action_external_resource_flush_elasticache)],
) -> ActionSchemaOut:
    """Flush an ElastiCache instance.

    This action initiates a flush of a specified ElastiCache instance in a given AWS account.
    """
    log.info(
        f"Flushing ElastiCache {identifier} in AWS account {account}. action_id={action.action_id}"
    )
    external_resource_flush_elasticache_task.apply_async(
        kwargs={
            "account": account,
            "identifier": identifier,
            "action": action,
        },
        task_id=action.action_id,
    )
    return action.dump()
