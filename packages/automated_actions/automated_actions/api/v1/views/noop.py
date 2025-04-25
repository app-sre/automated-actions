import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from automated_actions.api.v1.dependencies import ActionLog, UserDep
from automated_actions.db.models import (
    Action,
    ActionSchemaOut,
    ActionStatus,
    UserSchemaOut,
)

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
    action: Annotated[Action, Depends(ActionLog("noop"))],
    labels: Annotated[list[str] | None, Query()] = None,
) -> ActionSchemaOut:
    """Run a noop action"""
    log.info(f"{param=}, {labels=}")
    action.set_status(ActionStatus.RUNNING)
    return action.dump()


@router.get("/foobar/{pk}", operation_id="foobar")
def run_foobar(
    pk: str,
    user: UserDep,
    q: str | None = None,
) -> UserSchemaOut:
    """Run a foobar action"""
    log.debug(f"{pk=}, {q=}")
    return user.dump()
