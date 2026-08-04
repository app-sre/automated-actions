# ruff: file-ignore[hardcoded-password-func-arg]


from datetime import UTC
from datetime import datetime as dt
from datetime import timedelta as td
from typing import TYPE_CHECKING
from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from fastapi import FastAPI, HTTPException, status
from fastapi.routing import APIRoute
from httpx2 import HTTPStatusError
from starlette.datastructures import URL

from automated_actions.auth import OpenIDConnect

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from pytest_httpx2 import HTTPXMock
    from pytest_mock import MockerFixture

    from tests.conftest import MockUserModel


@pytest.fixture
def openid_connect(usermodel: type) -> OpenIDConnect:
    return OpenIDConnect[usermodel](  # type: ignore[valid-type]
        issuer="http://dev.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        session_secret="test_session_secret",
        session_timeout_secs=60,
        authorization_endpoint="http://dev.com/authorize",
        token_endpoint="http://dev.com/token",
        userinfo_endpoint="http://dev.com/userinfo",
        user_model=usermodel,
    )


@pytest.mark.asyncio
async def test_openid_connect_create(httpx_mock: HTTPXMock, usermodel: type) -> None:
    httpx_mock.add_response(
        url="http://dev.com/.well-known/openid-configuration",
        json={
            "authorization_endpoint": "http://dev.com/authorize",
            "token_endpoint": "http://dev.com/token",
            "userinfo_endpoint": "http://dev.com/userinfo",
        },
    )
    openid_connect = await OpenIDConnect[usermodel].create(  # type: ignore[valid-type]
        issuer="http://dev.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        session_secret="test_session_secret",
        session_timeout_secs=60,
        user_model=usermodel,
    )
    assert openid_connect.authorization_endpoint
    assert openid_connect.token_endpoint
    assert openid_connect.userinfo_endpoint


def test_openid_connect_init_endpoints(openid_connect: OpenIDConnect) -> None:
    assert openid_connect.authorization_endpoint
    assert openid_connect.token_endpoint
    assert openid_connect.userinfo_endpoint


def test_openid_connect_init_router(openid_connect: OpenIDConnect) -> None:
    assert len(openid_connect.router.routes) == 3  # ruff: ignore[magic-value-comparison]
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
    mock_request.url = URL("/")
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
    mock_request.url = URL("/next")
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
    mock_request.url = URL("/next")
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
    mock_request.url = URL("/next")

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
    openid_connect: OpenIDConnect,
    full_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
) -> None:
    response = client(full_app).get(
        "/api/v1/auth/login", params={"next_url": "/foobar"}, follow_redirects=False
    )
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT

    query = parse_qs(urlparse(response.headers["Location"]).query)
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["client_id"] == ["test_client_id"]
    assert query["redirect_uri"] == ["http://testserver/api/v1/auth/callback"]

    state_token = query["state"][0]
    assert response.cookies["oidc_state"] == state_token
    state_data = openid_connect.state_serializer.loads(state_token)
    assert state_data["next_url"] == "/foobar"


def test_openid_connect_login_rejects_open_redirect(
    openid_connect: OpenIDConnect,
    full_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
) -> None:
    """FIND-003: an absolute/off-site next_url must not survive into state."""
    response = client(full_app).get(
        "/api/v1/auth/login",
        params={"next_url": "https://evil.example.com"},
        follow_redirects=False,
    )
    state_token = parse_qs(urlparse(response.headers["Location"]).query)["state"][0]
    state_data = openid_connect.state_serializer.loads(state_token)
    assert state_data["next_url"] == "/"


def test_openid_connect_callback_endpoint(
    openid_connect: OpenIDConnect,
    full_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url=openid_connect.token_endpoint,
        match_headers={
            # Basic auth with client_id:client_secret
            "Authorization": "Basic dGVzdF9jbGllbnRfaWQ6dGVzdF9jbGllbnRfc2VjcmV0"
        },
        json={"access_token": "not_a_real_token"},
    )

    test_client = client(full_app)
    login_response = test_client.get(
        "/api/v1/auth/login", params={"next_url": "/foobar"}, follow_redirects=False
    )
    state_token = login_response.cookies["oidc_state"]

    response = test_client.get(
        "/api/v1/auth/callback",
        params={"code": "test_code", "state": state_token},
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["Location"] == "/foobar"
    assert response.cookies["session"]
    assert "oidc_state" not in response.cookies


def test_openid_connect_callback_endpoint_error(
    openid_connect: OpenIDConnect,
    full_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url=openid_connect.token_endpoint,
        status_code=status.HTTP_400_BAD_REQUEST,
    )

    test_client = client(full_app)
    login_response = test_client.get(
        "/api/v1/auth/login", params={"next_url": "/foobar"}, follow_redirects=False
    )
    state_token = login_response.cookies["oidc_state"]

    response = test_client.get(
        "/api/v1/auth/callback",
        params={"code": "test_code", "state": state_token},
        follow_redirects=False,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_openid_connect_callback_rejects_missing_state_cookie(
    full_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
) -> None:
    """FIND-003: a callback with no matching oidc_state cookie is login-CSRF."""
    response = client(full_app).get(
        "/api/v1/auth/callback",
        params={"code": "attacker_code", "state": "/foobar"},
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_openid_connect_callback_rejects_tampered_state(
    full_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
) -> None:
    """FIND-003: an unsigned state is rejected.

    This holds even if an attacker manages to also set a matching cookie value.
    """
    test_client = client(full_app)
    forged_state = "not-a-validly-signed-token"
    test_client.cookies.set("oidc_state", forged_state)

    response = test_client.get(
        "/api/v1/auth/callback",
        params={"code": "attacker_code", "state": forged_state},
        follow_redirects=False,
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_openid_connect_logout_endpoint(
    full_app: FastAPI, client: Callable[[FastAPI], TestClient]
) -> None:
    response = client(full_app).get(
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
