from datetime import UTC
from datetime import datetime as dt
from typing import Any

from pydantic import BaseModel
from pynamodb.attributes import NumberAttribute, UnicodeAttribute, UnicodeSetAttribute
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex
from pynamodb.models import Model

from automated_actions.api.models import Table
from automated_actions.api.models.base import ALL_TABLES


class UserSchemaIn(BaseModel):
    name: str
    username: str
    email: str
    roles: list[str]


class UserSchemaOut(UserSchemaIn):
    created_at: float
    updated_at: float


class UsernameIndex(GlobalSecondaryIndex["User"]):
    """Secondary index for UserTable"""

    class Meta:
        index_name = "username-index"
        read_capacity_units = 10
        write_capacity_units = 10
        projection = AllProjection()

    name = UnicodeAttribute(hash_key=True)
    updated_at = NumberAttribute(range_key=True)


class User(Model, Table[UserSchemaIn, UserSchemaOut]):
    """User."""

    class Meta(Table.Meta):
        table_name = "aa-user"
        schema_out = UserSchemaOut

    @staticmethod
    def _pre_create(values: dict[str, Any]) -> dict[str, Any]:
        timestamp_now = dt.now(UTC).timestamp()
        values["created_at"] = timestamp_now
        values["updated_at"] = timestamp_now
        return values

    email = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    username = UnicodeAttribute()
    roles = UnicodeSetAttribute()

    created_at = NumberAttribute()
    updated_at = NumberAttribute()

    # TODO @cassing: brauche ich den Index?
    username_index = UsernameIndex()


ALL_TABLES.append(User)
