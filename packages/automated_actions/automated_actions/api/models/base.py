from typing import Any, ClassVar, Self

from pydantic import BaseModel as PydanticBaseModel
from pynamodb.models import Model

from automated_actions.config import settings


class Table[SchemaIn: PydanticBaseModel, SchemaOut: PydanticBaseModel]:
    """PynamoDB - FastAPI integration."""

    class Meta:
        host = settings.dynamodb_url
        region = settings.dynamodb_aws_region
        aws_access_key_id = settings.dynamodb_aws_access_key_id
        aws_secret_access_key = settings.dynamodb_aws_secret_access_key
        tags: ClassVar = {"app": "automated-actions"}

    @staticmethod
    def _pre_create(values: dict[str, Any]) -> dict[str, Any]:
        return values

    def dump(self) -> SchemaOut:
        return self.Meta.schema_out(**self.attribute_values)  # type: ignore[attr-defined]

    @classmethod
    def create(cls, item: SchemaIn) -> Self:
        data = cls._pre_create(item.model_dump(exclude_none=True))
        db_item = cls(**data)
        db_item.save()  # type: ignore[attr-defined]
        return db_item


ALL_TABLES: list[type[Model]] = []
