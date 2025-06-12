import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path

from automated_actions.api.v1.dependencies import UserDep
from automated_actions.celery.openshift.tasks import (
    openshift_workload_restart as openshift_workload_restart_task,
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
    """Creates a new action record for an OpenShift operation."""
    return action_mgr.create_action(name="openshift-workload-restart", owner=user)


@router.post(
    "/openshift/workload-restart/{cluster}/{namespace}/{kind}/{name}",
    operation_id="openshift-workload-restart",
    status_code=202,
    tags=["Actions"],
)
def openshift_workload_restart(
    cluster: Annotated[str, Path(description="OpenShift cluster name")],
    namespace: Annotated[str, Path(description="OpenShift namespace")],
    kind: Annotated[
        # keep in sync with openshift_client.RollingRestartResource. Especially it must match the string cases!
        Literal["Pod", "Deployment", "DaemonSet", "StatefulSet"],
        Path(description="OpenShift workload kind. e.g. Deployment or Pod"),
    ],
    name: Annotated[str, Path(description="OpenShift workload name")],
    action: Annotated[Action, Depends(get_action)],
) -> ActionSchemaOut:
    """Initiates a restart of a specified OpenShift workload.

    This action triggers a restart of a workload (e.g., Pod, Deployment)
    within a given OpenShift cluster and namespace.
    """
    log.info(
        f"Restarting {kind}/{name} in {cluster}/{namespace}: action_id={action.action_id}"
    )
    openshift_workload_restart_task.apply_async(
        kwargs={
            "cluster": cluster,
            "namespace": namespace,
            "kind": kind,
            "name": name,
            "action": action,
        },
        task_id=action.action_id,
    )
    return action.dump()
