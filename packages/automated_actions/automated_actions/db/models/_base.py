from datetime import UTC
from datetime import datetime as dt
from typing import Any, ClassVar, Self

from fastapi import HTTPException
from pydantic import BaseModel as PydanticBaseModel
from pynamodb.attributes import NumberAttribute
from pynamodb.exceptions import DoesNotExist
from pynamodb.expressions.condition import Condition
from pynamodb.expressions.update import Action as PynamoAction
from pynamodb.models import Model as PynamoModel

from automated_actions.config import settings


class Table[SchemaIn: PydanticBaseModel, SchemaOut: PydanticBaseModel](PynamoModel):
    """PynamoDB - FastAPI integration."""

    created_at = NumberAttribute()
    updated_at = NumberAttribute()

    class Meta:
        host = settings.dynamodb_url
        region = settings.dynamodb_aws_region
        aws_access_key_id = settings.dynamodb_aws_access_key_id
        aws_secret_access_key = settings.dynamodb_aws_secret_access_key
        tags: ClassVar = {"app": "automated-actions"}
        schema_out: Any

    @staticmethod
    def _pre_create(values: dict[str, Any]) -> dict[str, Any]:
        timestamp_now = dt.now(UTC).timestamp()
        values["created_at"] = timestamp_now
        values["updated_at"] = timestamp_now
        return values

    def dump(self) -> SchemaOut:
        return self.Meta.schema_out(**self.attribute_values)

    @classmethod
    def create(cls, item: SchemaIn) -> Self:
        data = cls._pre_create(item.model_dump(exclude_none=True))
        db_item = cls(**data)
        db_item.save()
        return db_item

    def update(
        self,
        actions: list[PynamoAction],
        condition: Condition | None = None,
        *,
        add_version_condition: bool = True,
    ) -> Any:
        actions.append(Table.updated_at.set(dt.now(UTC).timestamp()))
        return super().update(
            actions, condition, add_version_condition=add_version_condition
        )

    @classmethod
    def get_or_404(cls, pk: str) -> Self:
        try:
            item = cls.get(pk)
        except DoesNotExist:
            raise HTTPException(status_code=404, detail="Item not found") from None
        return item
