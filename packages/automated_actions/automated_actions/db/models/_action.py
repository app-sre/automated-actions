import uuid
from enum import StrEnum
from typing import Any

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
        self.update(actions=[Action.status.set(status.value), Action.result.set(result)])

    action_id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    status = UnicodeAttribute()
    result = UnicodeAttribute(null=True)
    owner = UnicodeAttribute()
    owner_index = OwnerIndex()
