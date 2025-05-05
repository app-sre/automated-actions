from collections.abc import Iterable
from typing import Any, Self
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from pydantic import BaseModel, Field


class MockUserModel(BaseModel):
    username: str
    allowed_actions: list[str] = Field([], exclude=True)

    @classmethod
    def load(cls, username: str, **_: Any) -> Self:
        return cls(username=username)

    def dump(self) -> Self:
        return self

    def set_allowed_actions(self, allowed_actions: Iterable[str]) -> None:
        self.allowed_actions = list(allowed_actions)


@pytest.fixture
def usermodel() -> type[MockUserModel]:
    return MockUserModel


@pytest.fixture
def mock_request() -> Request:
    request = MagicMock(spec=Request)
    request.headers = {}

    return request
