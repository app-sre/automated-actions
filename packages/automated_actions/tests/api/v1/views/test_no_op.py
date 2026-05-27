from typing import TYPE_CHECKING, get_type_hints

import pytest
from fastapi import FastAPI, status

from automated_actions.api.v1.views.no_op import get_action
from automated_actions.db.models import Action

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import MagicMock

    from fastapi.testclient import TestClient
    from pytest_mock import MockerFixture


@pytest.fixture
def mock_no_op_task(mocker: MockerFixture) -> MagicMock:
    """Mock the no_op_task function."""
    return mocker.patch("automated_actions.api.v1.views.no_op.no_op_task")


@pytest.fixture
def test_app(app: FastAPI, mocker: MockerFixture, running_action: dict) -> FastAPI:
    action_mock = mocker.MagicMock(spec=Action)
    action_mock.action_id = running_action["action_id"]
    action_mock.dump.return_value = running_action
    app.dependency_overrides[get_action] = lambda: action_mock
    return app


def test_no_op(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_no_op_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(test_app.url_path_for("no_op"))
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_no_op_task.apply_async.assert_called_once_with(
        kwargs={
            "action": test_app.dependency_overrides[get_action](),
        },
        task_id=running_action["action_id"],
    )


def test_dependency_type_aliases_resolve_at_runtime() -> None:
    """UserDep must not be in a TYPE_CHECKING block."""
    get_type_hints(get_action, include_extras=True)
