import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from pynamodb.attributes import UnicodeAttribute
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex

from automated_actions.api.models._base import Table


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class TaskSchemaIn(BaseModel):
    name: str
    owner: str
    status: TaskStatus = TaskStatus.PENDING


class TaskSchemaOut(TaskSchemaIn):
    task_id: str
    result: str | None = None
    created_at: float
    updated_at: float


class OwnerIndex(GlobalSecondaryIndex["Task"]):
    class Meta:
        index_name = "owner-index"
        read_capacity_units = 10
        write_capacity_units = 10
        projection = AllProjection()

    owner = UnicodeAttribute(hash_key=True)
    status = UnicodeAttribute(range_key=True)


class Task(Table[TaskSchemaIn, TaskSchemaOut]):
    """Task."""

    class Meta(Table.Meta):
        table_name = "aa-task"
        schema_out = TaskSchemaOut

    @staticmethod
    def _pre_create(values: dict[str, Any]) -> dict[str, Any]:
        values = super(Task, Task)._pre_create(values)
        values["task_id"] = str(uuid.uuid4())
        return values

    def set_status(self, status: TaskStatus) -> None:
        self.update(actions=[Task.status.set(status.value)])

    task_id = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    status = UnicodeAttribute()
    result = UnicodeAttribute(null=True)
    owner = UnicodeAttribute()
    owner_index = OwnerIndex()
