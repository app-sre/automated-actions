import logging
from time import time
from typing import Any

from billiard.einfo import ExceptionInfo
from hvac.exceptions import VaultError
from kubernetes.client.exceptions import ApiException

from automated_actions.celery.metrics import action_elapsed_time
from automated_actions.db.models import ActionStatus
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
        kwargs["action"].set_status(ActionStatus.RUNNING)
        log.info("status=%s", ActionStatus.RUNNING)

    def on_success(  # noqa: PLR6301
        self,
        retval: Any,  # noqa: ARG002
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        result = "ok"
        kwargs["action"].set_final_state(
            status=ActionStatus.SUCCESS,
            result=result,
            task_args=_task_kwargs_to_store(kwargs),
        )
        log.info(
            "status=%s - %s",
            ActionStatus.SUCCESS,
            result,
        )
        elapsed_time = time() - kwargs["action"].created_at
        action_elapsed_time.labels(
            name=kwargs["action"].name, status=ActionStatus.SUCCESS
        ).observe(amount=elapsed_time)

    def on_failure(  # noqa: PLR6301
        self,
        exc: Exception,
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        result = str(exc)
        kwargs["action"].set_final_state(
            status=ActionStatus.FAILURE,
            result=result,
            task_args=_task_kwargs_to_store(kwargs),
        )
        log.error(
            "status=%s - %s",
            ActionStatus.FAILURE,
            result,
        )
        elapsed_time = time() - kwargs["action"].created_at
        action_elapsed_time.labels(
            name=kwargs["action"].name, status=ActionStatus.FAILURE
        ).observe(amount=elapsed_time)

    def on_retry(  # noqa: PLR6301
        self,
        exc: Exception,
        task_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,  # noqa: ARG002
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        log.debug("retrying due to %s", exc)


def _task_kwargs_to_store(kwargs: dict) -> dict:
    return {k: kwargs[k] for k in kwargs if k != "action"}
