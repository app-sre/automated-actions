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
        action_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        kwargs["action"].set_status(ActionStatus.RUNNING)
        log.info(
            "action_id=%s status=%s", kwargs["action"].action_id, ActionStatus.RUNNING
        )

    def on_success(  # noqa: PLR6301
        self,
        retval: Any,  # noqa: ARG002
        action_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
    ) -> None:
        result = (
            f"{kwargs['kind']} {kwargs['name']} restarted successfully on "
            f"{kwargs['cluster']}/{kwargs['namespace']}."
        )
        kwargs["action"].set_status_and_result(ActionStatus.SUCCESS, result)
        log.info(
            "action_id=%s status=%s - %s",
            kwargs["action"].action_id,
            ActionStatus.SUCCESS,
            result,
        )

    def on_failure(  # noqa: PLR6301
        self,
        exc: Exception,
        action_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        result = (
            f"{kwargs['kind']} '{kwargs['name']}' restart failed on "
            f"'{kwargs['cluster']}/{kwargs['namespace']}': {exc}."
        )
        kwargs["action"].set_status_and_result(ActionStatus.FAILURE, result)
        log.error(
            "action_id=%s status=%s - %s",
            kwargs["action"].action_id,
            ActionStatus.FAILURE,
            result,
        )

    def on_retry(  # noqa: PLR6301
        self,
        exc: Exception,
        action_id: str,  # noqa: ARG002
        args: tuple,  # noqa: ARG002
        kwargs: dict,
        einfo: ExceptionInfo,  # noqa: ARG002
    ) -> None:
        log.debug("action_id=%s retrying due to %s", kwargs["action"].action_id, exc)
