from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC
from datetime import datetime as dt
from enum import StrEnum
from typing import Any, Protocol, Self, TypeVar

from pydantic import BaseModel, ConfigDict, field_serializer
from pynamodb.attributes import DynamicMapAttribute, NumberAttribute, UnicodeAttribute
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
    updated_at = NumberAttribute(range_key=True)


class Action(Table[ActionSchemaIn, ActionSchemaOut]):
    """Action."""

    class Meta(Table.Meta):
        table_name = f"aa-{settings.environment}-actions"
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
        cls: type[Self],
        username: str,
        status: ActionStatus | None = None,
        max_age: int | None = None,
    ) -> Iterable[Action]:
        """Returns actions for owner."""
        match (status, max_age):
            case (None, None):
                # If no status or max_age is provided, return all actions for the user
                return cls.owner_index.query(username)
            case (None, max_age_val) if max_age_val is not None:
                # If no status is provided, but max_age is, return actions
                # for the user not older than max_age
                return cls.owner_index.query(
                    username,
                    range_key_condition=cls.updated_at
                    >= int(dt.now(tz=UTC).timestamp() - max_age_val),
                )
            case (status_val, None) if status_val is not None:
                # If status is provided, but no max_age, return actions
                # for the user with the given status
                return cls.owner_index.query(
                    username, filter_condition=cls.status == status_val.value
                )
            case (status_val, max_age_val) if (
                status_val is not None and max_age_val is not None
            ):
                # If both status and max_age are provided, return actions
                # for the user with the given status not older than max_age
                return cls.owner_index.query(
                    username,
                    range_key_condition=cls.updated_at
                    >= int(dt.now(tz=UTC).timestamp() - max_age_val),
                    filter_condition=cls.status == status_val.value,
                )
            case _:
                return []

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
        cls,
        username: str,
        status: ActionStatus | None,
        max_age: int | None = None,
    ) -> Iterable[T_co]: ...

    @classmethod
    def get_or_404(cls, pk: str) -> T_co: ...

    @classmethod
    def create(cls, params: ActionSchemaIn) -> T_co: ...


class User(Protocol):
    username: str


class ActionManager[ActionClass: ActionProtocol]:
    """Abstract class for the action model."""

    def __init__(self, klass: type[ActionClass]) -> None:
        self.klass = klass

    def get_user_actions(
        self,
        username: str,
        status: ActionStatus | None = None,
        max_age: int | None = None,
    ) -> Iterable[ActionClass]:
        return self.klass.find_by_owner(username, status, max_age)

    def get_or_404(self, pk: str) -> ActionClass:
        """Get an action by its primary key or raise a 404 error."""
        return self.klass.get_or_404(pk)

    def create_action(self, name: str, owner: User) -> ActionClass:
        return self.klass.create(ActionSchemaIn(name=name, owner=owner.username))


def get_action_manager() -> ActionManager[Action]:
    """Get the action manager."""
    return ActionManager[Action](Action)
