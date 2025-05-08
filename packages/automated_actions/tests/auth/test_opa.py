import re
from unittest.mock import MagicMock

import httpx
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


def test_opa_get_opa_result_bad_status_code(opa: OPA) -> None:
    assert not opa.get_opa_result(httpx.Response(status_code=403))


def test_opa_get_opa_result_bad_response(opa: OPA) -> None:
    assert not opa.get_opa_result(httpx.Response(status_code=200, text="whatever"))


def test_opa_get_opa_result_boolean(opa: OPA) -> None:
    assert (
        opa.get_opa_result(httpx.Response(status_code=200, json={"result": True}))
        is True
    )


def test_opa_get_opa_result_dict(opa: OPA) -> None:
    assert opa.get_opa_result(
        httpx.Response(status_code=200, json={"result": {"foo": "bar"}})
    ) == {"foo": "bar"}


def test_opa_get_opa_result_list(opa: OPA) -> None:
    assert opa.get_opa_result(
        httpx.Response(status_code=200, json={"result": ["foo", "bar"]})
    ) == ["foo", "bar"]


def test_opa_get_opa_result_none(opa: OPA) -> None:
    assert (
        opa.get_opa_result(httpx.Response(status_code=200, json={"result": None}))
        is None
    )


@pytest.mark.asyncio
async def test_opa_user_is_authorized(
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
    user_is_authorized = await opa.user_is_authorized(
        user=user, obj="endpoint", params={"foo": "bar"}
    )
    assert user_is_authorized is True


@pytest.mark.asyncio
async def test_opa_user_is_authorized_exception(
    opa: OPA, usermodel: MockUserModel, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    httpx_mock.add_response(
        method="POST",
        json={"result": {"whatever": "foo"}},
    )
    with pytest.raises(HTTPException):
        await opa.user_is_authorized(user=user, obj="endpoint", params={"foo": "bar"})


@pytest.mark.asyncio
async def test_opa_user_objects(
    opa: OPA, usermodel: MockUserModel, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    httpx_mock.add_response(
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
            }
        },
        json={"result": ["action-1", "action-2"]},
    )
    user_objects = await opa.user_objects(user=user)
    assert user_objects == ["action-1", "action-2"]


@pytest.mark.asyncio
async def test_opa_user_objects_exception(
    opa: OPA, usermodel: MockUserModel, httpx_mock: HTTPXMock
) -> None:
    user = usermodel.load("test_user")
    httpx_mock.add_response(
        method="POST",
        json={"result": {"whatever": "foo"}},
    )
    with pytest.raises(HTTPException):
        await opa.user_objects(user=user)


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
        url=re.compile(r".*allow"),
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

    # user_objects
    httpx_mock.add_response(
        url=re.compile(r".*objects"),
        method="POST",
        match_json={
            "input": {
                "username": "test_user",
            }
        },
        json={"result": ["action-1", "action-2"]},
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
        url=re.compile(r".*allow"),
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
        json={"result": False},
    )

    with pytest.raises(HTTPException) as excinfo:
        await opa(request=mock_request, user=user)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert user.allowed_actions == []
