from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from automated_actions.db.models import (
    ActionManager,
    ActionSchemaOut,
    ActionStatus,
    get_action_manager,
)


class ActionStub(ActionSchemaOut):
    """Stub for Action model."""

    def dump(self) -> ActionSchemaOut:
        return self

    @classmethod
    def find_by_owner_and_status(
        cls, owner_email: str, status: str
    ) -> list[ActionStub]:
        """Stub method to return a list of actions."""
        return [
            ActionStub(
                action_id="1",
                name="test action",
                status=status,
                result="test result",
                owner=owner_email,
                created_at=1.0,
                updated_at=2.0,
            ),
            ActionStub(
                action_id="2",
                name="test action 2",
                status=status,
                result="test result 2",
                owner=owner_email,
                created_at=1.0,
                updated_at=2.0,
            ),
        ]

    @classmethod
    def get_or_404(cls, action_id: str) -> ActionStub:
        """Stub method to return an action by its primary key."""
        if action_id == "1":
            return ActionStub(
                action_id=action_id,
                name="test action",
                status=ActionStatus.RUNNING,
                result="test result",
                owner="test@example.com",
                created_at=1.0,
                updated_at=2.0,
            )
        raise ValueError("Action not found")

    def set_status(self, status: ActionStatus) -> None:
        """Stub method to set the status of an action."""
        self.status = status


@pytest.fixture
def testing_app(app: FastAPI) -> FastAPI:
    def _get_action_manager_test() -> ActionManager[ActionStub]:
        """Override the action manager for testing."""
        return ActionManager[ActionStub](ActionStub)

    app.dependency_overrides[get_action_manager] = _get_action_manager_test
    return app


def test_action_list(
    testing_app: FastAPI, client: Callable[[FastAPI], TestClient]
) -> None:
    response = client(testing_app).get(testing_app.url_path_for("action_list"))
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            "name": "test action",
            "owner": "test@example.com",
            "status": "RUNNING",
            "action_id": "1",
            "result": "test result",
            "created_at": 1.0,
            "updated_at": 2.0,
        },
        {
            "name": "test action 2",
            "owner": "test@example.com",
            "status": "RUNNING",
            "action_id": "2",
            "result": "test result 2",
            "created_at": 1.0,
            "updated_at": 2.0,
        },
    ]


def test_action_detail(
    testing_app: FastAPI, client: Callable[[FastAPI], TestClient]
) -> None:
    response = client(testing_app).get(
        testing_app.url_path_for("action_detail", action_id="1"),
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "name": "test action",
        "owner": "test@example.com",
        "status": "RUNNING",
        "action_id": "1",
        "result": "test result",
        "created_at": 1.0,
        "updated_at": 2.0,
    }


def test_action_cancel(
    testing_app: FastAPI, client: Callable[[FastAPI], TestClient]
) -> None:
    response = client(testing_app).post(
        testing_app.url_path_for("action_cancel", action_id="1"),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == ActionStatus.CANCELLED
