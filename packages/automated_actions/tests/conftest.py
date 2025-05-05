# ruff: noqa: S105, PLC0415, TD003
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock

os.environ["AA_OIDC_ISSUER"] = "http://dev.com"
os.environ["AA_OIDC_CLIENT_ID"] = "test_client_id"
os.environ["AA_OIDC_CLIENT_SECRET"] = "test_client_secret"
os.environ["AA_SESSION_SECRET"] = "test_session_secret"
os.environ["AA_TOKEN_SECRET"] = "test_token_secret"


@pytest.fixture
def client(httpx_mock: HTTPXMock) -> Generator[TestClient, None, None]:
    from automated_actions.__main__ import app  # noqa: PLC2701
    from automated_actions.db.models import ALL_TABLES

    # TODO(Chris): Figure out how to mock the DynamoDB tables
    ALL_TABLES.clear()

    # Mock the OpenID Connect configuration
    httpx_mock.add_response(
        url="http://dev.com/.well-known/openid-configuration",
        json={
            "authorization_endpoint": "http://dev.com/authorize",
            "token_endpoint": "http://dev.com/token",
            "userinfo_endpoint": "http://dev.com/userinfo",
        },
    )

    with TestClient(app) as client:
        yield client
