from datetime import UTC
from datetime import datetime as dt
from unittest.mock import MagicMock

import pytest
from kubernetes.dynamic.exceptions import NotFoundError
from pytest_mock import MockerFixture

from automated_actions_utils import openshift_client as openshift_client_utils
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
    OpenshiftClientPodDeletionNotSupportedError,
    OpenshiftClientResourceNotFoundError,
    RollingRestartResource,
)


@pytest.fixture(autouse=True)
def mock_dynamic_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("automated_actions_utils.openshift_client.DynamicClient")


@pytest.fixture(autouse=True)
def now(mocker: MockerFixture) -> dt:
    datetime_mock = mocker.patch.object(
        openshift_client_utils, "datetime", autospec=True
    )
    datetime_mock.now.return_value = dt.now(UTC)
    return datetime_mock.now.return_value


@pytest.fixture
def openshift_client() -> OpenshiftClient:
    return OpenshiftClient(server_url="https://example.com", token="fake-token")  # noqa: S106


def test_rolling_restart_success(
    openshift_client: OpenshiftClient, mock_dynamic_client: MagicMock, now: dt
) -> None:
    mock_api = MagicMock()
    mock_dynamic_client.return_value.resources.get.return_value = mock_api
    mock_api.patch.return_value = {"status": "success"}

    kind = RollingRestartResource.deployment
    name = "test-deployment"
    namespace = "test-namespace"

    result = openshift_client.rolling_restart(kind, name, namespace)

    mock_dynamic_client.return_value.resources.get.assert_called_once_with(
        api_version="apps/v1", kind="Deployment"
    )
    mock_api.patch.assert_called_once_with(
        namespace=namespace,
        name=name,
        body={
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now.isoformat()
                        }
                    }
                }
            }
        },
    )
    assert result == {"status": "success"}


def test_rolling_restart_not_found(
    openshift_client: OpenshiftClient, mock_dynamic_client: MagicMock
) -> None:
    mock_api = MagicMock()
    mock_dynamic_client.return_value.resources.get.return_value = mock_api
    error = MagicMock(NotFoundError)
    error.status = 404
    error.reason = "Not Found"
    error.body = '{"message": "Resource not found"}'
    error.headers = {"Content-Type": "application/json"}
    mock_api.patch.side_effect = NotFoundError(error)

    kind = RollingRestartResource.deployment
    name = "nonexistent-deployment"
    namespace = "test-namespace"

    with pytest.raises(OpenshiftClientResourceNotFoundError) as exc_info:
        openshift_client.rolling_restart(kind, name, namespace)

    assert (
        str(exc_info.value)
        == f"Deployment {name} does not exist in namespace {namespace}"
    )


def test_delete_pod_success(
    openshift_client: OpenshiftClient, mock_dynamic_client: MagicMock
) -> None:
    mock_api = MagicMock()
    mock_dynamic_client.return_value.resources.get.return_value = mock_api
    mock_api.get.return_value = {
        "metadata": {"ownerReferences": [{"kind": "ReplicaSet"}]}
    }
    mock_api.delete.return_value = {"status": "deleted"}

    name = "test-pod"
    namespace = "test-namespace"

    result = openshift_client.delete_pod_from_replicated_resource(name, namespace)

    mock_dynamic_client.return_value.resources.get.assert_called_once_with(
        api_version="v1", kind="Pod"
    )
    mock_api.get.assert_called_once_with(name=name, namespace=namespace)
    mock_api.delete.assert_called_once_with(name=name, namespace=namespace)
    assert result == {"status": "deleted"}


def test_delete_pod_not_found(
    openshift_client: OpenshiftClient, mock_dynamic_client: MagicMock
) -> None:
    mock_api = MagicMock()
    mock_dynamic_client.return_value.resources.get.return_value = mock_api
    error = MagicMock(NotFoundError)
    error.status = 404
    error.reason = "Not Found"
    error.body = '{"message": "Resource not found"}'
    error.headers = {"Content-Type": "application/json"}
    mock_api.get.side_effect = NotFoundError(error)

    name = "nonexistent-pod"
    namespace = "test-namespace"

    with pytest.raises(OpenshiftClientResourceNotFoundError) as exc_info:
        openshift_client.delete_pod_from_replicated_resource(name, namespace)

    assert str(exc_info.value) == f"Pod {name} does not exist in namespace {namespace}"


def test_delete_pod_unsupported_owner(
    openshift_client: OpenshiftClient, mock_dynamic_client: MagicMock
) -> None:
    mock_api = MagicMock()
    mock_dynamic_client.return_value.resources.get.return_value = mock_api
    mock_api.get.return_value = {
        "metadata": {"ownerReferences": [{"kind": "UnsupportedKind"}]}
    }

    name = "test-pod"
    namespace = "test-namespace"

    with pytest.raises(OpenshiftClientPodDeletionNotSupportedError) as exc_info:
        openshift_client.delete_pod_from_replicated_resource(name, namespace)

    assert str(exc_info.value) == (
        f"Pod '{name}' in namespace '{namespace}' cannot be deleted as "
        f"it does not belong to a ReplicaSet, StatefulSet."
    )
