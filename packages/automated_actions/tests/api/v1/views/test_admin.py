from collections.abc import Callable
from datetime import UTC
from datetime import datetime as dt

import jwt
from fastapi import FastAPI, status
from fastapi.testclient import TestClient


def test_admin_create_token(
    app: FastAPI, client: Callable[[FastAPI], TestClient]
) -> None:
    token_data = {
        "name": "test-token",
        "username": "service-account",
        "email": "service@example.com",
        "expiration": "2100-12-31T23:59:59Z",
    }
    now = int(dt.now(tz=UTC).timestamp())
    expiration_timestamp = int(dt.fromisoformat(token_data["expiration"]).timestamp())
    response = client(app).post(app.url_path_for("create_token"), json=token_data)
    assert response.status_code == status.HTTP_200_OK
    encoded_token = response.json()
    assert isinstance(encoded_token, str)
    token = jwt.decode(
        encoded_token,
        algorithms="HS256",
        options={
            "verify_signature": False,
            "require": ["exp", "iat", "iss"],
        },
    )
    assert token["preferred_username"] == token_data["username"]
    assert token["name"] == token_data["name"]
    assert token["email"] == token_data["email"]
    assert token["exp"] == expiration_timestamp
    assert token["iat"] >= now
    assert token["iss"] == "http://dev.com"
