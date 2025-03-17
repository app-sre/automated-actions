from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="UserSchemaOut")


@_attrs_define
class UserSchemaOut:
    """
    Attributes:
        name (str):
        username (str):
        email (str):
        created_at (float):
        updated_at (float):
    """

    name: str
    username: str
    email: str
    created_at: float
    updated_at: float
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        username = self.username

        email = self.email

        created_at = self.created_at

        updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "name": name,
            "username": username,
            "email": email,
            "created_at": created_at,
            "updated_at": updated_at,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: dict[str, Any]) -> T:
        d = src_dict.copy()
        name = d.pop("name")

        username = d.pop("username")

        email = d.pop("email")

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        user_schema_out = cls(
            name=name,
            username=username,
            email=email,
            created_at=created_at,
            updated_at=updated_at,
        )

        user_schema_out.additional_properties = d
        return user_schema_out

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
