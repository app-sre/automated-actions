import uuid
from unittest.mock import ANY, Mock

from automated_actions_utils.cluster_connection import ClusterConnectionData
from pytest_mock import MockerFixture

from automated_actions.celery.openshift.tasks import (
    OpenshiftTriggerCronjob,
    openshift_trigger_cronjob,
)
from automated_actions.db.models import ActionStatus


def test_openshift_trigger_cronjob(
    mock_oc: Mock,
    mock_action: Mock,
) -> None:
    namespace = "test-namespace"
    cronjob = "test-cronjob"

    automated_action = OpenshiftTriggerCronjob(
        action=mock_action, oc=mock_oc, namespace=namespace, cronjob=cronjob
    )

    automated_action.run()

    mock_oc.trigger_cronjob.assert_called_once_with(
        namespace=namespace, cronjob=cronjob, annotations=ANY
    )


def test_openshift_trigger_cronjob_task(
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
    mock_owd = mocker.patch.object(OpenshiftTriggerCronjob, "run")
    action_id = str(uuid.uuid4())
    task_args = {
        "cluster": "cluster",
        "namespace": "namespace",
        "cronjob": "cronjob-xxx",
    }
    openshift_trigger_cronjob.signature(
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
