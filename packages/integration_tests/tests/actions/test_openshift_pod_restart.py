import random
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
from kubernetes.dynamic.resource import ResourceInstance
from pydantic import BaseModel

from tests.conftest import Config


@pytest.fixture
def openshift_client(config: Config) -> OpenshiftClient:
    cluster = config.openshift_pod_restart.cluster
    cluster_connection = get_cluster_connection_data(cluster, settings)
    return OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )


class ParentResourceData(BaseModel):
    replicas: int
    label_selector: str


def _get_parent_resource(
    openshift_client: OpenshiftClient,
    namespace: str,
    kind: str,
    name: str,
) -> ResourceInstance:
    v1_apps = openshift_client.dyn_client.resources.get(
        api_version="apps/v1", kind=kind
    )
    resource_instance = v1_apps.get(name=name, namespace=namespace)
    replicas = resource_instance.spec.replicas
    assert replicas == resource_instance.status.replicas
    assert replicas == resource_instance.status.availableReplicas
    assert replicas == resource_instance.status.readyReplicas

    label_selector = ",".join(
        f"{key}={value}"
        for key, value in resource_instance.spec.selector.matchLabels.items()
    )

    return ParentResourceData(replicas=replicas, label_selector=label_selector)


def _get_running_pod_names(
    openshift_client: OpenshiftClient, namespace: str, label_selector: str
) -> list[str]:
    pods = openshift_client.dyn_client.resources.get(api_version="v1", kind="Pod").get(
        namespace=namespace, label_selector=label_selector
    )
    return [p.metadata.name for p in pods.items if p.status.phase == "Running"]


def test_openshift_pod_restart_ok(
    aa_client: AuthenticatedClient, config: Config, openshift_client: OpenshiftClient
) -> None:
    cluster = config.openshift_pod_restart.cluster
    namespace = config.openshift_pod_restart.namespace

    parent = _get_parent_resource(
        openshift_client=openshift_client,
        namespace=namespace,
        kind=config.openshift_pod_restart.parent_kind,
        name=config.openshift_pod_restart.parent_kind_name,
    )
    pod_names = _get_running_pod_names(
        openshift_client=openshift_client,
        namespace=namespace,
        label_selector=parent.label_selector,
    )
    assert len(pod_names) == parent.replicas

    pod_to_delete = random.choice(pod_names)  # noqa: S311
    action = openshift_workload_restart.sync(
        client=aa_client,
        cluster=cluster,
        namespace=namespace,
        kind=OpenshiftWorkloadRestartKind("Pod"),
        name=pod_to_delete,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result

    retry = 1
    success = False
    while retry <= config.openshift_pod_restart.retries:
        pod_names = _get_running_pod_names(
            openshift_client=openshift_client,
            namespace=namespace,
            label_selector=parent.label_selector,
        )

        success = len(pod_names) == parent.replicas and pod_to_delete not in pod_names
        if success:
            break

        retry += 1
        sleep(config.openshift_pod_restart.sleep_time)

    assert success

    action = action_detail.sync(client=aa_client, action_id=action.action_id)
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.SUCCESS
    assert action.result


def test_openshift_pod_restart_does_not_exist(
    aa_client: AuthenticatedClient, config: Config, openshift_client: OpenshiftClient
) -> None:
    namespace = config.openshift_pod_restart.namespace

    pods = openshift_client.dyn_client.resources.get(api_version="v1", kind="Pod").get(
        namespace=namespace
    )
    pod_names = [p.metadata.name for p in pods.items]
    pod_to_delete = "this-pod-does-not-exist"
    assert pod_to_delete not in pod_names

    action = openshift_workload_restart.sync(
        client=aa_client,
        cluster=config.openshift_pod_restart.cluster,
        namespace=namespace,
        kind=OpenshiftWorkloadRestartKind("Pod"),
        name=pod_to_delete,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result

    action = action_detail.sync(client=aa_client, action_id=action.action_id)
    assert isinstance(action, ActionSchemaOut)

    retry = 1
    while retry <= config.openshift_pod_restart.retries and action.status in {
        ActionStatus.PENDING,
        ActionStatus.RUNNING,
    }:
        action = action_detail.sync(client=aa_client, action_id=action.action_id)
        assert isinstance(action, ActionSchemaOut)
        retry += 1
        sleep(config.openshift_pod_restart.sleep_time)

    assert action.status == ActionStatus.FAILURE
    assert (
        action.result == f"Pod {pod_to_delete} does not exist in namespace {namespace}"
    )
