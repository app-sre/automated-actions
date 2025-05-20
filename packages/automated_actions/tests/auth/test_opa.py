from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status
from pytest_httpx import HTTPXMock

from automated_actions.auth import OPA
from tests.conftest import MockUserModel


@pytest.fixture
def opa(usermodel: MockUserModel) -> OPA:
    return OPA[usermodel](opa_host="http://dev.com", skip_endpoints=["/skip-me"])  # type: ignore[valid-type]


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        ("/skip-me", True),
        ("/do-not-skip-me", False),
    ],
)
def test_opa_should_skip_endpoint(opa: OPA, endpoint: str, *, expected: bool) -> None:
    assert opa.should_skip_endpoint(endpoint) == expected


@pytest.mark.asyncio
async def test_opa_query_opa(
    opa: OPA, usermodel: MockUserModel, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    httpx_mock.add_response(
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
                "name": "test user",
                "email": "test@example.com",
                "created_at": 1,
                "updated_at": 2,
                "obj": "endpoint",
                "params": {"foo": "bar"},
            }
        },
        json={"result": True},
    )
    result = await opa.query_opa(user=user, obj="endpoint", params={"foo": "bar"})
    assert result is True


def test_opa_user_is_authorized(opa: OPA) -> None:
    opa.user_is_authorized({"authorized": True})


def test_opa_user_is_authorized_denied(opa: OPA) -> None:
    with pytest.raises(HTTPException) as excinfo:
        opa.user_is_authorized({"authorized": False})
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_opa_user_is_authorized_missing_result(opa: OPA) -> None:
    with pytest.raises(HTTPException) as excinfo:
        opa.user_is_authorized({"foobar": False})
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_opa_user_is_within_rate_limits(opa: OPA) -> None:
    opa.user_is_within_rate_limits({"within_rate_limits": True})


def test_opa_user_is_within_rate_limits_denied(opa: OPA) -> None:
    with pytest.raises(HTTPException) as excinfo:
        opa.user_is_within_rate_limits({"within_rate_limits": False})
    assert excinfo.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_opa_user_is_within_rate_limits_missing_result(opa: OPA) -> None:
    with pytest.raises(HTTPException) as excinfo:
        opa.user_is_within_rate_limits({"foobar": False})
    assert excinfo.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.asyncio
async def test_opa_call(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    route_mock = MagicMock()
    route_mock.operation_id = "endpoint"
    mock_request.__getitem__.return_value = route_mock
    mock_request.path_params = {"foo": "bar"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/endpoint"

    # user_is_authorized
    httpx_mock.add_response(
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
                "name": "test user",
                "email": "test@example.com",
                "created_at": 1,
                "updated_at": 2,
                "obj": "endpoint",
                "params": {"foo": "bar"},
            }
        },
        json={
            "result": {
                "authorized": True,
                "within_rate_limits": True,
                "objects": ["action-1", "action-2"],
            }
        },
    )
    await opa(request=mock_request, user=user)
    assert user.allowed_actions == ["action-1", "action-2"]


@pytest.mark.asyncio
async def test_opa_call_skipped(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock
) -> None:
    user = usermodel.load("test_user")
    mock_request.url = MagicMock()
    mock_request.url.path = "/skip-me"

    await opa(request=mock_request, user=user)
    assert user.allowed_actions == []


@pytest.mark.asyncio
async def test_opa_call_not_authorized(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    route_mock = MagicMock()
    route_mock.operation_id = "endpoint"
    mock_request.__getitem__.return_value = route_mock
    mock_request.path_params = {"foo": "bar"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/endpoint"

    # user_is_authorized
    httpx_mock.add_response(
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
                "name": "test user",
                "email": "test@example.com",
                "created_at": 1,
                "updated_at": 2,
                "obj": "endpoint",
                "params": {"foo": "bar"},
            }
        },
        json={
            "result": {
                "authorized": False,
                "within_rate_limits": True,
                "objects": ["action-1", "action-2"],
            }
        },
    )

    with pytest.raises(HTTPException) as excinfo:
        await opa(request=mock_request, user=user)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert user.allowed_actions == []


@pytest.mark.asyncio
async def test_opa_call_rate_limit_exceeded(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    route_mock = MagicMock()
    route_mock.operation_id = "endpoint"
    mock_request.__getitem__.return_value = route_mock
    mock_request.path_params = {"foo": "bar"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/endpoint"

    # user_is_authorized
    httpx_mock.add_response(
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
                "name": "test user",
                "email": "test@example.com",
                "created_at": 1,
                "updated_at": 2,
                "obj": "endpoint",
                "params": {"foo": "bar"},
            }
        },
        json={
            "result": {
                "authorized": True,
                "within_rate_limits": False,
                "objects": ["action-1", "action-2"],
            }
        },
    )

    with pytest.raises(HTTPException) as excinfo:
        await opa(request=mock_request, user=user)

    assert excinfo.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert user.allowed_actions == []
