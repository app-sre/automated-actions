from typing import TYPE_CHECKING, get_type_hints

import pytest
from fastapi import FastAPI, status

from automated_actions.api.v1.views.payload_tracker import (
    get_action_payload_tracker_create_partition,
)
from automated_actions.db.models import Action

if TYPE_CHECKING:
    from collections.abc import Callable
    from unittest.mock import MagicMock

    from fastapi.testclient import TestClient
    from pytest_mock import MockerFixture


@pytest.fixture
def mock_payload_tracker_create_partition_task(mocker: MockerFixture) -> MagicMock:
    """Mock the payload_tracker_create_partition task function."""
    return mocker.patch(
        "automated_actions.api.v1.views.payload_tracker"
        ".payload_tracker_create_partition_task"
    )


@pytest.fixture
def test_app(app: FastAPI, mocker: MockerFixture, running_action: dict) -> FastAPI:
    action_mock = mocker.MagicMock(spec=Action)
    action_mock.action_id = running_action["action_id"]
    action_mock.dump.return_value = running_action
    app.dependency_overrides[get_action_payload_tracker_create_partition] = lambda: (
        action_mock
    )
    return app


def test_payload_tracker_create_partition(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_payload_tracker_create_partition_task: MagicMock,
    running_action: dict,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "payload_tracker_create_partition",
            cluster="test-cluster",
            namespace="payload-tracker-prod",
            date="2026-10-01",
        )
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json()["action_id"] == running_action["action_id"]
    mock_payload_tracker_create_partition_task.apply_async.assert_called_once_with(
        kwargs={
            "cluster": "test-cluster",
            "namespace": "payload-tracker-prod",
            "date": "2026-10-01",
            "action": test_app.dependency_overrides[
                get_action_payload_tracker_create_partition
            ](),
        },
        task_id=running_action["action_id"],
    )


def test_payload_tracker_create_partition_invalid_date(
    test_app: FastAPI,
    client: Callable[[FastAPI], TestClient],
    mock_payload_tracker_create_partition_task: MagicMock,
) -> None:
    response = client(test_app).post(
        test_app.url_path_for(
            "payload_tracker_create_partition",
            cluster="test-cluster",
            namespace="payload-tracker-prod",
            date="not-a-date",
        )
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    mock_payload_tracker_create_partition_task.apply_async.assert_not_called()


def test_dependency_type_aliases_resolve_at_runtime() -> None:
    """UserDep must not be in a TYPE_CHECKING block."""
    get_type_hints(get_action_payload_tracker_create_partition, include_extras=True)
