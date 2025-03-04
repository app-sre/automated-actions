import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from automated_actions.api.models import (
    Task,
    TaskSchemaOut,
    TaskStatus,
    User,
    UserSchemaOut,
)
from automated_actions.api.v1.auth import oidc
from automated_actions.api.v1.dependencies import TaskLog

router = APIRouter()
log = logging.getLogger(__name__)


class NoopParam(BaseModel):
    alias: str
    description: str = "no description"

    # pydantic config
    model_config = {"extra": "ignore"}


@router.post(
    "/noop",
    operation_id="noop",
    status_code=202,
)
def run_noop(
    param: NoopParam,
    action: Annotated[Task, Depends(TaskLog("noop"))],
    labels: Annotated[list[str] | None, Query()] = None,
) -> TaskSchemaOut:
    """Run a noop action"""
    log.info(f"{param=}, {labels=}")
    action.set_status(TaskStatus.RUNNING)
    return action.dump()


@router.get("/foobar/{pk}", operation_id="foobar")
def run_foobar(
    pk: str,
    user: Annotated[User, Depends(oidc)],
    q: str | None = None,
) -> UserSchemaOut:
    """Run a foobar action"""
    log.debug(f"{pk=}, {q=}")
    return user.dump()
