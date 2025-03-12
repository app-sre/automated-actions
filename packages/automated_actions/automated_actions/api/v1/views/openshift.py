import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from automated_actions.api.models import (
    Task,
    TaskSchemaOut,
    TaskStatus,
)
from automated_actions.api.v1.dependencies import TaskLog

router = APIRouter()
log = logging.getLogger(__name__)


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
        Path(
            description="OpenShift workload kind. e.g. Deployment or Pod",
            example="Deployment",
        ),
    ],
    name: Annotated[str, Path(description="OpenShift workload name")],
    task: Annotated[Task, Depends(TaskLog("openshift-workload-restart"))],
) -> TaskSchemaOut:
    """Restart an OpenShift workload."""
    log.info(f"Restarting {kind}/{name} in {cluster}/{namespace}")
    task.set_status(TaskStatus.RUNNING)
    return task.dump()
