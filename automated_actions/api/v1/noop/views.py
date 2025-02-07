import logging
from typing import Annotated

from fastapi import APIRouter, Query

from automated_actions.api.v1.models import Action

from .models import NoopParam

router = APIRouter()
log = logging.getLogger(__name__)


@router.post(
    "/noop",
    operation_id="run_noop_action",
    summary="Run a noop action",
    status_code=202,
)
def run_noop(
    param: NoopParam,
    labels: Annotated[list[str] | None, Query()] = None,
) -> Action:
    """Noop action"""
    log.info(f"{param=}, {labels=}")
    return Action(id="123")


@router.get(
    "/foobar/{pk}", operation_id="run_foobar_action", summary="Run a foobar action"
)
def run_foobar(pk: str) -> None:
    """Noop action"""
    log.debug(f"{pk=}")
