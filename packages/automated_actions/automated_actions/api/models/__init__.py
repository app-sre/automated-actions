from pynamodb.models import Model

from ._base import Table
from ._task import Task, TaskSchemaIn, TaskSchemaOut, TaskStatus
from ._user import User, UserSchemaOut

ALL_TABLES: list[type[Model]] = [User, Task]

__all__ = [
    "ALL_TABLES",
    "Table",
    "Task",
    "TaskSchemaIn",
    "TaskSchemaOut",
    "TaskStatus",
    "User",
    "UserSchemaOut",
]
