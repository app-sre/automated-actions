import logging
from typing import Any

from billiard.einfo import ExceptionInfo
from hvac.exceptions import VaultError
from kubernetes.client.exceptions import ApiException

from automated_actions.db.models import ActionStatus
from celery import Task

log = logging.getLogger(__name__)


class AutomatedActionTask(Task):
    autoretry_for = (ApiException, VaultError)
    default_retry_delay = 5
    max_retries = 3

    def before_start(  # noqa: PLR6301
        self,
        task_id: str,
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        kwargs["action"].set_status(ActionStatus.RUNNING)
        log.info("action_id=%s status=%s", task_id, ActionStatus.RUNNING)

    def on_success(  # noqa: PLR6301
        self,
        retval: Any,  # noqa: ARG002
        task_id: str,
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        result = "ok"
        kwargs["action"].set_status_and_result(ActionStatus.SUCCESS, result)
        log.info(
            "action_id=%s status=%s - %s",
            task_id,
            ActionStatus.SUCCESS,
            result,
        )

    def on_failure(  # noqa: PLR6301
        self,
        exc: Exception,
        task_id: str,
        args: tuple,  # noqa: ARG002
        kwargs: dict,
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        result = str(exc)
        kwargs["action"].set_status_and_result(ActionStatus.FAILURE, result)
        log.error(
            "action_id=%s status=%s - %s",
            task_id,
            ActionStatus.FAILURE,
            result,
        )

    def on_retry(  # noqa: PLR6301
        self,
        exc: Exception,
        task_id: str,
        args: tuple,  # noqa: ARG002
        kwargs: dict,  # noqa: ARG002
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        log.debug("action_id=%s retrying due to %s", task_id, exc)
