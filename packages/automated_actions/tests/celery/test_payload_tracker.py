import uuid
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock

from automated_actions.celery.payload_tracker.tasks import (
    PayloadTrackerCreatePartition,
    payload_tracker_create_partition,
)
from automated_actions.db.models import ActionStatus

if TYPE_CHECKING:
    from automated_actions_utils.cluster_connection import ClusterConnectionData
    from pytest_mock import MockerFixture


def test_payload_tracker_create_partition_run(
    mock_oc: Mock,
    mock_action: Mock,
) -> None:
    namespace = "payload-tracker-prod"

    automated_action = PayloadTrackerCreatePartition(
        action=mock_action, oc=mock_oc, namespace=namespace
    )

    automated_action.run(
        image="test-image:latest",
        date="2026-10-01",
        secret_name="test-secret",
        env_secret_mappings={"PGHOST": "db.host"},
    )

    mock_oc.run_job.assert_called_once_with(namespace=namespace, job=ANY)


def test_payload_tracker_create_partition_task(
    mocker: MockerFixture,
    mock_action: Mock,
    cluster_connection_data: ClusterConnectionData,
) -> None:
    patched_oc = mocker.patch(
        "automated_actions.celery.payload_tracker.tasks.OpenshiftClient"
    )
    mocker.patch(
        "automated_actions.celery.payload_tracker.tasks.get_cluster_connection_data",
        return_value=cluster_connection_data,
    )
    mock_run = mocker.patch.object(PayloadTrackerCreatePartition, "run")
    action_id = str(uuid.uuid4())
    task_args = {
        "cluster": "cluster",
        "namespace": "payload-tracker-prod",
        "date": "2026-10-01",
    }
    payload_tracker_create_partition.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    patched_oc.assert_called_once_with(
        server_url=cluster_connection_data.url, token=cluster_connection_data.token
    )
    mock_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS, result="ok", task_args=task_args
    )
