import uuid
from unittest.mock import Mock, call

import pytest
from automated_actions_utils.cluster_connection import ClusterConnectionData
from automated_actions_utils.openshift_client import (
    OpenshiftClientResourceNotFoundError,
    RollingRestartResource,
)
from kubernetes.client.exceptions import ApiException
from pytest_mock import MockerFixture

from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.celery.openshift.tasks import (
    OpenshiftResourceKindNotSupportedError,
    OpenshiftWorkloadRestart,
    openshift_workload_restart,
)
from automated_actions.db.models import ActionStatus


def test_openshift_workload_restart_pod(mock_oc: Mock) -> None:
    namespace = "test-namespace"
    pod = "test-pod"

    automated_action = OpenshiftWorkloadRestart(
        oc=mock_oc, namespace=namespace, kind="Pod", name=pod
    )

    automated_action.run()

    mock_oc.delete_pod_from_replicated_resource.assert_called_once_with(
        name=pod, namespace=namespace
    )


def test_openshift_workload_restart_deployment(mock_oc: Mock) -> None:
    namespace = "test-namespace"
    deployment = "test-deployment"

    automated_action = OpenshiftWorkloadRestart(
        oc=mock_oc, namespace=namespace, kind="Deployment", name=deployment
    )

    automated_action.run()

    mock_oc.rolling_restart.assert_called_once_with(
        name=deployment, namespace=namespace, kind=RollingRestartResource("Deployment")
    )


def test_openshift_workload_restart_unsupported(mock_oc: Mock) -> None:
    with pytest.raises(OpenshiftResourceKindNotSupportedError) as exc_info:
        OpenshiftWorkloadRestart(
            oc=mock_oc, namespace="namespace", kind="Whatever", name="whatever-name"
        )

    assert "kind 'Whatever' not supported" in str(exc_info.value)


def test_openshift_workload_restart_task(
    mocker: MockerFixture,
    mock_action: Mock,
    cluster_connection_data: ClusterConnectionData,
) -> None:
    mocker.patch(
        "automated_actions.celery.openshift.tasks.get_cluster_connection_data",
        return_value=cluster_connection_data,
    )
    mock_oc = mocker.patch("automated_actions.celery.openshift.tasks.OpenshiftClient")
    mock_owr = mocker.patch.object(OpenshiftWorkloadRestart, "run")

    action_id = str(uuid.uuid4())
    task_args = {
        "cluster": "cluster",
        "namespace": "namespace",
        "kind": "Pod",
        "name": "pod-name",
    }
    openshift_workload_restart.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_oc.asssert_called_once_with(
        server_url=cluster_connection_data.url, token=cluster_connection_data.token
    )
    mock_owr.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS, result="ok", task_args=task_args
    )


def test_openshift_workload_restart_task_non_retryable_failure(
    mocker: MockerFixture,
    mock_action: Mock,
    cluster_connection_data: ClusterConnectionData,
) -> None:
    mock_oc = mocker.patch("automated_actions.celery.openshift.tasks.OpenshiftClient")
    mock_owr = mocker.patch.object(
        OpenshiftWorkloadRestart,
        "run",
        side_effect=OpenshiftClientResourceNotFoundError("pod pod-name does not exist"),
    )
    mocker.patch(
        "automated_actions.celery.openshift.tasks.get_cluster_connection_data",
        return_value=cluster_connection_data,
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "cluster": "cluster",
        "namespace": "namespace",
        "kind": "Pod",
        "name": "pod-name",
    }
    openshift_workload_restart.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_oc.asssert_called_once_with(
        server_url=cluster_connection_data.url, token=cluster_connection_data.token
    )
    mock_owr.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.FAILURE,
        result="pod pod-name does not exist",
        task_args=task_args,
    )


def test_openshift_workload_restart_task_retryable_failure(
    mocker: MockerFixture,
    mock_action: Mock,
    cluster_connection_data: ClusterConnectionData,
) -> None:
    mock_oc = mocker.patch("automated_actions.celery.openshift.tasks.OpenshiftClient")
    mock_owr = mocker.patch.object(
        OpenshiftWorkloadRestart,
        "run",
        side_effect=ApiException("Cannot connect to cluster"),
    )
    mocker.patch(
        "automated_actions.celery.openshift.tasks.get_cluster_connection_data",
        return_value=cluster_connection_data,
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "cluster": "cluster",
        "namespace": "namespace",
        "kind": "Pod",
        "name": "pod-name",
    }
    openshift_workload_restart.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    call_count = AutomatedActionTask.max_retries + 1
    mock_oc.assert_has_calls(
        [
            call(
                server_url=cluster_connection_data.url,
                token=cluster_connection_data.token,
            )
        ]
        * call_count
    )
    assert mock_owr.call_count == call_count
    mock_action.set_status.assert_has_calls([call(ActionStatus.RUNNING)] * call_count)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.FAILURE,
        result="(Cannot connect to cluster)\nReason: None\n",
        task_args=task_args,
    )
