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
        table_name = f"aa-{settings.environment}-user"
        schema_out = UserSchemaOut

    @classmethod
    def load(cls, username: str, name: str, email: str) -> Self:
        try:
            user = cls.get(email)
            if user.username == username and user.name == name:
                # avoid unnecessary updates
                return user
            user.update(actions=[cls.name.set(name), cls.username.set(username)])
            return user
        except cls.DoesNotExist:
            return cls.create(UserSchemaIn(name=name, username=username, email=email))

    def set_allowed_actions(self, allowed_actions: list[str]) -> None:
        if set(allowed_actions) == set(self.allowed_actions):
            # avoid unnecessary update
            return
        self.update(actions=[User.allowed_actions.set(allowed_actions)])

    # We use the user's email as key because it is unique
    # and generally available in the OIDC providers.
    email = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    username = UnicodeAttribute()
    # The allowed_actions list gets updated via the OPA policy engine
    # and contains the actions that the user is really allowed to perform.
    # It's for debugging purposes and to expose the list of actions to the user
    # via the `me` endpoint.
    # It is not used for authorization, which is done via OPA policies.
    allowed_actions: ListAttribute = ListAttribute(default=list)
