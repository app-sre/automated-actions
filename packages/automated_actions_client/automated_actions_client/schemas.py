from __future__ import annotations

import enum
import inspect
import typing

import pydantic
from clientele.schemas import ListResponse  # noqa


class ActionSchemaOut(pydantic.BaseModel):
    name: str
    owner: str
    status: ActionStatus | None = None
    action_id: str
    result: str | None = None
    task_args: dict[str, typing.Any] | None = None
    created_at: float
    updated_at: float


class ActionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"


class CreateTokenParam(pydantic.BaseModel):
    name: str
    username: str
    email: str
    expiration: str


class HTTPValidationError(pydantic.BaseModel):
    detail: list[ValidationError]


class UserSchemaOut(pydantic.BaseModel):
    name: str
    username: str
    email: str
    created_at: float
    updated_at: float
    allowed_actions: list[str]


class ValidationError(pydantic.BaseModel):
    loc: list[str | int]
    msg: str
    type_: str = pydantic.Field(alias="type")
    input: typing.Any | None = None
    ctx: dict[str, typing.Any] | None = None

    model_config = pydantic.ConfigDict(populate_by_name=True)


class ResponseCreateToken(pydantic.BaseModel):
    pass


class ResponseActionList(ListResponse[ActionSchemaOut]):
    pass


def get_subclasses_from_same_file() -> list[type[pydantic.BaseModel]]:
    """
    Due to how Python declares classes in a module,
    we need to update_forward_refs for all the schemas generated
    here in the situation where there are nested classes.
    """
    calling_frame = inspect.currentframe()
    if not calling_frame:
        return []
    else:
        calling_frame = calling_frame.f_back
    module = inspect.getmodule(calling_frame)

    subclasses = []
    for _, c in inspect.getmembers(module):
        if (
            inspect.isclass(c)
            and issubclass(c, pydantic.BaseModel)
            and c != pydantic.BaseModel
        ):
            subclasses.append(c)

    return subclasses


subclasses: list[type[pydantic.BaseModel]] = get_subclasses_from_same_file()
for c in subclasses:
    c.model_rebuild()
