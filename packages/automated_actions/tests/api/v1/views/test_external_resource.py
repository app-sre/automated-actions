from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from automated_actions.api.v1.views.external_resource import (
    get_action_external_resource_flush_elasticache,
    get_action_external_resource_rds_logs,
    get_action_external_resource_rds_reboot,
    get_action_external_resource_rds_snapshot,
)
from automated_actions.db.models import Action


@pytest.fixture
def mock_external_resource_rds_reboot_task(mocker: MockerFixture) -> MagicMock:
    """Mock the external_resource_rds_reboot_task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.external_resource.external_resource_rds_reboot_task"
    )


@pytest.fixture
def mock_external_resource_rds_snapshot_task(mocker: MockerFixture) -> MagicMock:
    """Mock the external_resource_rds_snapshot_task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.external_resource.external_resource_rds_snapshot_task"
    )


@pytest.fixture
def mock_external_resource_rds_logs_task(mocker: MockerFixture) -> MagicMock:
    """Mock the external_resource_rds_logs_task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.external_resource.external_resource_rds_logs_task"
    )


@pytest.fixture
def mock_external_resource_flush_elasticache_task(mocker: MockerFixture) -> MagicMock:
    """Mock the external_resource_flush_elasticache_task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.external_resource.external_resource_flush_elasticache_task"
    )


@pytest.fixture
def test_app(app: FastAPI, mocker: MockerFixture, running_action: dict) -> FastAPI:
    action_mock = mocker.MagicMock(spec=Action)
    action_mock.action_id = running_action["action_id"]
    action_mock.dump.return_value = running_action
    app.dependency_overrides[get_action_external_resource_rds_reboot] = (
        lambda: action_mock
    )
    app.dependency_overrides[get_action_external_resource_rds_logs] = (
        lambda: action_mock
    )
    app.dependency_overrides[get_action_external_resource_rds_snapshot] = (
        lambda: action_mock
    )
    app.dependency_overrides[get_action_external_resource_flush_elasticache] = (
        lambda: action_mock
    )
    return app


def test_external_resource_rds_reboot(
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
            "action": test_app.dependency_overrides[
                get_action_external_resource_rds_reboot
            ](),
        },
        task_id=running_action["action_id"],
    )


def test_external_resource_rds_logs(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_external_resource_rds_logs_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_rds_logs",
            account="test-account",
            identifier="test-identifier",
        ),
        params={
            "expiration_days": 5,
            "s3_file_name": "custom-logs.zip",
        },
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_external_resource_rds_logs_task.apply_async.assert_called_once_with(
        kwargs={
            "account": "test-account",
            "identifier": "test-identifier",
            "expiration_days": 5,
            "s3_file_name": "custom-logs.zip",
            "action": test_app.dependency_overrides[
                get_action_external_resource_rds_logs
            ](),
        },
        task_id=running_action["action_id"],
    )


def test_external_resource_rds_logs_default_params(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_external_resource_rds_logs_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_rds_logs",
            account="test-account",
            identifier="test-identifier",
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_external_resource_rds_logs_task.apply_async.assert_called_once_with(
        kwargs={
            "account": "test-account",
            "identifier": "test-identifier",
            "expiration_days": 7,
            "s3_file_name": None,
            "action": test_app.dependency_overrides[
                get_action_external_resource_rds_logs
            ](),
        },
        task_id=running_action["action_id"],
    )


def test_external_resource_rds_logs_expiration_validation(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_rds_logs",
            account="test-account",
            identifier="test-identifier",
        ),
        params={"expiration_days": 0},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_rds_logs",
            account="test-account",
            identifier="test-identifier",
        ),
        params={"expiration_days": 8},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_external_resource_rds_snapshot(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_external_resource_rds_snapshot_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_rds_snapshot",
            account="test-account",
            identifier="test-identifier",
            snapshot_identifier="test-snapshot-identifier",
        ),
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_external_resource_rds_snapshot_task.apply_async.assert_called_once_with(
        kwargs={
            "account": "test-account",
            "identifier": "test-identifier",
            "snapshot_identifier": "test-snapshot-identifier",
            "action": test_app.dependency_overrides[
                get_action_external_resource_rds_snapshot
            ](),
        },
        task_id=running_action["action_id"],
    )


def test_external_resource_flush_elasticache(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_external_resource_flush_elasticache_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "external_resource_flush_elasticache",
            account="test-account",
            identifier="test-identifier",
        ),
        params={
            "force_failover": True,
        },
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_external_resource_flush_elasticache_task.apply_async.assert_called_once_with(
        kwargs={
            "account": "test-account",
            "identifier": "test-identifier",
            "action": test_app.dependency_overrides[
                get_action_external_resource_flush_elasticache
            ](),
        },
        task_id=running_action["action_id"],
    )
