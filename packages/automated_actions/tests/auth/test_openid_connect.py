# ruff: noqa: S106


from datetime import UTC
from datetime import datetime as dt
from datetime import timedelta as td
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from httpx import HTTPStatusError
from pytest_httpx import HTTPXMock
from pytest_mock import MockerFixture

from automated_actions.auth import OpenIDConnect

from .conftest import MockUserModel


@pytest.fixture
def openid_connect(usermodel: type, httpx_mock: HTTPXMock) -> OpenIDConnect:
    httpx_mock.add_response(
        url="http://dev.com/.well-known/openid-configuration",
        json={
            "authorization_endpoint": "http://dev.com/authorize",
            "token_endpoint": "http://dev.com/token",
            "userinfo_endpoint": "http://dev.com/userinfo",
        },
    )
    return OpenIDConnect[usermodel](  # type: ignore[valid-type]
        issuer="http://dev.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        session_secret="test_session_secret",
        session_timeout_secs=60,
        user_model=usermodel,
    )


def test_openid_connect_init_endpoints(openid_connect: OpenIDConnect) -> None:
    assert openid_connect.authorization_endpoint
    assert openid_connect.token_endpoint
    assert openid_connect.userinfo_endpoint


def test_openid_connect_init_router(openid_connect: OpenIDConnect) -> None:
    assert len(openid_connect.router.routes) == 3  # noqa: PLR2004
    assert isinstance(openid_connect.router.routes[0], APIRoute)
    assert openid_connect.router.routes[0].path == "/login"
    assert openid_connect.router.routes[0].endpoint == openid_connect.login
    assert isinstance(openid_connect.router.routes[1], APIRoute)
    assert openid_connect.router.routes[1].path == "/callback"
    assert openid_connect.router.routes[1].endpoint == openid_connect.callback
    assert isinstance(openid_connect.router.routes[2], APIRoute)
    assert openid_connect.router.routes[2].path == "/logout"
    assert openid_connect.router.routes[2].endpoint == openid_connect.logout


@pytest.mark.asyncio
async def test_openid_connect_call(
    openid_connect: OpenIDConnect,
    mock_request: MagicMock,
    mocker: MockerFixture,
    usermodel: MockUserModel,
) -> None:
    mocker.patch.object(
        openid_connect, "get_user_info", return_value=usermodel.load("test_user")
    )
    session = openid_connect.session_serializer.dumps("session_data")
    mock_request.cookies.get.return_value = session
    user_info = await openid_connect(mock_request)
    assert user_info.username == "test_user"


@pytest.mark.asyncio
async def test_openid_connect_call_no_session(
    openid_connect: OpenIDConnect, mock_request: MagicMock
) -> None:
    mock_request.cookies.get.return_value = None
    mock_request.url_for.return_value = "/login"
    mock_request.url = "/next"
    with pytest.raises(HTTPException) as exc_info:
        await openid_connect(mock_request)
    assert exc_info.value.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert exc_info.value.headers
    assert exc_info.value.headers["Location"] == "/login?next_url=/next"


@pytest.mark.asyncio
async def test_openid_connect_call_bad_session(
    openid_connect: OpenIDConnect, mock_request: MagicMock
) -> None:
    mock_request.cookies.get.return_value = None
    mock_request.url_for.return_value = "/login"
    mock_request.url = "/next"
    mock_request.cookies.get.return_value = "invalid_session"
    with pytest.raises(HTTPException) as exc_info:
        await openid_connect(mock_request)
    assert exc_info.value.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert exc_info.value.headers
    assert exc_info.value.headers["Location"] == "/login?next_url=/next"


@pytest.mark.asyncio
async def test_openid_connect_call_bad_token(
    openid_connect: OpenIDConnect,
    mock_request: MagicMock,
    mocker: MockerFixture,
) -> None:
    mock_request.cookies.get.return_value = None
    mock_request.url_for.return_value = "/login"
    mock_request.url = "/next"

    mocker.patch.object(
        openid_connect,
        "get_user_info",
        side_effect=HTTPStatusError(
            "Bad token", request=MagicMock(), response=MagicMock()
        ),
    )
    session = openid_connect.session_serializer.dumps("session_data")
    mock_request.cookies.get.return_value = session

    with pytest.raises(HTTPException) as exc_info:
        await openid_connect(mock_request)
    assert exc_info.value.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert exc_info.value.headers
    assert exc_info.value.headers["Location"] == "/login?next_url=/next"


def test_openid_connect_login(
    openid_connect: OpenIDConnect, client: TestClient
) -> None:
    response = client.get(
        "/api/v1/auth/login", params={"next_url": "/foobar"}, follow_redirects=False
    )
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert (
        response.headers["Location"]
        == f"{openid_connect.authorization_endpoint}?response_type=code&scope=openid%20email%20profile&client_id=test_client_id&redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fv1%2Fauth%2Fcallback&state=/foobar"
    )


def test_openid_connect_callback_endpoint(
    openid_connect: OpenIDConnect, client: TestClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=openid_connect.token_endpoint,
        match_headers={
            # Basic auth with client_id:client_secret
            "Authorization": "Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0"
        },
        json={"access_token": "not_a_real_token"},
    )

    response = client.get(
        "/api/v1/auth/callback",
        params={"code": "test_code", "state": "/foobar"},
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["Location"] == "/foobar"
    assert response.cookies["session"]


def test_openid_connect_callback_endpoint_error(
    openid_connect: OpenIDConnect, client: TestClient, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=openid_connect.token_endpoint,
        status_code=status.HTTP_400_BAD_REQUEST,
    )

    response = client.get(
        "/api/v1/auth/callback",
        params={"code": "test_code", "state": "/foobar"},
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_openid_connect_logout_endpoint(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/logout",
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["Location"] == "/"
    assert not response.cookies


def test_openid_connect_get_user_info(
    openid_connect: OpenIDConnect, httpx_mock: HTTPXMock
) -> None:
    access_token = jwt.encode(
        {
            "preferred_username": "username",
            "name": "name",
            "email": "email",
            "iss": "issuer",
            "exp": dt.now(tz=UTC) + td(minutes=5),
            "iat": dt.now(tz=UTC),
        },
        "not-a-secret",
        algorithm="HS256",
    )
    httpx_mock.add_response(
        url=openid_connect.userinfo_endpoint,
        match_headers={"Authorization": f"Bearer {access_token}"},
    )
    user_info = openid_connect.get_user_info(access_token)
    assert user_info.username == "username"


def test_openid_connect_get_user_info_error(
    openid_connect: OpenIDConnect, httpx_mock: HTTPXMock
) -> None:
    httpx_mock.add_response(
        url=openid_connect.userinfo_endpoint, status_code=status.HTTP_400_BAD_REQUEST
    )
    with pytest.raises(HTTPStatusError):
        openid_connect.get_user_info("access_token")
