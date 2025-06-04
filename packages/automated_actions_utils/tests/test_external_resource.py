from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from automated_actions_utils.external_resource import (
    AwsAccount,
    ExternalResource,
    ExternalResourceAppInterfaceError,
    VaultSecret,
    get_external_resource,
)


@pytest.fixture(autouse=True)
def mock_gql_client(mocker: MockerFixture) -> MagicMock:
    """Mocks the GQLClient and its query method for testing."""
    m = mocker.patch("automated_actions_utils.external_resource.GQLClient")
    m.return_value.query.return_value = {
        "namespaces": [
            {
                "name": "test-namespace",
                "delete": None,
                "externalResources": [
                    {
                        "provider": "aws",
                        "provisioner": {
                            "name": "test-account",
                            "automationToken": {
                                "path": "wherever/test-account",
                                "field": "all",
                                "version": None,
                                "format": None,
                            },
                            "resourcesDefaultRegion": "us-east-1",
                        },
                        "resources": [
                            {
                                "provider": "rds",
                                "identifier": "test-rds",
                                "region": None,
                                "delete": None,
                            },
                            {
                                "provider": "elasticache",
                                "identifier": "test-elasticache",
                            },
                        ],
                    }
                ],
                "cluster": {
                    "name": "test-cluster",
                    "serverUrl": "https://cluster.example.com",
                    "insecureSkipTLSVerify": None,
                    "jumpHost": None,
                    "automationToken": {
                        "path": "wherever/test-cluster",
                        "field": "token",
                        "version": None,
                        "format": None,
                    },
                    "clusterAdminAutomationToken": {
                        "path": "wherever/test-cluster-admin",
                        "field": "token",
                        "version": None,
                        "format": None,
                    },
                    "spec": {"region": "us-east-1"},
                    "internal": True,
                    "disable": None,
                },
            },
        ]
    }
    return m


def test_get_external_resource_success(mock_gql_client: MagicMock) -> None:
    """Tests successful retrieval of an external resource."""
    result = get_external_resource(account="test-account", identifier="test-rds")
    assert result == ExternalResource(
        identifier="test-rds",
        region=None,
        account=AwsAccount(
            name="test-account",
            automation_token=VaultSecret(
                path="wherever/test-account", field="all", version=None, q_format=None
            ),
            region="us-east-1",
        ),
    )
    mock_gql_client.return_value.query.assert_called_once()


def test_get_external_resource_missing(mock_gql_client: MagicMock) -> None:
    """Tests retrieval of a non-existent external resource."""
    with pytest.raises(ExternalResourceAppInterfaceError):
        get_external_resource(account="test-account", identifier="does-not-exist")

    mock_gql_client.return_value.query.assert_called_once()


def test_get_external_resource_no_namespaces(mock_gql_client: MagicMock) -> None:
    """Tests retrieval when no namespaces are returned from app-interface."""
    mock_gql_client.return_value.query.return_value = {"namespaces": []}
    with pytest.raises(ExternalResourceAppInterfaceError):
        get_external_resource(account="test-account", identifier="does-not-exist")

    mock_gql_client.return_value.query.assert_called_once()
