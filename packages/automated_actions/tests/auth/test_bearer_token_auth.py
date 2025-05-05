from datetime import UTC
from datetime import datetime as dt
from datetime import timedelta as td
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, status

from automated_actions.auth import BearerTokenAuth


@pytest.fixture
def bearer_token_auth(usermodel: type) -> BearerTokenAuth:
    return BearerTokenAuth[usermodel](  # type: ignore[valid-type]
        issuer="http://dev.com",
        secret="secret",  # noqa: S106
        user_model=usermodel,
    )


@pytest.mark.asyncio
async def test_bearer_auth_valid_token(
    bearer_token_auth: BearerTokenAuth, mock_request: MagicMock
) -> None:
    token = bearer_token_auth.create_token(
        name="test_token",
        username="test_user",
        email="test@test.com",
        expiration=dt.now(tz=UTC) + td(minutes=5),
    )

    mock_request.headers["Authorization"] = f"Bearer {token}"

    # Methode aufrufen
    user = await bearer_token_auth(mock_request)

    # Assertions
    assert user is not None
    assert user.username == "test_user"


@pytest.mark.asyncio
async def test_bearer_auth_invalid_header(
    bearer_token_auth: BearerTokenAuth, mock_request: MagicMock
) -> None:
    mock_request.headers["Authorization"] = "InvalidHeader"

    with pytest.raises(HTTPException) as exc_info:
        await bearer_token_auth(mock_request)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Invalid authorization header."


@pytest.mark.asyncio
async def test_bearer_auth_missing_authorization(
    bearer_token_auth: BearerTokenAuth, mock_request: MagicMock
) -> None:
    mock_request.headers = {}

    user = await bearer_token_auth(mock_request)

    # Assertions
    assert user is None


@pytest.mark.asyncio
async def test_bearer_auth_invalid_token(
    bearer_token_auth: BearerTokenAuth, mock_request: MagicMock
) -> None:
    mock_request.headers["Authorization"] = "Bearer invalid_token"

    user = await bearer_token_auth(mock_request)

    # Assertions
    assert user is None


@pytest.mark.asyncio
async def test_bearer_auth_expired_token(
    bearer_token_auth: BearerTokenAuth, mock_request: MagicMock
) -> None:
    token = bearer_token_auth.create_token(
        name="test_token",
        username="test_user",
        email="test@test.com",
        expiration=dt.now(tz=UTC) - td(minutes=5),
    )
    mock_request.headers["Authorization"] = f"Bearer {token}"

    user = await bearer_token_auth(mock_request)

    # Assertions
    assert user is None
