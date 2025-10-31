from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from automated_actions.api.v1.views.openshift import (
    get_action_openshift_trigger_cronjob,
    get_action_openshift_workload_delete,
    get_action_openshift_workload_restart,
)
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
    app.dependency_overrides[get_action_openshift_workload_restart] = (
        lambda: action_mock
    )
    app.dependency_overrides[get_action_openshift_workload_delete] = lambda: action_mock
    app.dependency_overrides[get_action_openshift_trigger_cronjob] = lambda: action_mock
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
            "action": test_app.dependency_overrides[
                get_action_openshift_workload_restart
            ](),
        },
        task_id=running_action["action_id"],
    )


@pytest.fixture
def mock_openshift_workload_delete_task(mocker: MockerFixture) -> MagicMock:
    """Mock the openshift_workload_delete function."""
    return mocker.patch(
        "automated_actions.api.v1.views.openshift.openshift_workload_delete_task"
    )


def test_openshift_workload_delete(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_openshift_workload_delete_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "openshift_workload_delete",
            cluster="test-cluster",
            namespace="test-namespace",
            kind="Pod",
            name="pod-xxx",
        ),
        params={"api_version": "v1000"},
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_openshift_workload_delete_task.apply_async.assert_called_once_with(
        kwargs={
            "cluster": "test-cluster",
            "namespace": "test-namespace",
            "kind": "Pod",
            "name": "pod-xxx",
            "api_version": "v1000",
            "action": test_app.dependency_overrides[
                get_action_openshift_workload_delete
            ](),
        },
        task_id=running_action["action_id"],
    )


@pytest.fixture
def mock_openshift_trigger_cronjob_task(mocker: MockerFixture) -> MagicMock:
    """Mock the openshift_trigger_cronjob function."""
    return mocker.patch(
        "automated_actions.api.v1.views.openshift.openshift_trigger_cronjob_task"
    )


def test_openshift_trigger_cronjob(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_openshift_trigger_cronjob_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "openshift_trigger_cronjob",
            cluster="test-cluster",
            namespace="test-namespace",
            cronjob="cronjob-xxx",
        )
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_openshift_trigger_cronjob_task.apply_async.assert_called_once_with(
        kwargs={
            "cluster": "test-cluster",
            "namespace": "test-namespace",
            "cronjob": "cronjob-xxx",
            "action": test_app.dependency_overrides[
                get_action_openshift_trigger_cronjob
            ](),
        },
        task_id=running_action["action_id"],
    )
