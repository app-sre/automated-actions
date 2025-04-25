from pynamodb.models import Model

from ._action import Action, ActionSchemaIn, ActionSchemaOut, ActionStatus
from ._base import Table
from ._user import User, UserSchemaOut

ALL_TABLES: list[type[Model]] = [User, Action]

__all__ = [
    "ALL_TABLES",
    "Action",
    "ActionSchemaIn",
    "ActionSchemaOut",
    "ActionStatus",
    "Table",
    "User",
    "UserSchemaOut",
]
