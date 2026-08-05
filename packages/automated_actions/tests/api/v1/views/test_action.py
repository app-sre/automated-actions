from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from fastapi import FastAPI, HTTPException, status
from pynamodb.attributes import DynamicMapAttribute

from automated_actions.api.v1.dependencies import get_opa_instance, get_user
from automated_actions.db.models import (
    ActionManager,
    ActionSchemaOut,
    ActionStatus,
    get_action_manager,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient

    from automated_actions.db.models._action import ActionSchemaIn
    from tests.conftest import MockUserModel


class ActionStub(ActionSchemaOut):
    """Stub for Action model."""

    def dump(self) -> ActionSchemaOut:
        return self

    @classmethod
    def find_by_owner(
        cls,
        username: str,
        status: ActionStatus | None = None,
        max_age: int | None = None,
    ) -> list[ActionStub]:
        """Stub method to return a list of actions."""
        return [
            ActionStub(
                action_id="1",
                name="test action",
                status=ActionStatus.SUCCESS,
                result="test result",
                owner=username,
                created_at=1.0,
                updated_at=2.0,
                task_args=None,
            ),
            ActionStub(
                action_id="2",
                name="test action 2",
                status=ActionStatus.FAILURE,
                result="test result 2",
                owner=username,
                created_at=1.0,
                updated_at=2.0,
                task_args=DynamicMapAttribute(
                    attribute_values={}, key1="value1", key2="value2"
                ),
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
                owner="test_user",
                created_at=1.0,
                updated_at=2.0,
                task_args=None,
            )
        raise ValueError("Action not found")

    def set_status(self, status: ActionStatus) -> None:
        """Stub method to set the status of an action."""
        self.status = status

    @classmethod
    def create(cls, params: ActionSchemaIn) -> ActionStub:
        return ActionStub(
            action_id="action_id",
            name="test action",
            status=ActionStatus.RUNNING,
            result="test result",
            owner="test_user",
            created_at=1.0,
            updated_at=2.0,
            task_args=None,
        )


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
            "owner": "test_user",
            "status": "SUCCESS",
            "action_id": "1",
            "result": "test result",
            "created_at": 1.0,
            "updated_at": 2.0,
            "task_args": {},
        },
        {
            "name": "test action 2",
            "owner": "test_user",
            "status": "FAILURE",
            "action_id": "2",
            "result": "test result 2",
            "created_at": 1.0,
            "updated_at": 2.0,
            "task_args": {"key1": "value1", "key2": "value2"},
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
        "owner": "test_user",
        "status": "RUNNING",
        "action_id": "1",
        "result": "test result",
        "created_at": 1.0,
        "updated_at": 2.0,
        "task_args": {},
    }


def test_action_cancel(
    testing_app: FastAPI, client: Callable[[FastAPI], TestClient]
) -> None:
    response = client(testing_app).post(
        testing_app.url_path_for("action_cancel", action_id="1"),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["status"] == ActionStatus.CANCELLED


def _make_owner_enforcing_authz(calls: list[dict[str, Any]]) -> Callable:
    """Stand-in for OPA: records each call and denies if owner != caller."""

    async def _authz(
        _request: Any, user: Any, extra_params: dict[str, str] | None = None
    ) -> None:
        calls.append({"username": user.username, "extra_params": extra_params})
        if extra_params and extra_params.get("owner") != user.username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
            )

    return _authz


@pytest.mark.parametrize(
    ("method", "operation_id"),
    [("get", "action_detail"), ("post", "action_cancel")],
)
def test_action_detail_and_cancel_pass_action_owner_to_authz(
    testing_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    method: str,
    operation_id: str,
) -> None:
    """ActionStub("1").owner == "test_user" == the default fake user's username."""
    calls: list[dict[str, Any]] = []
    testing_app.dependency_overrides[get_opa_instance] = lambda: (
        _make_owner_enforcing_authz(calls)
    )

    response = getattr(client(testing_app), method)(
        testing_app.url_path_for(operation_id, action_id="1"),
    )

    assert response.status_code in {status.HTTP_200_OK, status.HTTP_202_ACCEPTED}
    assert calls == [{"username": "test_user", "extra_params": {"owner": "test_user"}}]


@pytest.mark.parametrize(
    ("method", "operation_id"),
    [("get", "action_detail"), ("post", "action_cancel")],
)
def test_action_detail_and_cancel_deny_other_users_action(
    testing_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    usermodel: type[MockUserModel],
    method: str,
    operation_id: str,
) -> None:
    """FIND-005: a user must not be able to view/cancel another user's action."""
    calls: list[dict[str, Any]] = []
    testing_app.dependency_overrides[get_opa_instance] = lambda: (
        _make_owner_enforcing_authz(calls)
    )
    testing_app.dependency_overrides[get_user] = lambda: usermodel(
        username="other_user"
    )

    response = getattr(client(testing_app), method)(
        testing_app.url_path_for(operation_id, action_id="1"),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert calls == [{"username": "other_user", "extra_params": {"owner": "test_user"}}]
