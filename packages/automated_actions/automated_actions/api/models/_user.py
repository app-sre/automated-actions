from typing import Self

from pydantic import BaseModel
from pynamodb.attributes import UnicodeAttribute, UnicodeSetAttribute

from automated_actions.api.models._base import Table
from automated_actions.auth import AccessToken
from automated_actions.config import settings


class UserSchemaIn(BaseModel):
    name: str
    username: str
    email: str
    roles: set[str]


class UserSchemaOut(UserSchemaIn):
    created_at: float
    updated_at: float


class User(Table[UserSchemaIn, UserSchemaOut]):
    """User."""

    class Meta(Table.Meta):
        table_name = "aa-user"
        schema_out = UserSchemaOut

    @classmethod
    def load(cls, access_token: AccessToken) -> Self:
        def _get_roles(access_token: AccessToken) -> set[str]:
            return {
                role
                for role in access_token.realm_access.get("roles", [])
                if role.startswith(settings.app_interface_role_prefix)
            }

        try:
            user = cls.get(access_token.email)
            user.update(
                actions=[
                    cls.name.set(access_token.name),
                    cls.username.set(access_token.preferred_username),
                    cls.roles.set(_get_roles(access_token)),
                ]
            )
            return user
        except cls.DoesNotExist:
            return cls.create(
                UserSchemaIn(
                    name=access_token.name,
                    username=access_token.preferred_username,
                    email=access_token.email,
                    roles=_get_roles(access_token),
                )
            )

    email = UnicodeAttribute(hash_key=True)
    name = UnicodeAttribute()
    username = UnicodeAttribute()
    roles = UnicodeSetAttribute()
