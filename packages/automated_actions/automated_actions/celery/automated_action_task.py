import logging
from time import time
from typing import TYPE_CHECKING, Any

from hvac.exceptions import VaultError
from kubernetes.client.exceptions import ApiException

from automated_actions.celery.metrics import action_elapsed_time
from automated_actions.db.models import ActionStatus
from celery import Task

if TYPE_CHECKING:
    from billiard.einfo import ExceptionInfo

log = logging.getLogger(__name__)


class AutomatedActionTask(Task):
    autoretry_for = (ApiException, VaultError)
    default_retry_delay = 5
    max_retries = 3

    def before_start(  # ruff: ignore[no-self-use]
        self,
        task_id: str,  # ruff: ignore[unused-method-argument]
        args: tuple,  # ruff: ignore[unused-method-argument]
        kwargs: dict,
    ) -> None:
        kwargs["action"].set_status(ActionStatus.RUNNING)
        log.info("status=%s", ActionStatus.RUNNING)

    def on_success(  # ruff: ignore[no-self-use]
        self,
        retval: Any,  # ruff: ignore[unused-method-argument]
        task_id: str,  # ruff: ignore[unused-method-argument]
        args: tuple,  # ruff: ignore[unused-method-argument]
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

    def on_failure(  # ruff: ignore[no-self-use]
        self,
        exc: Exception,
        task_id: str,  # ruff: ignore[unused-method-argument]
        args: tuple,  # ruff: ignore[unused-method-argument]
        kwargs: dict,
        einfo: ExceptionInfo,  # ruff: ignore[unused-method-argument]
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

    def on_retry(  # ruff: ignore[no-self-use]
        self,
        exc: Exception,
        task_id: str,  # ruff: ignore[unused-method-argument]
        args: tuple,  # ruff: ignore[unused-method-argument]
        kwargs: dict,  # ruff: ignore[unused-method-argument]
        einfo: ExceptionInfo,  # ruff: ignore[unused-method-argument]
    ) -> None:
        log.debug("retrying due to %s", exc)


def _task_kwargs_to_store(kwargs: dict) -> dict:
    return {k: kwargs[k] for k in kwargs if k != "action"}
