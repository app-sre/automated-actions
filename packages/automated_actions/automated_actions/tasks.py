import logging
from typing import Any

from billiard.einfo import ExceptionInfo
from celery import Celery
from celery import Task as CeleryTask
from hvac.exceptions import VaultError
from kubernetes.client.exceptions import ApiException

from automated_actions.actions.openshift_workload_restart import (
    OpenshiftWorkloadRestart,
)
from automated_actions.api.models import Task, TaskStatus
from automated_actions.config import settings
from automated_actions.utils.cluster_connection import get_cluster_connection_data
from automated_actions.utils.openshift_client import OpenshiftClient

log = logging.getLogger(__name__)

app = Celery(
    "tasks",
    broker=settings.broker_url,
    broker_transport_options={
        "region": settings.broker_aws_region,
        "predefined_queues": {
            "celery": {
                "url": settings.sqs_url,
                "access_key_id": settings.broker_aws_access_key_id,
                "secret_access_key": settings.broker_aws_secret_access_key,
            }
        },
    },
    broker_connection_retry_on_startup=True,
    worker_enable_remote_control=False,
    worker_log_format="[%(asctime)s: GJB] %(message)s",
    # support pydantic models
    task_serializer="pickle",
    result_serializer="pickle",
    event_serializer="json",
    accept_content=["application/json", "application/x-python-serialize"],
    result_accept_content=["application/json", "application/x-python-serialize"],
)


class AutomatedActionTask(CeleryTask):
    autoretry_for = (ApiException, VaultError)
    default_retry_delay = 5
    max_retries = 3

    def before_start(  # noqa: PLR6301
        self,
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        kwargs["task"].set_status(TaskStatus.RUNNING)
        log.info("task_id=%s status=%s", kwargs["task"].task_id, TaskStatus.RUNNING)

    def on_success(  # noqa: PLR6301
        self,
        retval: Any,  # noqa: ARG002
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        result = (
            f"{kwargs['kind']} {kwargs['name']} restarted successfully on "
            f"{kwargs['cluster']}/{kwargs['namespace']}."
        )
        kwargs["task"].set_status_and_result(TaskStatus.SUCCESS, result)
        log.info(
            "task_id=%s status=%s - %s",
            kwargs["task"].task_id,
            TaskStatus.SUCCESS,
            result,
        )

    def on_failure(  # noqa: PLR6301
        self,
        exc: Exception,
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        result = (
            f"{kwargs['kind']} '{kwargs['name']}' restart failed on "
            f"'{kwargs['cluster']}/{kwargs['namespace']}': {exc}."
        )
        kwargs["task"].set_status_and_result(TaskStatus.FAILURE, result)
        log.error(
            "task_id=%s status=%s - %s",
            kwargs["task"].task_id,
            TaskStatus.FAILURE,
            result,
        )

    def on_retry(  # noqa: PLR6301
        self,
        exc: Exception,
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        log.debug("task_id=%s retrying due to %s", kwargs["task"].task_id, exc)


@app.task(base=AutomatedActionTask)
def openshift_workload_restart(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    task: Task,  # noqa: ARG001
) -> None:
    cluster_connection = get_cluster_connection_data(cluster)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    OpenshiftWorkloadRestart(oc, namespace, kind, name).run()
