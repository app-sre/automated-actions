from typing import Self

from pydantic import BaseModel
from pynamodb.attributes import UnicodeAttribute

from automated_actions.api.models._base import Table


class UserSchemaIn(BaseModel):
    name: str
    username: str
    email: str


class UserSchemaOut(UserSchemaIn):
    created_at: float
    updated_at: float


class User(Table[UserSchemaIn, UserSchemaOut]):
    """User."""

    class Meta(Table.Meta):
        table_name = "aa-user"
        schema_out = UserSchemaOut

    @classmethod
    def load(cls, username: str, name: str, email: str) -> Self:
        try:
            user = cls.get(email)
            user.update(actions=[cls.name.set(name), cls.username.set(username)])
            return user
        except cls.DoesNotExist:
            return cls.create(UserSchemaIn(name=name, username=username, email=email))

    email = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    username = UnicodeAttribute()
