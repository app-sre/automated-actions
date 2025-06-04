from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from automated_actions.api.v1.views.external_resource import get_action
from automated_actions.db.models import Action


@pytest.fixture
def mock_external_resource_rds_reboot_task(mocker: MockerFixture) -> MagicMock:
    """Mock the external_resource_rds_reboot_task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.external_resource.external_resource_rds_reboot_task"
    )


@pytest.fixture
def test_app(app: FastAPI, mocker: MockerFixture, running_action: dict) -> FastAPI:
    action_mock = mocker.MagicMock(spec=Action)
    action_mock.action_id = running_action["action_id"]
    action_mock.dump.return_value = running_action
    app.dependency_overrides[get_action] = lambda: action_mock
    return app


def test_external_resource(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_external_resource_rds_reboot_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_rds_reboot",
            account="test-account",
            identifier="test-identifier",
        ),
        params={
            "force_failover": True,
        },
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_external_resource_rds_reboot_task.apply_async.assert_called_once_with(
        kwargs={
            "account": "test-account",
            "identifier": "test-identifier",
            "force_failover": True,
            "action": test_app.dependency_overrides[get_action](),
        },
        task_id=running_action["action_id"],
    )
