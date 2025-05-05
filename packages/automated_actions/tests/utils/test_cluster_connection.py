# ruff: noqa: S105, S106
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from automated_actions.utils.cluster_connection import (
    ClusterConnectionData,
    ClusterMissingInAppInterfaceError,
    MissingAppInterfaceClusterAutomationTokenError,
    get_cluster_connection_data,
)
from automated_actions.utils.vault_client import SecretFieldNotFoundError


@pytest.fixture(autouse=True)
def mock_gql_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("automated_actions.utils.cluster_connection.GQLClient")


@pytest.fixture(autouse=True)
def mock_vault_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("automated_actions.utils.cluster_connection.VaultClient")


@pytest.fixture(autouse=True)
def mock_settings(mocker: MockerFixture) -> None:
    mock = mocker.patch("automated_actions.utils.cluster_connection.settings")
    mock.qontract_server_url = "https://qontract.example.com"
    mock.qontract_server_token = "qontract-token"
    mock.vault_server_url = "https://vault.example.com"
    mock.vault_role_id = "role-id"
    mock.vault_secret_id = "secret-id"
    mock.vault_kube_auth_role = None
    mock.vault_kube_auth_mount = None


def test_get_cluster_connection_data_success(
    mock_gql_client: MagicMock, mock_vault_client: MagicMock
) -> None:
    # Mock GraphQL query response
    mock_gql_client.return_value.query.return_value = {
        "cluster": [
            {
                "name": "test-cluster",
                "serverUrl": "https://cluster.example.com",
                "automationToken": {
                    "path": "secret/path",
                    "version": 1,
                    "field": "token",
                    "format": "whatever",
                },
            }
        ]
    }

    # Mock Vault client response
    mock_vault_client.return_value.read_secret.return_value = {"token": "test-token"}

    result = get_cluster_connection_data("test-cluster")

    assert result == ClusterConnectionData(
        url="https://cluster.example.com", token="test-token"
    )
    mock_gql_client.return_value.query.assert_called_once()
    mock_vault_client.return_value.read_secret.assert_called_once()


def test_get_cluster_connection_data_missing_cluster(
    mock_gql_client: MagicMock,
) -> None:
    # Mock GraphQL query response with no cluster
    mock_gql_client.return_value.query.return_value = {"cluster": []}

    with pytest.raises(ClusterMissingInAppInterfaceError) as exc_info:
        get_cluster_connection_data("missing-cluster")

    assert str(exc_info.value) == "cluster 'missing-cluster' missing in app-interface"
    mock_gql_client.return_value.query.assert_called_once()


def test_get_cluster_connection_data_missing_automation_token(
    mock_gql_client: MagicMock,
) -> None:
    # Mock GraphQL query response with no automation token
    mock_gql_client.return_value.query.return_value = {
        "cluster": [
            {
                "name": "test-cluster",
                "automationToken": None,
                "serverUrl": "https://cluster.example.com",
            }
        ]
    }

    with pytest.raises(MissingAppInterfaceClusterAutomationTokenError) as exc_info:
        get_cluster_connection_data("test-cluster")

    assert str(exc_info.value) == "No automationToken for cluster test-cluster"
    mock_gql_client.return_value.query.assert_called_once()


def test_get_cluster_connection_data_secret_field_not_found(
    mock_gql_client: MagicMock, mock_vault_client: MagicMock
) -> None:
    # Mock GraphQL query response
    mock_gql_client.return_value.query.return_value = {
        "cluster": [
            {
                "name": "test-cluster",
                "serverUrl": "https://cluster.example.com",
                "automationToken": {
                    "path": "secret/path",
                    "version": 1,
                    "field": "token",
                    "format": "whatever",
                },
            }
        ]
    }

    # Mock Vault client response with missing field
    mock_vault_client.return_value.read_secret.return_value = {}

    with pytest.raises(SecretFieldNotFoundError) as exc_info:
        get_cluster_connection_data("test-cluster")

    assert str(exc_info.value) == ("token not found in secret secret/path")
    mock_gql_client.return_value.query.assert_called_once()
    mock_vault_client.return_value.read_secret.assert_called_once()
