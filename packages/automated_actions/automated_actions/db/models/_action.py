from __future__ import annotations

import uuid
from collections.abc import Iterable
from enum import StrEnum
from typing import Any, Protocol, Self, TypeVar

from pydantic import BaseModel
from pynamodb.attributes import UnicodeAttribute
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex

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
    action_id: str
    result: str | None = None
    created_at: float
    updated_at: float


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
        table_name = "aa-action"
        schema_out = ActionSchemaOut

    @staticmethod
    def _pre_create(values: dict[str, Any]) -> dict[str, Any]:
        values = super(Action, Action)._pre_create(values)
        values["action_id"] = str(uuid.uuid4())
        return values

    def set_status(self, status: ActionStatus) -> None:
        self.update(actions=[Action.status.set(status.value)])

    def set_status_and_result(self, status: ActionStatus, result: str) -> None:
        self.update(
            actions=[Action.status.set(status.value), Action.result.set(result)]
        )

    @classmethod
    def find_by_owner_and_status(
        cls: type[Self], owner_email: str, status: ActionStatus
    ) -> Iterable[Action]:
        """Returns actions by owner and status."""
        return cls.owner_index.query(owner_email, cls.status == status.value)

    action_id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    status = UnicodeAttribute()
    result = UnicodeAttribute(null=True)
    owner = UnicodeAttribute()
    owner_index = OwnerIndex()


T_co = TypeVar("T_co", covariant=True)


class ActionProtocol(Protocol[T_co]):
    """Protocol for the action model."""

    status: Any

    @classmethod
    def find_by_owner_and_status(
        cls, owner_email: str, status: ActionStatus
    ) -> Iterable[T_co]: ...

    @classmethod
    def get_or_404(cls, pk: str) -> T_co: ...


class ActionManager[ActionClass: ActionProtocol]:
    """Abstract class for the action model."""

    def __init__(self, klass: type[ActionClass]) -> None:
        self.klass = klass

    def get_user_actions(
        self, email: str, status: ActionStatus
    ) -> Iterable[ActionClass]:
        return self.klass.find_by_owner_and_status(email, status)

    def get_or_404(self, pk: str) -> ActionClass:
        """Get an action by its primary key or raise a 404 error."""
        return self.klass.get_or_404(pk)


def get_action_manager() -> ActionManager[Action]:
    """Get the action manager."""
    return ActionManager[Action](Action)
