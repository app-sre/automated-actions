# ruff: file-ignore[hardcoded-password-func-arg]
from unittest.mock import MagicMock

import pytest
from automated_actions.config import settings
from pytest_mock import MockerFixture

from automated_actions_utils.cluster_connection import (
    ClusterConnectionData,
    ClusterMissingInAppInterfaceError,
    MissingAppInterfaceClusterAutomationTokenError,
    get_cluster_connection_data,
)
from automated_actions_utils.vault_client import SecretFieldNotFoundError


@pytest.fixture(autouse=True)
def mock_gql_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("automated_actions_utils.cluster_connection.GQLClient")


@pytest.fixture(autouse=True)
def mock_vault_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("automated_actions_utils.cluster_connection.VaultClient")


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
                "automationTokens": None,
            }
        ]
    }

    # Mock Vault client response
    mock_vault_client.return_value.read_secret.return_value = {"token": "test-token"}

    result = get_cluster_connection_data("test-cluster", settings)

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
        get_cluster_connection_data("missing-cluster", settings)

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
                "automationTokens": None,
                "serverUrl": "https://cluster.example.com",
            }
        ]
    }

    with pytest.raises(MissingAppInterfaceClusterAutomationTokenError) as exc_info:
        get_cluster_connection_data("test-cluster", settings)

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
                "automationTokens": None,
            }
        ]
    }

    # Mock Vault client response with missing field
    mock_vault_client.return_value.read_secret.return_value = {}

    with pytest.raises(SecretFieldNotFoundError) as exc_info:
        get_cluster_connection_data("test-cluster", settings)

    assert str(exc_info.value) == ("token not found in secret secret/path")
    mock_gql_client.return_value.query.assert_called_once()
    mock_vault_client.return_value.read_secret.assert_called_once()


@pytest.mark.parametrize(
    ("entries", "legacy", "expected_path"),
    [
        ([(True, False, "active")], False, "active"),
        ([(True, False, "active")], True, "active"),
        (
            [
                (False, False, "inactive"),
                (True, True, "deleted"),
                (True, False, None),
                (True, False, "active"),
                (True, False, "second-active"),
            ],
            True,
            "active",
        ),
        (None, True, "legacy"),
        ([], True, "legacy"),
        ([(False, False, "inactive")], True, "legacy"),
        ([(True, True, "deleted")], True, "legacy"),
        ([(True, False, None)], True, "legacy"),
        ([(None, None, "inactive")], True, "legacy"),
        ([(True, None, "active")], False, "active"),
        (None, False, None),
        ([], False, None),
        ([(False, False, "inactive")], False, None),
        ([(True, True, "deleted")], False, None),
        ([(True, False, None)], False, None),
    ],
)
def test_get_cluster_connection_data_rotation_tokens(
    mock_gql_client: MagicMock,
    mock_vault_client: MagicMock,
    entries: list[tuple[bool | None, bool | None, str | None]] | None,
    *,
    legacy: bool,
    expected_path: str | None,
) -> None:
    mock_gql_client.return_value.query.return_value = {
        "cluster": [
            {
                "name": "test-cluster",
                "serverUrl": "https://cluster.example.com",
                "automationToken": {
                    "path": "legacy",
                    "version": 1,
                    "field": "token",
                    "format": None,
                }
                if legacy
                else None,
                "automationTokens": [
                    {
                        "name": f"token-{index}",
                        "namespace": "dedicated-admin",
                        "active": active,
                        "delete": delete,
                        "secret": {
                            "path": path,
                            "version": 2,
                            "field": "rotated_token",
                            "format": None,
                        }
                        if path
                        else None,
                    }
                    for index, (active, delete, path) in enumerate(entries)
                ]
                if entries is not None
                else None,
            }
        ]
    }
    mock_vault_client.return_value.read_secret.return_value = {
        "token": "legacy-value",
        "rotated_token": "rotated-value",
    }

    if expected_path is None:
        with pytest.raises(
            MissingAppInterfaceClusterAutomationTokenError,
            match="No automationToken for cluster test-cluster",
        ):
            get_cluster_connection_data("test-cluster", settings)
        mock_vault_client.return_value.read_secret.assert_not_called()
        return

    result = get_cluster_connection_data("test-cluster", settings)

    assert result == ClusterConnectionData(
        url="https://cluster.example.com",
        token="legacy-value" if expected_path == "legacy" else "rotated-value",
    )
    mock_vault_client.return_value.read_secret.assert_called_once_with(
        path=expected_path,
        version="1" if expected_path == "legacy" else "2",
    )
