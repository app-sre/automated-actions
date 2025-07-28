import uuid
from collections.abc import Callable

import pytest
from automated_actions.config import settings
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import (
    openshift_workload_delete,
)
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from automated_actions_utils.cluster_connection import get_cluster_connection_data
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
)
from kubernetes.dynamic.exceptions import NotFoundError
from pydantic import BaseModel

from tests.conftest import Config


class OpenshiftWorkloadDeleteParameters(BaseModel):
    cluster: str
    namespace: str
    api_version: str
    kind: str
    name: str


@pytest.fixture(scope="session")
def openshift_workload_delete_parameters(
    config: Config,
) -> OpenshiftWorkloadDeleteParameters:
    return OpenshiftWorkloadDeleteParameters(
        cluster=config.openshift_workload_delete.cluster,
        namespace=config.openshift_workload_delete.namespace,
        api_version="v1",
        kind="ConfigMap",
        name="aa-integration-test-" + str(uuid.uuid4())[:20],
    )


@pytest.fixture
def openshift_client(config: Config) -> OpenshiftClient:
    cluster_connection = get_cluster_connection_data(
        config.openshift_workload_delete.cluster, settings
    )
    return OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )


@pytest.fixture(scope="session")
def action_id(
    aa_client: AuthenticatedClient,
    openshift_workload_delete_parameters: OpenshiftWorkloadDeleteParameters,
) -> str:
    """Trigger an Openshift workload delete action and return the action id.

    We use a pytest fixture with session scope to avoid multiple actions being triggered
    in case of retry via the flaky mark
    """
    action = openshift_workload_delete.sync(
        client=aa_client,
        cluster=openshift_workload_delete_parameters.cluster,
        namespace=openshift_workload_delete_parameters.namespace,
        api_version=openshift_workload_delete_parameters.api_version,
        kind=openshift_workload_delete_parameters.kind,
        name=openshift_workload_delete_parameters.name,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


def test_openshift_workload_delete_success(
    action_id: str,
    wait_for_action_success: Callable,
    config: Config,
    openshift_client: OpenshiftClient,
    openshift_workload_delete_parameters: OpenshiftWorkloadDeleteParameters,
) -> None:
    # create a test configmap
    api = openshift_client.dyn_client.resources.get(
        api_version=openshift_workload_delete_parameters.api_version,
        kind=openshift_workload_delete_parameters.kind,
    )
    body = {
        "apiVersion": "v1",
        "kind": openshift_workload_delete_parameters.kind,
        "metadata": {
            "name": openshift_workload_delete_parameters.name,
        },
        "data": {"data": "test data"},
    }
    api.create(body=body, namespace=openshift_workload_delete_parameters.namespace)

    # wait for the action to complete and assert it was successful
    wait_for_action_success(
        action_id=action_id,
        retries=config.openshift_workload_delete.retries,
        sleep_time=config.openshift_workload_delete.sleep_time,
    )

    # verify the configmap was deleted
    with pytest.raises(NotFoundError):
        api.get(
            namespace=openshift_workload_delete_parameters.namespace,
            name=openshift_workload_delete_parameters.name,
        )
