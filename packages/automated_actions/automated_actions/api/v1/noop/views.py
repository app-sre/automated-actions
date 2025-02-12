import logging
from typing import Annotated

from fastapi import APIRouter, Query

from automated_actions.api.v1.models import Action

from .models import NoopParam

router = APIRouter()
log = logging.getLogger(__name__)


@router.post(
    "/noop",
    operation_id="noop",
    status_code=202,
)
def run_noop(
    param: NoopParam,
    labels: Annotated[list[str] | None, Query()] = None,
) -> Action:
    """Run a noop action"""
    log.info(f"{param=}, {labels=}")
    return Action(id="123")


@router.get("/foobar/{pk}", operation_id="foobar")
def run_foobar(pk: str, q: str | None = None) -> None:
    """Run a foobar action"""
    log.debug(f"{pk=}")
