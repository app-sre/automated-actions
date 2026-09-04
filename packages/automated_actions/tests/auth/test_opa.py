from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status

from automated_actions.auth import OPA

if TYPE_CHECKING:
    from pytest_httpx2 import HTTPXMock

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
    """Denial is an authorization (403) failure, distinct from authentication (401)."""
    with pytest.raises(HTTPException) as excinfo:
        opa.user_is_authorized({"authorized": False})
    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN


def test_opa_user_is_authorized_missing_result(opa: OPA) -> None:
    with pytest.raises(HTTPException) as excinfo:
        opa.user_is_authorized({"foobar": False})
    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN


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
async def test_opa_call_with_extra_params(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock, httpx_mock: HTTPXMock
) -> None:
    """extra_params (e.g. an action's owner) must be merged into the params sent to OPA."""
    user = usermodel.load("test_user")
    route_mock = MagicMock()
    route_mock.operation_id = "action-detail"
    mock_request.__getitem__.return_value = route_mock
    mock_request.path_params = {"action_id": "1"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/actions/1"

    httpx_mock.add_response(
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
                "name": "test user",
                "email": "test@example.com",
                "created_at": 1,
                "updated_at": 2,
                "obj": "action-detail",
                "params": {"action_id": "1", "owner": "test_user"},
            }
        },
        json={"result": {"authorized": True, "within_rate_limits": True}},
    )
    await opa(request=mock_request, user=user, extra_params={"owner": "test_user"})


def _fake_query_param(
    alias: str, default: object, *, required: bool = False
) -> MagicMock:
    """Build a fake FastAPI ModelField, as found in APIRoute.dependant.query_params."""
    field = MagicMock()
    field.alias = alias
    field.field_info.is_required.return_value = required
    field.default = default
    return field


@pytest.mark.asyncio
async def test_opa_call_backfills_missing_optional_query_param_defaults(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock, httpx_mock: HTTPXMock
) -> None:
    """A client may omit an optional query param and rely on the server-side default.

    E.g. api_version="v1" on openshift-workload-delete. OPA's valid_params policy
    treats a missing key as "does not match", even against a wildcard pattern, so
    input.params must reflect the effective (defaulted) value, not the raw wire value.
    """
    user = usermodel.load("test_user")
    route_mock = MagicMock()
    route_mock.operation_id = "endpoint"
    route_mock.dependant.query_params = [
        _fake_query_param("api_version", "v1"),
        _fake_query_param("required_field", ..., required=True),
    ]
    mock_request.__getitem__.return_value = route_mock
    mock_request.path_params = {"foo": "bar"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/endpoint"

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
                "params": {"foo": "bar", "api_version": "v1"},
            }
        },
        json={"result": {"authorized": True, "within_rate_limits": True}},
    )
    await opa(request=mock_request, user=user)


@pytest.mark.asyncio
async def test_opa_call_does_not_override_explicit_query_param(
    opa: OPA, usermodel: MockUserModel, mock_request: MagicMock, httpx_mock: HTTPXMock
) -> None:
    """A value explicitly sent by the client must win over the declared default."""
    user = usermodel.load("test_user")
    route_mock = MagicMock()
    route_mock.operation_id = "endpoint"
    route_mock.dependant.query_params = [_fake_query_param("api_version", "v1")]
    mock_request.__getitem__.return_value = route_mock
    mock_request.path_params = {"foo": "bar"}
    mock_request.query_params = {"api_version": "v1000"}
    mock_request.url = MagicMock()
    mock_request.url.path = "/endpoint"

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
                "params": {"foo": "bar", "api_version": "v1000"},
            }
        },
        json={"result": {"authorized": True, "within_rate_limits": True}},
    )
    await opa(request=mock_request, user=user)


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

    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
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
