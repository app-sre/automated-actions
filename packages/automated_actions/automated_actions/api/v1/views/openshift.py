import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from automated_actions.api.v1.dependencies import ActionLog
from automated_actions.celery.openshift.tasks import (
    openshift_workload_restart as openshift_workload_restart_task,
)
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
)

router = APIRouter()
log = logging.getLogger(__name__)


def get_action_log() -> ActionLog:
    """Get the action log dependency."""
    return ActionLog("openshift-workload-restart")


@router.post(
    "/openshift/workload-restart/{cluster}/{namespace}/{kind}/{name}",
    operation_id="openshift-workload-restart",
    status_code=202,
)
def openshift_workload_restart(
    cluster: Annotated[str, Path(description="OpenShift cluster name")],
    namespace: Annotated[str, Path(description="OpenShift namespace")],
    kind: Annotated[
        str,
        Path(description="OpenShift workload kind. e.g. Deployment or Pod"),
    ],
    name: Annotated[str, Path(description="OpenShift workload name")],
    action: Annotated[Action, Depends(get_action_log)],
) -> ActionSchemaOut:
    """Restart an OpenShift workload."""
    log.info(f"Restarting {kind}/{name} in {cluster}/{namespace}")
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
