from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.action_status import ActionStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="ActionSchemaOut")


@_attrs_define
class ActionSchemaOut:
    """
    Attributes:
        name (str):
        owner (str):
        action_id (str):
        created_at (float):
        updated_at (float):
        status (Union[Unset, ActionStatus]):
        result (Union[None, Unset, str]):
    """

    name: str
    owner: str
    action_id: str
    created_at: float
    updated_at: float
    status: Unset | ActionStatus = UNSET
    result: None | Unset | str = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        owner = self.owner

        action_id = self.action_id

        created_at = self.created_at

        updated_at = self.updated_at

        status: Unset | str = UNSET
        if not isinstance(self.status, Unset):
            status = self.status.value

        result: None | Unset | str
        if isinstance(self.result, Unset):
            result = UNSET
        else:
            result = self.result

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "name": name,
            "owner": owner,
            "action_id": action_id,
            "created_at": created_at,
            "updated_at": updated_at,
        })
        if status is not UNSET:
            field_dict["status"] = status
        if result is not UNSET:
            field_dict["result"] = result

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        owner = d.pop("owner")

        action_id = d.pop("action_id")

        created_at = d.pop("created_at")

        updated_at = d.pop("updated_at")

        _status = d.pop("status", UNSET)
        status: Unset | ActionStatus
        if isinstance(_status, Unset):
            status = UNSET
        else:
            status = ActionStatus(_status)

        def _parse_result(data: object) -> None | Unset | str:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | Unset | str, data)

        result = _parse_result(d.pop("result", UNSET))

        action_schema_out = cls(
            name=name,
            owner=owner,
            action_id=action_id,
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            result=result,
        )

        action_schema_out.additional_properties = d
        return action_schema_out

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
