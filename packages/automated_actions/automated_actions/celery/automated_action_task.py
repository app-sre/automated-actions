import logging
from typing import Any

from billiard.einfo import ExceptionInfo
from hvac.exceptions import VaultError
from kubernetes.client.exceptions import ApiException

from automated_actions.db.models import TaskStatus
from celery import Task

log = logging.getLogger(__name__)


class AutomatedActionTask(Task):
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
