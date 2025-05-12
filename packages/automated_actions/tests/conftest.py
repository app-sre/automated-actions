# ruff: noqa: S105, S106, PLC0415
import os
from collections.abc import Callable, Iterable
from typing import Any, Self

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from pytest_httpx import HTTPXMock

os.environ["AA_ENVIRONMENT"] = "unit_tests"
os.environ["AA_OIDC_ISSUER"] = "http://dev.com"
os.environ["AA_OIDC_CLIENT_ID"] = "test_client_id"
os.environ["AA_OIDC_CLIENT_SECRET"] = "test_client_secret"
os.environ["AA_SESSION_SECRET"] = "test_session_secret"
os.environ["AA_TOKEN_SECRET"] = "test_token_secret"


class MockUserModel(BaseModel):
    username: str
    allowed_actions: list[str] = Field([], exclude=True)
    name: str = "test user"
    email: str = "test@example.com"
    created_at: float = 1
    updated_at: float = 2

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
def get_user_fake() -> Callable:
    def _get_user() -> MockUserModel:
        return MockUserModel(
            username="test_user", allowed_actions=["action1", "action2"]
        )

    return _get_user


@pytest.fixture
def get_authz_fake() -> Callable:
    def _get_authz() -> None: ...

    return _get_authz


@pytest.fixture
def full_app(httpx_mock: HTTPXMock) -> FastAPI:
    """FastAPI app with authentication and authorization setup but without DynamoDB."""
    from automated_actions.app_factory import create_app

    # Mock the OpenID Connect configuration
    httpx_mock.add_response(
        url="http://dev.com/.well-known/openid-configuration",
        json={
            "authorization_endpoint": "http://dev.com/authorize",
            "token_endpoint": "http://dev.com/token",
            "userinfo_endpoint": "http://dev.com/userinfo",
        },
    )

    return create_app(run_db_init=False)


@pytest.fixture
def app(get_user_fake: Callable, get_authz_fake: Callable, usermodel: type) -> FastAPI:
    """FastAPI app without authentication, authorization, and DynamoDB."""
    # import here to have all os.env variables set before importing the settings module
    from automated_actions.api.v1.dependencies import get_authz, get_user
    from automated_actions.app_factory import create_app
    from automated_actions.auth import BearerTokenAuth

    test_app = create_app(run_db_init=False, run_auth_init=False)
    test_app.dependency_overrides[get_user] = get_user_fake
    test_app.dependency_overrides[get_authz] = get_authz_fake
    test_app.state.token = BearerTokenAuth[usermodel](  # type: ignore[valid-type]
        issuer="http://dev.com", secret="fake", user_model=usermodel
    )
    return test_app


@pytest.fixture
def client() -> Callable[[FastAPI], TestClient]:
    """FastAPI TestClient for your app."""

    def _client(app: FastAPI) -> TestClient:
        client = TestClient(app)
        client.__enter__()  # noqa: PLC2801
        return client

    return _client


@pytest.fixture
def running_action() -> dict[str, Any]:
    """Fixture for a running action."""
    return {
        "name": "test action",
        "owner": "test@example.com",
        "status": "RUNNING",
        "action_id": "1",
        "result": "test result",
        "created_at": 1.0,
        "updated_at": 2.0,
    }
