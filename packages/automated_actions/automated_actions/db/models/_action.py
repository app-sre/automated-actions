from __future__ import annotations

import uuid
from collections.abc import Iterable
from enum import StrEnum
from typing import Any, Protocol, Self, TypeVar

from pydantic import BaseModel, ConfigDict, field_serializer
from pynamodb.attributes import DynamicMapAttribute, UnicodeAttribute
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex

from automated_actions.config import settings
from automated_actions.db.models._base import Table


class ActionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"


class ActionSchemaIn(BaseModel):
    name: str
    owner: str
    status: ActionStatus = ActionStatus.PENDING


class ActionSchemaOut(ActionSchemaIn):
    # Pydantic doesn't know about PynamoDB's DynamicMapAttribute
    model_config = ConfigDict(arbitrary_types_allowed=True)

    action_id: str
    result: str | None = None
    task_args: DynamicMapAttribute | None = None
    created_at: float
    updated_at: float

    @field_serializer("task_args")
    def serialize_task_args(self, task_args: DynamicMapAttribute) -> dict:  # noqa: PLR6301
        if task_args is None:
            return {}

        # "attribute_values" is an empty dict in DynamicMapAttribute(s). We remove it
        # from the serialized version since it doesn't it doesn't relate to what we
        # want to show from that database field. See
        # https://github.com/pynamodb/PynamoDB/blob/a5c1f4e1b3201f01ee6d4cf759fc6dc494e67fd4/pynamodb/attributes.py#L1213
        return {
            k: task_args.attribute_values[k]
            for k in task_args.attribute_values
            if k != "attribute_values"
        }


class OwnerIndex(GlobalSecondaryIndex["Action"]):
    class Meta:
        index_name = "owner-index"
        read_capacity_units = 10
        write_capacity_units = 10
        projection = AllProjection()

    owner = UnicodeAttribute(hash_key=True)
    status = UnicodeAttribute(range_key=True)


class Action(Table[ActionSchemaIn, ActionSchemaOut]):
    """Action."""

    class Meta(Table.Meta):
        table_name = f"aa-action-{settings.environment}"
        schema_out = ActionSchemaOut

    @staticmethod
    def _pre_create(values: dict[str, Any]) -> dict[str, Any]:
        values = super(Action, Action)._pre_create(values)
        values["action_id"] = str(uuid.uuid4())
        return values

    def set_status(self, status: ActionStatus) -> None:
        self.update(actions=[Action.status.set(status.value)])

    def set_final_state(
        self, status: ActionStatus, result: str, task_args: dict
    ) -> None:
        self.update(
            actions=[
                Action.status.set(status.value),
                Action.result.set(result),
                Action.task_args.set(task_args),
            ]
        )

    @classmethod
    def find_by_owner(
        cls: type[Self], username: str, status: ActionStatus | None = None
    ) -> Iterable[Action]:
        """Returns actions for owner."""
        if status is None:
            return cls.owner_index.query(username)
        return cls.owner_index.query(username, cls.status == status.value)

    action_id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    status = UnicodeAttribute()
    result = UnicodeAttribute(null=True)
    task_args = DynamicMapAttribute(null=True)
    owner = UnicodeAttribute()
    owner_index = OwnerIndex()


T_co = TypeVar("T_co", covariant=True)


class ActionProtocol(Protocol[T_co]):
    """Protocol for the action model."""

    status: Any

    @classmethod
    def find_by_owner(
        cls, username: str, status: ActionStatus | None
    ) -> Iterable[T_co]: ...

    @classmethod
    def get_or_404(cls, pk: str) -> T_co: ...

    @classmethod
    def create(cls, params: ActionSchemaIn) -> T_co: ...


class User(Protocol):
    username: UnicodeAttribute


class ActionManager[ActionClass: ActionProtocol]:
    """Abstract class for the action model."""

    def __init__(self, klass: type[ActionClass]) -> None:
        self.klass = klass

    def get_user_actions(
        self, username: str, status: ActionStatus | None = None
    ) -> Iterable[ActionClass]:
        return self.klass.find_by_owner(username, status)

    def get_or_404(self, pk: str) -> ActionClass:
        """Get an action by its primary key or raise a 404 error."""
        return self.klass.get_or_404(pk)

    def create_action(self, name: str, owner: User) -> ActionClass:
        return self.klass.create(ActionSchemaIn(name=name, owner=owner.username))


def get_action_manager() -> ActionManager[Action]:
    """Get the action manager."""
    return ActionManager[Action](Action)
