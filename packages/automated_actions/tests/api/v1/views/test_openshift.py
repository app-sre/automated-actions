from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from automated_actions.api.v1.views.openshift import get_action
from automated_actions.db.models import Action


@pytest.fixture
def mock_openshift_workload_restart_task(mocker: MockerFixture) -> MagicMock:
    """Mock the openshift_workload_restart_task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.openshift.openshift_workload_restart_task"
    )


@pytest.fixture
def test_app(app: FastAPI, mocker: MockerFixture, running_action: dict) -> FastAPI:
    action_mock = mocker.MagicMock(spec=Action)
    action_mock.action_id = running_action["action_id"]
    action_mock.dump.return_value = running_action
    app.dependency_overrides[get_action] = lambda: action_mock
    return app


def test_openshift_workload_restart(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_openshift_workload_restart_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "openshift_workload_restart",
            cluster="test-cluster",
            namespace="test-namespace",
            kind="Pod",
            name="pod-xxx",
        )
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_openshift_workload_restart_task.apply_async.assert_called_once_with(
        kwargs={
            "cluster": "test-cluster",
            "namespace": "test-namespace",
            "kind": "Pod",
            "name": "pod-xxx",
            "action": test_app.dependency_overrides[get_action](),
        },
        task_id=running_action["action_id"],
    )
