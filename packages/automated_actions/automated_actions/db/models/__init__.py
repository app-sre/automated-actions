from pynamodb.models import Model

from ._action import (
    Action,
    ActionManager,
    ActionSchemaIn,
    ActionSchemaOut,
    ActionStatus,
    get_action_manager,
)
from ._base import Table
from ._user import User, UserSchemaOut

ALL_TABLES: list[type[Model]] = [User, Action]

__all__ = [
    "ALL_TABLES",
    "Action",
    "ActionManager",
    "ActionSchemaIn",
    "ActionSchemaOut",
    "ActionStatus",
    "Table",
    "User",
    "UserSchemaOut",
    "get_action_manager",
]
