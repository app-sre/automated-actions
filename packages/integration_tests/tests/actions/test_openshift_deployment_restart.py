from time import sleep

import pytest
from automated_actions.config import settings
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import openshift_workload_restart
from automated_actions_client.api.general import action_detail
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from automated_actions_client.models.openshift_workload_restart_kind import (
    OpenshiftWorkloadRestartKind,
)
from automated_actions_utils.cluster_connection import get_cluster_connection_data
from automated_actions_utils.openshift_client import OpenshiftClient

from tests.conftest import Config


@pytest.fixture
def openshift_client(config: Config) -> OpenshiftClient:
    cluster = config.openshift_deployment_restart.cluster
    cluster_connection = get_cluster_connection_data(cluster, settings)
    return OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )


def test_openshift_deployment_restart(
    aa_client: AuthenticatedClient, config: Config, openshift_client: OpenshiftClient
) -> None:
    api = openshift_client.dyn_client.resources.get(
        api_version="apps/v1", kind="Deployment"
    )

    before = api.get(
        name=config.openshift_deployment_restart.name,
        namespace=config.openshift_deployment_restart.namespace,
    )
    replicas = before["spec"]["replicas"]
    before_generation = before["status"]["observedGeneration"]
    assert replicas == before["status"]["replicas"]
    assert replicas == before["status"]["availableReplicas"]
    assert replicas == before["status"]["readyReplicas"]

    action = openshift_workload_restart.sync(
        client=aa_client,
        cluster=config.openshift_deployment_restart.cluster,
        namespace=config.openshift_deployment_restart.namespace,
        kind=OpenshiftWorkloadRestartKind("Deployment"),
        name=config.openshift_deployment_restart.name,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result

    retry = 1
    success = False
    while retry <= config.openshift_deployment_restart.retries:
        after = api.get(
            name=config.openshift_deployment_restart.name,
            namespace=config.openshift_deployment_restart.namespace,
        )
        status = after["status"]
        success = (
            before_generation < status["observedGeneration"]
            and status["availableReplicas"] == replicas
            and status["replicas"] == replicas
            and status["updatedReplicas"] == replicas
        )

        if success:
            break

        retry += 1
        sleep(config.openshift_deployment_restart.sleep_time)

    assert success

    action = action_detail.sync(client=aa_client, action_id=action.action_id)
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.SUCCESS
    assert action.result


def test_openshift_deployment_restart_does_not_exist(
    aa_client: AuthenticatedClient, config: Config, openshift_client: OpenshiftClient
) -> None:
    namespace = config.openshift_deployment_restart.namespace

    v1_apps = openshift_client.dyn_client.resources.get(
        api_version="apps/v1", kind="Deployment"
    )
    deployment_names = [p.metadata.name for p in v1_apps.get(namespace=namespace).items]
    deployment_to_delete = "this-deployment-does-not-exist"
    assert deployment_to_delete not in deployment_names

    action = openshift_workload_restart.sync(
        client=aa_client,
        cluster=config.openshift_deployment_restart.cluster,
        namespace=config.openshift_deployment_restart.namespace,
        kind=OpenshiftWorkloadRestartKind("Deployment"),
        name=deployment_to_delete,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result

    action = action_detail.sync(client=aa_client, action_id=action.action_id)
    assert isinstance(action, ActionSchemaOut)

    retry = 1
    while retry <= config.openshift_deployment_restart.retries and action.status in {
        ActionStatus.PENDING,
        ActionStatus.RUNNING,
    }:
        action = action_detail.sync(client=aa_client, action_id=action.action_id)
        assert isinstance(action, ActionSchemaOut)
        retry += 1
        sleep(config.openshift_deployment_restart.sleep_time)

    assert action.status == ActionStatus.FAILURE
    assert (
        action.result
        == f"Deployment {deployment_to_delete} does not exist in namespace {namespace}"
    )
