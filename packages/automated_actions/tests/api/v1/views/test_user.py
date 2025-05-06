from collections.abc import Callable

from fastapi import FastAPI, status
from fastapi.testclient import TestClient


def test_user_me(app: FastAPI, client: Callable[[FastAPI], TestClient]) -> None:
    response = client(app).get(app.url_path_for("me"))
    assert response.status_code == status.HTTP_200_OK
    user = response.json()
    # see conftest.py for the user stub data
    assert user == {
        "name": "test user",
        "username": "test_user",
        "email": "test@example.com",
        "created_at": 1.0,
        "updated_at": 2.0,
        "allowed_actions": ["action1", "action2"],
    }
