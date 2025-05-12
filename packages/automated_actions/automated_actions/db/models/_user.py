from typing import Self

from pydantic import BaseModel
from pynamodb.attributes import ListAttribute, UnicodeAttribute

from automated_actions.config import settings
from automated_actions.db.models._base import Table


class UserSchemaIn(BaseModel):
    name: str
    username: str
    email: str


class UserSchemaOut(UserSchemaIn):
    created_at: float
    updated_at: float
    allowed_actions: list[str]


class User(Table[UserSchemaIn, UserSchemaOut]):
    """User."""

    class Meta(Table.Meta):
        table_name = f"aa-user-{settings.environment}"
        schema_out = UserSchemaOut

    @classmethod
    def load(cls, username: str, name: str, email: str) -> Self:
        try:
            user = cls.get(email)
            user.update(actions=[cls.name.set(name), cls.username.set(username)])
            return user
        except cls.DoesNotExist:
            return cls.create(UserSchemaIn(name=name, username=username, email=email))

    def set_allowed_actions(self, allowed_actions: list[str]) -> None:
        self.update(actions=[User.allowed_actions.set(allowed_actions)])

    email = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    username = UnicodeAttribute()
    allowed_actions: ListAttribute = ListAttribute(default=list)
