import uuid
from unittest.mock import Mock

from automated_actions_utils.cluster_connection import ClusterConnectionData
from pytest_mock import MockerFixture

from automated_actions.celery.openshift.tasks import (
    OpenshiftWorkloadDelete,
    openshift_workload_delete,
)
from automated_actions.db.models import ActionStatus


def test_openshift_workload_delete(mock_oc: Mock) -> None:
    namespace = "test-namespace"
    api_version = "v1"
    kind = "Deployment"
    name = "test-deployment"

    automated_action = OpenshiftWorkloadDelete(
        oc=mock_oc, namespace=namespace, api_version=api_version, kind=kind, name=name
    )

    automated_action.run()

    mock_oc.delete.assert_called_once_with(
        namespace=namespace, api_version=api_version, kind=kind, name=name
    )


def test_openshift_workload_delete_task(
    mocker: MockerFixture,
    mock_action: Mock,
    cluster_connection_data: ClusterConnectionData,
) -> None:
    patched_oc = mocker.patch(
        "automated_actions.celery.openshift.tasks.OpenshiftClient"
    )
    mocker.patch(
        "automated_actions.celery.openshift.tasks.get_cluster_connection_data",
        return_value=cluster_connection_data,
    )
    mock_owd = mocker.patch.object(OpenshiftWorkloadDelete, "run")
    action_id = str(uuid.uuid4())
    task_args = {
        "cluster": "cluster",
        "namespace": "namespace",
        "api_version": "v1",
        "kind": "Pod",
        "name": "pod-name",
    }
    openshift_workload_delete.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    patched_oc.assert_called_once_with(
        server_url=cluster_connection_data.url, token=cluster_connection_data.token
    )
    mock_owd.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS, result="ok", task_args=task_args
    )
