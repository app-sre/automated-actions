import logging
from typing import Annotated

from fastapi import APIRouter, Query

from automated_actions.api.v1.models import ActionSchemaOut, User
from automated_actions.api.v1.models.user import UserSchemaIn, UserSchemaOut

from .schemas import NoopParam

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
) -> ActionSchemaOut:
    """Run a noop action"""
    log.info(f"{param=}, {labels=}")
    return ActionSchemaOut(id="123")


@router.get("/foobar/{pk}", operation_id="foobar")
def run_foobar(pk: str, q: str | None = None) -> UserSchemaOut:
    """Run a foobar action"""
    log.debug(f"{pk=}, {q=}")
    return User.get("test@example.com").dump()
    return User.create(
        UserSchemaIn(
            name="foo", username="bar", email="test@example.com", roles=["admin"]
        )
    ).dump()
